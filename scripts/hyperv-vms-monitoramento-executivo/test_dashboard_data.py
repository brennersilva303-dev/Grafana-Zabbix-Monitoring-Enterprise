#!/usr/bin/env python3
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
DISCOVERY = LOGS / "hyperv-items-discovery.json"
OUTPUT = LOGS / "dashboard-data-validation.json"
HOSTS = ["HYPERV_HOST_A", "HYPERV-HYPERV_HOST_B"]
DIRECT_KEYS = {
    "status": ["agent.ping"],
    "uptime": ["system.uptime"],
    "memory_used": ["vm.memory.size[used]"],
    "memory_total": ["vm.memory.size[total]"],
    "memory_available": ["vm.memory.size[available]", "vm.memory.size[free]"],
}
DIRECT_KEY_NAMES = {
    "agent.ping": "Zabbix agent ping",
    "system.uptime": "Uptime",
    "vm.memory.size[used]": "Used memory",
    "vm.memory.size[total]": "Total memory",
    "vm.memory.size[available]": "Available memory",
    "vm.memory.size[free]": "Free memory",
}


def has_data(item):
    return bool(
        item
        and item.get("enabled")
        and (
            int(item.get("lastclock") or 0) > 0
            or item.get("validation_source") == "zabbix_get"
        )
        and item.get("lastvalue") not in (None, "", "ZBX_NOTSUPPORTED", "ZBX_NODATA")
    )


def interface_ip(hdata):
    for interface in hdata.get("interfaces", []):
        if interface.get("ip"):
            return interface["ip"]
    return None


def zabbix_get(ip, key):
    if not ip or not shutil.which("zabbix_get"):
        return None
    try:
        completed = subprocess.run(
            ["zabbix_get", "-s", ip, "-k", key],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=8,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    if value in ("", "ZBX_NOTSUPPORTED", "ZBX_NODATA"):
        return None
    return value


def validate_item_with_agent(item, ip):
    if has_data(item) or not item or not item.get("enabled"):
        return item
    value = zabbix_get(ip, item.get("key_", ""))
    if value is None:
        return item
    enriched = dict(item)
    enriched["lastvalue"] = value
    enriched["has_data"] = True
    enriched["validation_source"] = "zabbix_get"
    enriched["validation_note"] = "Item enabled validado por zabbix_get; API Zabbix ainda nao tinha lastclock > 0."
    return enriched


def enrich_items_with_agent_checks(items, hdata):
    ip = interface_ip(hdata)
    if not ip:
        return items, {"zabbix_get_available": bool(shutil.which("zabbix_get")), "ip": None, "validated_keys": []}

    direct_keys = {key for keys in DIRECT_KEYS.values() for key in keys}
    candidates = []
    for item in items:
        key = item.get("key_", "")
        name = item.get("name", "")
        if key in direct_keys:
            candidates.append(item)
        elif any(label.lower() in name.lower() for label in ["CPU user time", "CPU privileged time", "Space utilization", "Bits received", "Bits sent"]):
            candidates.append(item)

    validated_by_itemid = {}
    for item in candidates:
        checked = validate_item_with_agent(item, ip)
        if checked.get("validation_source") == "zabbix_get":
            validated_by_itemid[item.get("itemid")] = checked

    enriched = [validated_by_itemid.get(item.get("itemid"), item) for item in items]
    existing_keys = {item.get("key_") for item in enriched}
    for key in sorted(direct_keys - existing_keys):
        value = zabbix_get(ip, key)
        if value is None:
            continue
        synthetic = {
            "itemid": f"zabbix_get:{ip}:{key}",
            "name": DIRECT_KEY_NAMES.get(key, key),
            "key_": key,
            "value_type": "3",
            "units": "B" if key.startswith("vm.memory.size") else "",
            "lastvalue": value,
            "lastclock": 0,
            "status": "0",
            "enabled": True,
            "has_data": True,
            "validation_source": "zabbix_get",
            "validation_note": "Key validada diretamente por zabbix_get, mas nao existe como item enabled retornado pela API Zabbix.",
            "synthetic": True,
        }
        if key == "vm.memory.size[available]":
            synthetic["synthetic_expression"] = "memory_total_minus_used"
        enriched.append(synthetic)
        validated_by_itemid[synthetic["itemid"]] = synthetic
    return enriched, {
        "zabbix_get_available": bool(shutil.which("zabbix_get")),
        "ip": ip,
        "validated_keys": [
            {"name": item.get("name"), "key_": item.get("key_"), "lastvalue": item.get("lastvalue")}
            for item in validated_by_itemid.values()
        ],
    }


def by_key(items, exact_keys):
    for key in exact_keys:
        for item in items:
            if has_data(item) and item.get("key_") == key:
                return item
    return None


def by_key_regex(items, patterns):
    compiled = [re.compile(p, re.I) for p in patterns]
    for item in items:
        if has_data(item) and any(p.search(item.get("key_", "")) for p in compiled):
            return item
    return None


def by_name(items, names):
    lowered = [n.lower() for n in names]
    for item in items:
        name = item.get("name", "").lower()
        if has_data(item) and any(n in name for n in lowered):
            return item
    return None


def all_by_name(items, names):
    lowered = [n.lower() for n in names]
    return [item for item in items if has_data(item) and any(n in item.get("name", "").lower() for n in lowered)]


def all_by_key_or_name(items, key_patterns, names):
    compiled = [re.compile(p, re.I) for p in key_patterns]
    lowered = [n.lower() for n in names]
    out = []
    for item in items:
        if not has_data(item):
            continue
        key = item.get("key_", "")
        name = item.get("name", "").lower()
        if any(p.search(key) for p in compiled) or any(n in name for n in lowered):
            out.append(item)
    return out


def cpu_candidates(items):
    priorities = [
        (
            "cpu_hyperv_logical_total",
            [
                r"hyper-v hypervisor logical processor.*\(_total\).*total run time",
                r"hyper-v hypervisor logical processor.*total run time",
                r"logical processor.*\(_total\).*total run time",
            ],
            [
                "Hyper-V Hypervisor Logical Processor(_Total)% Total Run Time",
                "Hyper-V Hypervisor Logical Processor",
                "Logical Processor",
                "Total Run Time",
            ],
        ),
        (
            "cpu_hyperv_root_total",
            [
                r"hyper-v hypervisor root virtual processor.*\(_total\).*total run time",
                r"hyper-v hypervisor root partition.*total run time",
                r"root virtual processor.*total run time",
            ],
            [
                "Hyper-V Hypervisor Root Virtual Processor",
                "Hyper-V Hypervisor Root Partition",
                "Root Virtual Processor",
                "Total Run Time",
            ],
        ),
        (
            "cpu_hyperv_virtual_total",
            [
                r"hyper-v hypervisor virtual processor.*\(_total\).*total run time",
                r"hyper-v hypervisor virtual processor.*total run time",
                r"virtual processor.*total run time",
            ],
            [
                "Hyper-V Hypervisor Virtual Processor",
                "Virtual Processor",
                "Total Run Time",
            ],
        ),
        (
            "cpu_processor_total",
            [
                r"processor information.*\(_total\).*processor time",
                r"processor\(_total\).*processor time",
                r"% processor time",
            ],
            [
                "Processor Information(_Total)% Processor Time",
                "Processor(_Total)% Processor Time",
                "Processor Time",
            ],
        ),
        (
            "cpu_utilization",
            [r"system\.cpu\.util", r"cpu utilization", r"processor utilization"],
            ["CPU utilization", "Processor utilization"],
        ),
    ]
    by_priority = {}
    for category, key_patterns, name_parts in priorities:
        by_priority[category] = all_by_key_or_name(items, key_patterns, name_parts)
    fallback = all_by_name(items, [
        "CPU user time",
        "CPU privileged time",
        "CPU interrupt time",
        "CPU DPC time",
        "CPU queue length",
        "CPU utilization",
    ])
    by_priority["cpu_fallback"] = fallback
    return by_priority


def network_items(items):
    candidates = all_by_key_or_name(
        items,
        [r"^net\.if\.", r"network", r"wmi.*network"],
        [
            "Bits received",
            "Bits sent",
            "Bytes Received",
            "Bytes Sent",
            "Interface",
            "Network",
            "vEthernet",
            "Hyper-V Virtual Ethernet Adapter",
            "NIC Team",
            "Team",
            "iSCSI",
            "Ethernet",
        ],
    )
    return [item for item in candidates if not item.get("key_", "").startswith("service.info")]


def disk_metric(item):
    key = item.get("key_", "")
    match = re.search(r"^vfs\.fs\.size\[(.*),(pused|used|total|free)\]$", key, re.I)
    if match:
        return match.group(1), match.group(2).lower()
    name = item.get("name", "")
    volume = name.split("::", 1)[0] + ":" if "::" in name else name.split(":", 1)[0]
    lname = name.lower()
    if "space utilization" in lname:
        return volume, "pused"
    if "used space" in lname:
        return volume, "used"
    if "total space" in lname:
        return volume, "total"
    if "free space" in lname:
        return volume, "free"
    return None, None


def disk_inventory(items):
    inventory = {}
    for item in items:
        if not has_data(item):
            continue
        volume, metric = disk_metric(item)
        if not volume or metric not in ("pused", "used", "total", "free"):
            continue
        entry = inventory.setdefault(volume, {"volume": volume})
        entry[metric] = item
    out = []
    for volume, entry in sorted(inventory.items()):
        if "pused" not in entry and not any(k in entry for k in ("used", "total", "free")):
            continue
        out.append(entry)
    return out


def pick(items):
    selected = {}
    missing = {}

    selected["status"] = by_key(items, ["agent.ping"]) or by_name(items, ["zabbix agent ping", "agent availability"])
    selected["uptime"] = by_key(items, ["system.uptime"]) or by_name(items, ["uptime"])
    selected["memory_used"] = by_key(items, ["vm.memory.size[used]"])
    selected["memory_total"] = by_key(items, ["vm.memory.size[total]"])
    selected["memory_available"] = by_key(items, ["vm.memory.size[available]", "vm.memory.size[free]"])

    cpu_items = all_by_name(items, [
        "CPU user time",
        "CPU privileged time",
        "CPU interrupt time",
        "CPU DPC time",
        "CPU queue length",
        "CPU utilization",
    ])
    cpus = cpu_candidates(items)
    selected["cpu_hyperv_logical_total"] = cpus["cpu_hyperv_logical_total"][0] if cpus["cpu_hyperv_logical_total"] else None
    selected["cpu_hyperv_root_total"] = cpus["cpu_hyperv_root_total"][0] if cpus["cpu_hyperv_root_total"] else None
    selected["cpu_hyperv_virtual_total"] = cpus["cpu_hyperv_virtual_total"][0] if cpus["cpu_hyperv_virtual_total"] else None
    selected["cpu_processor_total"] = cpus["cpu_processor_total"][0] if cpus["cpu_processor_total"] else None
    selected["cpu_utilization"] = cpus["cpu_utilization"][0] if cpus["cpu_utilization"] else by_name(cpu_items, ["CPU utilization"])
    selected["cpu_user"] = by_name(cpu_items, ["CPU user time"])
    selected["cpu_privileged"] = by_name(cpu_items, ["CPU privileged time"])
    selected["cpu_interrupt"] = by_name(cpu_items, ["CPU interrupt time"])
    selected["cpu_dpc"] = by_name(cpu_items, ["CPU DPC time"])
    selected["cpu_queue"] = by_name(cpu_items, ["CPU queue length"])
    selected["cpu_current"] = (
        selected["cpu_hyperv_logical_total"]
        or selected["cpu_hyperv_root_total"]
        or selected["cpu_hyperv_virtual_total"]
        or selected["cpu_processor_total"]
    )
    selected["cpu_any"] = selected["cpu_current"] or selected["cpu_user"] or selected["cpu_privileged"] or (cpu_items[0] if cpu_items else None)

    disk_items = all_by_key_or_name(items, [r"^vfs\.fs\.size\[.*,\s*pused\]"], ["Space utilization"])
    selected["disk_percent"] = disk_items[0] if disk_items else None
    selected["disk_all_percent"] = disk_items
    selected["disk_all_used"] = all_by_key_or_name(items, [r"^vfs\.fs\.size\[.*,\s*used\]"], ["Used space"])
    selected["disk_all_total"] = all_by_key_or_name(items, [r"^vfs\.fs\.size\[.*,\s*total\]"], ["Total space"])
    selected["disk_all_free"] = all_by_key_or_name(items, [r"^vfs\.fs\.size\[.*,\s*free\]"], ["Free space"])
    selected["disk_volumes"] = disk_inventory(items)

    nets = network_items(items)
    selected["net_interfaces"] = nets
    selected["net_in"] = by_key_regex(items, [r"^net\.if\.in\[.*\]"]) or by_name(items, ["Bits received", "Bytes Received", "Incoming network traffic"])
    selected["net_out"] = by_key_regex(items, [r"^net\.if\.out\[.*\]"]) or by_name(items, ["Bits sent", "Bytes Sent", "Outgoing network traffic"])
    selected["net_errors"] = all_by_key_or_name(items, [r"^net\.if\..*errors"], ["errors", "error packets"])
    selected["net_drops"] = all_by_key_or_name(items, [r"^net\.if\..*(dropped|discarded)"], ["dropped", "drops", "discarded"])

    for key, item in selected.items():
        if key.startswith("disk_all_") or key in ("disk_volumes", "net_interfaces", "net_errors", "net_drops"):
            continue
        if item is None:
            missing[key] = "Nenhum item enabled validado por API Zabbix ou zabbix_get encontrado para este painel."

    return selected, missing


def slim(item):
    if item is None:
        return None
    return {k: item.get(k) for k in ("itemid", "name", "key_", "lastvalue", "lastclock", "units", "status", "enabled", "has_data", "validation_source", "validation_note", "synthetic", "synthetic_expression")}


def main():
    if not DISCOVERY.exists():
        print("ERRO: execute scripts/discover_hyperv_items.py antes.", file=sys.stderr)
        return 2

    discovery = json.loads(DISCOVERY.read_text())
    result = {"hosts": {}, "panels_without_data": []}

    for host in HOSTS:
        hdata = discovery.get("hosts", {}).get(host, {})
        items, agent_validation = enrich_items_with_agent_checks(hdata.get("items", []), hdata)
        with_data = [i for i in items if has_data(i)]
        selected, missing = pick(items)
        triggers = hdata.get("triggers", [])
        problems = [t for t in triggers if str(t.get("value")) == "1"]

        result["hosts"][host] = {
            "found": bool(hdata.get("found")),
            "query_host": hdata.get("query_host", host),
            "zabbix_host": hdata.get("zabbix_host"),
            "zabbix_name": hdata.get("zabbix_name"),
            "interfaces": hdata.get("interfaces", []),
            "groups": hdata.get("groups", []),
            "enabled_items": len(items),
            "items_with_data": len(with_data),
            "agent_validation": agent_validation,
            "items_without_data": [slim(i) for i in items if not has_data(i)],
            "selected": {
                k: (
                    [{kk: (slim(vv) if isinstance(vv, dict) else vv) for kk, vv in x.items()} for x in v]
                    if k in ("disk_volumes", "net_interfaces")
                    else ([slim(x) for x in v] if isinstance(v, list) else slim(v))
                )
                for k, v in selected.items()
            },
            "missing": missing,
            "problems_active": len(problems),
            "triggers_total": len(triggers),
        }
        for panel, reason in missing.items():
            result["panels_without_data"].append({"host": host, "panel": panel, "reason": reason})

    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps({
        "hosts": {h: {"items_with_data": d["items_with_data"], "missing": list(d["missing"].keys())} for h, d in result["hosts"].items()},
        "output": str(OUTPUT),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
