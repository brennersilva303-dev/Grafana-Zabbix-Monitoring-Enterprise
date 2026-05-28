#!/usr/bin/env python3
import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError as exc:
    raise SystemExit(f"requests nao instalado: {exc}")


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
HOSTS = ["HYPERV_HOST_A", "HYPERV-HYPERV_HOST_B"]
CACHE_FILE = LOGS / "hyperv-vms-collector-cache.json"
ZABBIX_URL = os.getenv("ZABBIX_URL", "http://SEU_SERVIDOR_INTERNO")
ZABBIX_USER = SEU_USUARIO
ZABBIX_PASSWORD = SUA_SENHA

QUERIES = {
    "vms": 'wmi.getall[root\\virtualization\\v2,"select ElementName,EnabledState,HealthState,Name,OnTimeInMilliseconds from Msvm_ComputerSystem where Caption=\\"Virtual Machine\\""]',
    "memory": 'wmi.getall[root\\virtualization\\v2,"select ElementName,VirtualQuantity,Reservation,Limit,InstanceID from Msvm_MemorySettingData"]',
    "cpu": 'wmi.getall[root\\cimv2,"select Name,PercentTotalRunTime from Win32_PerfFormattedData_HvStats_HyperVHypervisorVirtualProcessor"]',
    "vhd": 'wmi.getall[root\\virtualization\\v2,"select InstanceID,ElementName,HostResource,ResourceSubType from Msvm_StorageAllocationSettingData"]',
    "nic": 'wmi.getall[root\\virtualization\\v2,"select InstanceID,ElementName,Address,VirtualSystemIdentifiers from Msvm_SyntheticEthernetPortSettingData"]',
    "traffic": 'wmi.getall[root\\cimv2,"select Name,BytesReceivedPersec,BytesSentPersec from Win32_PerfFormattedData_NvspNicStats_HyperVVirtualNetworkAdapter"]',
    "settings": 'wmi.getall[root\\virtualization\\v2,"select ElementName,InstanceID,Description,VirtualSystemIdentifier,VirtualSystemType,Parent from Msvm_VirtualSystemSettingData"]',
}

QUERY_TTL_SECONDS = {
    "vms": 60,
    "memory": 60,
    "cpu": 60,
    "traffic": 60,
    "nic": 600,
    "vhd": 600,
    "settings": 300,
}

STATE_MAP = {
    2: "Running",
    3: "Off",
    32768: "Paused",
    32769: "Suspended",
    32770: "Starting",
    32771: "Snapshotting",
    32773: "Saving",
    32774: "Stopping",
    32776: "Pausing",
    32777: "Resuming",
}


class Zabbix:
    def __init__(self):
        self.req_id = 0
        self.auth = None

    def call(self, method, params=None, auth=True):
        self.req_id += 1
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": self.req_id}
        if auth and self.auth:
            payload["auth"] = self.auth
        response = requests.post(ZABBIX_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(f"{method}: {data['error']}")
        return data["result"]

    def login(self):
        self.auth = self.call("user.login", {"user": ZABBIX_USER, "password": ZABBIX_PASSWORD}, auth=False)


def find_host(zbx, wanted):
    for params in (
        {"filter": {"host": [wanted]}},
        {"filter": {"name": [wanted]}},
        {"search": {"host": wanted, "name": wanted}, "searchByAny": True},
    ):
        result = zbx.call(
            "host.get",
            {
                "output": ["hostid", "host", "name", "status"],
                "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type", "main"],
                **params,
            },
        )
        if result:
            return result[0]
    return None


def zabbix_get(ip, key, timeout=45):
    proc = subprocess.run(
        ["zabbix_get", "-s", ip, "-k", key],
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    text = proc.stdout.strip()
    return {
        "ok": proc.returncode == 0 and not text.startswith("ZBX_NOTSUPPORTED") and text != "",
        "rc": proc.returncode,
        "stdout": text,
        "stderr": proc.stderr.strip(),
        "key": key,
    }


def result_json(result):
    if not result["ok"]:
        return []
    try:
        data = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def load_cache():
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cached_zabbix_get(cache, host, ip, name, key):
    now = int(datetime.now().timestamp())
    ttl = QUERY_TTL_SECONDS.get(name, 60)
    host_cache = cache.setdefault(host, {})
    cached = host_cache.get(name)
    if cached and now - int(cached.get("timestamp", 0)) < ttl:
        result = cached["result"]
        result["cache"] = "hit"
        result["ttl_seconds"] = ttl
        return result
    result = zabbix_get(ip, key)
    result["cache"] = "miss"
    result["ttl_seconds"] = ttl
    if result["ok"]:
        host_cache[name] = {"timestamp": now, "result": result}
    return result


def guid_from_instance(instance_id):
    match = re.search(r"Microsoft:([0-9A-Fa-f-]{36})", instance_id or "")
    return match.group(1).upper() if match else None


def state_name(value):
    try:
        return STATE_MAP.get(int(value), str(value))
    except (TypeError, ValueError):
        return str(value or "-")


def uptime_text(ms):
    try:
        seconds = int(ms) // 1000
    except (TypeError, ValueError):
        return "-"
    if seconds <= 0:
        return "-"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def mb(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def aggregate_cpu(rows):
    cpu = defaultdict(list)
    for row in rows:
        name = row.get("Name", "")
        if name == "_Total" or ":Hv VP" not in name:
            continue
        vm_name = name.split(":Hv VP", 1)[0]
        try:
            cpu[vm_name].append(float(row.get("PercentTotalRunTime", 0)))
        except (TypeError, ValueError):
            pass
    return {name: round(sum(values) / len(values), 1) for name, values in cpu.items() if values}


def aggregate_traffic(rows):
    traffic = defaultdict(lambda: {"in_bps": 0.0, "out_bps": 0.0})
    for row in rows:
        name = row.get("Name", "")
        if "_" not in name or "__DEVICE_" in name:
            continue
        vm_name = name.split("_", 1)[0]
        try:
            traffic[vm_name]["in_bps"] += float(row.get("BytesReceivedPersec", 0)) * 8
            traffic[vm_name]["out_bps"] += float(row.get("BytesSentPersec", 0)) * 8
        except (TypeError, ValueError):
            pass
    return {k: {"in_mbps": round(v["in_bps"] / 1_000_000, 2), "out_mbps": round(v["out_bps"] / 1_000_000, 2)} for k, v in traffic.items()}


def collect_host(host, matched, cache):
    iface = next((i for i in matched.get("interfaces", []) if i.get("main") == "1"), matched.get("interfaces", [{}])[0])
    ip = iface.get("ip") or iface.get("dns")
    raw = {name: cached_zabbix_get(cache, host, ip, name, key) for name, key in QUERIES.items()}
    parsed = {name: result_json(result) for name, result in raw.items()}

    names_by_guid = {}
    vms = {}
    for row in parsed["vms"]:
        guid = (row.get("Name") or "").upper()
        name = row.get("ElementName") or guid
        names_by_guid[guid] = name
        vms[name] = {
            "name": name,
            "guid": guid,
            "host": host,
            "state": state_name(row.get("EnabledState")),
            "status": "OK" if str(row.get("HealthState")) == "5" else str(row.get("HealthState")),
            "uptime": uptime_text(row.get("OnTimeInMilliseconds")),
            "uptime_ms": int(row.get("OnTimeInMilliseconds") or 0),
            "cpu_usage_percent": 0.0,
            "assigned_memory_mb": 0,
            "demand_memory_mb": None,
            "checkpoint_count": 0,
            "vhd_paths": [],
            "vhd_count": 0,
            "network_adapters": [],
            "network_switch": "-",
            "ip_addresses": [],
            "traffic_in_mbps": 0.0,
            "traffic_out_mbps": 0.0,
        }

    for row in parsed["memory"]:
        guid = guid_from_instance(row.get("InstanceID"))
        name = names_by_guid.get(guid)
        if name and name in vms and row.get("ElementName") == "Memory":
            vms[name]["assigned_memory_mb"] = mb(row.get("VirtualQuantity"))

    cpu_by_vm = aggregate_cpu(parsed["cpu"])
    for name, value in cpu_by_vm.items():
        if name in vms:
            vms[name]["cpu_usage_percent"] = value

    traffic_by_vm = aggregate_traffic(parsed["traffic"])
    for name, value in traffic_by_vm.items():
        if name in vms:
            vms[name].update({"traffic_in_mbps": value["in_mbps"], "traffic_out_mbps": value["out_mbps"]})

    for row in parsed["vhd"]:
        if row.get("ResourceSubType") != "Microsoft:Hyper-V:Virtual Hard Disk":
            continue
        guid = guid_from_instance(row.get("InstanceID"))
        name = names_by_guid.get(guid)
        resources = row.get("HostResource") or []
        if isinstance(resources, str):
            resources = [resources]
        if name and name in vms:
            vms[name]["vhd_count"] += 1
            if not resources:
                resources = ["Caminho nao retornado pela WMI"]
            for path in resources:
                if path and path not in vms[name]["vhd_paths"]:
                    vms[name]["vhd_paths"].append(path)

    for row in parsed["nic"]:
        guid = guid_from_instance(row.get("InstanceID"))
        name = names_by_guid.get(guid)
        if name and name in vms and row.get("Address"):
            vms[name]["network_adapters"].append({"name": row.get("ElementName", "NIC"), "mac": row.get("Address")})

    active_guids = set(names_by_guid)
    for row in parsed["settings"]:
        if row.get("VirtualSystemType") != "Microsoft:Hyper-V:Snapshot:Realized":
            continue
        guid = (row.get("VirtualSystemIdentifier") or "").upper()
        if guid in active_guids:
            name = names_by_guid[guid]
            vms[name]["checkpoint_count"] += 1

    validation = {}
    for name, result in raw.items():
        validation[name] = {
            "ok": result["ok"],
            "cache": result.get("cache", "miss"),
            "ttl_seconds": result.get("ttl_seconds"),
            "rc": result["rc"],
            "error": result["stderr"] or (result["stdout"][:180] if not result["ok"] else ""),
            "records": len(parsed[name]),
            "key": result["key"],
        }
    return {
        "host": host,
        "zabbix_host": matched.get("host"),
        "visible_name": matched.get("name"),
        "interface": iface,
        "vms": sorted(vms.values(), key=lambda item: (item["state"] != "Running", item["name"].lower())),
        "validation": validation,
    }


def main():
    LOGS.mkdir(exist_ok=True)
    zbx = Zabbix()
    api_version = zbx.call("apiinfo.version", auth=False)
    zbx.login()
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "api_version": api_version,
        "collection_mode": "somente leitura: zabbix_get com chaves wmi.getall",
        "vm_operational_changes": False,
        "forbidden_commands_executed": [],
        "hosts": {},
        "summary": {},
    }
    cache = load_cache()
    for host in HOSTS:
        matched = find_host(zbx, host)
        if not matched:
            report["hosts"][host] = {"found": False, "error": "Host nao encontrado no Zabbix", "vms": []}
            continue
        collected = collect_host(host, matched, cache)
        report["hosts"][host] = {"found": True, **collected}
        vms = collected["vms"]
        report["summary"][host] = {
            "total": len(vms),
            "running": sum(1 for vm in vms if vm["state"] == "Running"),
            "off": sum(1 for vm in vms if vm["state"] == "Off"),
            "checkpoints": sum(vm["checkpoint_count"] for vm in vms),
            "vhd_count": sum(vm["vhd_count"] for vm in vms),
        }
    save_cache(cache)
    output = LOGS / "hyperv-vms-metrics-validation.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "summary": report["summary"], "vm_operational_changes": False}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
