#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERRO: biblioteca requests nao instalada. Execute ./run_all.sh", file=sys.stderr)
    sys.exit(2)

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
HOSTS = ["HYPERV_HOST_A", "HYPERV-HYPERV_HOST_B"]

CATEGORIES = {
    "availability": [r"zabbix agent ping", r"agent availability", r"icmpping"],
    "uptime": [r"system uptime", r"uptime"],
    "cpu_user": [r"cpu user time"],
    "cpu_privileged": [r"cpu privileged time"],
    "cpu_interrupt": [r"cpu interrupt time"],
    "cpu_dpc": [r"cpu dpc time"],
    "cpu_queue": [r"cpu queue length", r"processor queue length"],
    "cpu_utilization": [r"cpu utilization", r"processor utilization", r"utilization of processor time", r"cpu usage"],
    "cpu_hyperv_logical_total": [r"hyper-v hypervisor logical processor.*total run time", r"logical processor.*total run time"],
    "cpu_hyperv_root_total": [r"hyper-v hypervisor root virtual processor.*total run time", r"root virtual processor.*total run time", r"hyper-v hypervisor root partition.*total run time"],
    "cpu_hyperv_virtual_total": [r"hyper-v hypervisor virtual processor.*total run time", r"virtual processor.*total run time"],
    "cpu_processor_total": [r"processor information.*processor time", r"processor\(_total\).*processor time", r"processor time"],
    "cpu_hyperv_any": [r"hyper-v hypervisor", r"logical processor", r"virtual processor", r"total run time", r"root virtual processor", r"hyper-v"],
    "memory_used": [r"vm\.memory\.size\[used\]", r"used memory", r"memory.*used"],
    "memory_available": [r"vm\.memory\.size\[available\]", r"available memory", r"free memory"],
    "memory_total": [r"vm\.memory\.size\[total\]", r"total memory", r"memory total"],
    "disk_percent": [r"vfs\.fs\.size\[.*pused\]", r"space utilization"],
    "disk_used": [r"vfs\.fs\.size\[.*used\]", r"used space"],
    "disk_total": [r"vfs\.fs\.size\[.*total\]", r"total space"],
    "disk_free": [r"vfs\.fs\.size\[.*free\]", r"free space"],
    "net_in": [r"net\.if\.in", r"bits received", r"bytes received", r"incoming network traffic", r"interface.*received", r"network.*in", r"vEthernet", r"Hyper-V Virtual Ethernet Adapter", r"NIC Team", r"Team", r"iSCSI", r"Ethernet"],
    "net_out": [r"net\.if\.out", r"bits sent", r"bytes sent", r"outgoing network traffic", r"interface.*sent", r"network.*out", r"vEthernet", r"Hyper-V Virtual Ethernet Adapter", r"NIC Team", r"Team", r"iSCSI", r"Ethernet"],
    "net_interfaces": [r"net\.if\.", r"bits received", r"bits sent", r"bytes received", r"bytes sent", r"interface", r"network", r"vEthernet", r"Hyper-V Virtual Ethernet Adapter", r"NIC Team", r"Team", r"iSCSI", r"Ethernet"],
    "net_errors": [r"errors", r"error packets"],
    "net_drops": [r"dropped", r"drops", r"discarded", r"packets dropped"],
    "hyperv_services": [r"hyper-v", r"vmms", r"vmcompute", r"vmictimesync", r"virtual machine management"],
}

REQUIRED = [
    "availability",
    "uptime",
    "cpu_user",
    "cpu_privileged",
    "cpu_hyperv_any",
    "cpu_processor_total",
    "memory_used",
    "memory_available",
    "memory_total",
    "disk_percent",
    "disk_used",
    "disk_total",
    "disk_free",
    "net_in",
    "net_out",
    "hyperv_services",
]


class Zabbix:
    def __init__(self):
        load_dotenv(ROOT / ".env")
        self.url = os.getenv("ZABBIX_URL", "http://SEU_SERVIDOR_INTERNO")
        self.user = os.getenv("ZABBIX_USER", "SEU_USUARIO")
        self.password = os.getenv("ZABBIX_PASSWORD", "SUA_SENHA")
        self.auth = None
        self.req_id = 0

    def call(self, method, params=None, auth=True):
        self.req_id += 1
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": self.req_id}
        if auth and self.auth:
            payload["auth"] = self.auth
        response = requests.post(self.url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(f"{method}: {data['error']}")
        return data["result"]

    def login(self):
        self.auth = self.call("user.login", {"user": self.user, "password": self.password}, auth=False)


def find_host(zbx, wanted):
    exact = zbx.call(
        "host.get",
        {
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["ip", "dns", "useip", "type", "port"],
            "selectGroups": ["name"],
            "filter": {"host": [wanted]},
        },
    )
    if exact:
        return exact[0]
    candidates = []
    for field in ("host", "name"):
        candidates.extend(
            zbx.call(
                "host.get",
                {
                    "output": ["hostid", "host", "name", "status"],
                    "selectInterfaces": ["ip", "dns", "useip", "type", "port"],
                    "selectGroups": ["name"],
                    "search": {field: wanted},
                    "searchWildcardsEnabled": True,
                },
            )
        )
    wanted_l = wanted.lower()
    for host in candidates:
        if host.get("host", "").lower() == wanted_l or host.get("name", "").lower() == wanted_l:
            return host
    return candidates[0] if candidates else None


def match_category(item_name, category):
    haystack = item_name.lower()
    return any(re.search(pattern, haystack, re.I) for pattern in CATEGORIES[category])


def slim_item(item):
    lastclock = int(item.get("lastclock") or 0)
    lastvalue = item.get("lastvalue")
    return {
        "itemid": item.get("itemid"),
        "name": item.get("name"),
        "key_": item.get("key_"),
        "value_type": item.get("value_type"),
        "units": item.get("units"),
        "lastvalue": lastvalue,
        "lastclock": lastclock,
        "status": item.get("status"),
        "enabled": str(item.get("status")) == "0",
        "has_data": lastclock > 0 and lastvalue not in (None, "", "ZBX_NOTSUPPORTED", "ZBX_NODATA"),
    }


def main():
    LOGS.mkdir(exist_ok=True)
    discovery = {
        "zabbix_url": None,
        "api_version": None,
        "hosts_expected": HOSTS,
        "hosts": {},
        "missing": {},
        "problems": [],
    }
    debug_lines = []

    try:
        zbx = Zabbix()
        discovery["zabbix_url"] = zbx.url
        discovery["api_version"] = zbx.call("apiinfo.version", auth=False)
        zbx.login()
        for host in HOSTS:
            discovery["hosts"][host] = {"found": False, "items": [], "categories": {}, "triggers": []}
            discovery["missing"][host] = []
            matched = find_host(zbx, host)
            if not matched:
                msg = f"{host}: host nao encontrado no Zabbix"
                discovery["problems"].append(msg)
                debug_lines.append(msg)
                continue

            hostid = matched["hostid"]
            discovery["hosts"][host]["found"] = True
            discovery["hosts"][host]["hostid"] = hostid
            discovery["hosts"][host]["query_host"] = host
            discovery["hosts"][host]["zabbix_host"] = matched.get("host")
            discovery["hosts"][host]["zabbix_name"] = matched.get("name")
            discovery["hosts"][host]["groups"] = matched.get("groups", [])
            discovery["hosts"][host]["interfaces"] = matched.get("interfaces", [])

            items = zbx.call(
                "item.get",
                {
                    "output": ["itemid", "name", "key_", "value_type", "units", "lastvalue", "lastclock", "status"],
                    "hostids": [hostid],
                    "filter": {"status": 0},
                    "sortfield": "name",
                },
            )
            discovery["hosts"][host]["items"] = [slim_item(i) for i in items]
            discovery["hosts"][host]["items_with_data"] = [i for i in discovery["hosts"][host]["items"] if i["has_data"]]

            for category in CATEGORIES:
                matches = [slim_item(i) for i in items if match_category(i.get("name", "") + " " + i.get("key_", ""), category)]
                discovery["hosts"][host]["categories"][category] = matches
            for category in REQUIRED:
                if not discovery["hosts"][host]["categories"].get(category):
                    discovery["missing"][host].append(category)
                    debug_lines.append(f"{host}: nenhum item detectado para categoria {category}")

            triggers = zbx.call(
                "trigger.get",
                {
                    "output": ["triggerid", "description", "priority", "value", "lastchange"],
                    "hostids": [hostid],
                    "selectItems": ["itemid", "name", "key_"],
                    "sortfield": "priority",
                    "sortorder": "DESC",
                },
            )
            discovery["hosts"][host]["triggers"] = triggers
    except Exception as exc:
        discovery["problems"].append(str(exc))
        debug_lines.append(f"Falha geral na descoberta: {exc}")

    (LOGS / "hyperv-items-discovery.json").write_text(json.dumps(discovery, indent=2, ensure_ascii=False))
    (LOGS / "debug_no_data.log").write_text("\n".join(debug_lines) + ("\n" if debug_lines else "Nenhum item obrigatorio ausente detectado.\n"))
    print(json.dumps({
        "hosts": {h: {"found": d["found"], "items": len(d["items"]), "missing": discovery["missing"].get(h, [])} for h, d in discovery["hosts"].items()},
        "problems": discovery["problems"],
        "output": "logs/hyperv-items-discovery.json",
    }, indent=2, ensure_ascii=False))
    return 0 if not discovery["problems"] else 1


if __name__ == "__main__":
    sys.exit(main())
