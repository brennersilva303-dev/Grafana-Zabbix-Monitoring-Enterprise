#!/usr/bin/env python3
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError as exc:
    raise SystemExit(f"requests nao instalado: {exc}")


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
HOSTS = ["HYPERV_HOST_A", "HYPERV-HYPERV_HOST_B"]
ZABBIX_URL = os.getenv("ZABBIX_URL", "http://SEU_SERVIDOR_INTERNO")
ZABBIX_USER = SEU_USUARIO
ZABBIX_PASSWORD = SUA_SENHA


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


def zabbix_get(ip, key, timeout=30):
    cmd = ["zabbix_get", "-s", ip, "-k", key]
    proc = subprocess.run(cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return {
        "command": " ".join(cmd),
        "rc": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "ok": proc.returncode == 0 and not proc.stdout.startswith("ZBX_NOTSUPPORTED"),
    }


def parse_json_result(result):
    if not result["ok"]:
        return []
    try:
        data = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def main():
    LOGS.mkdir(exist_ok=True)
    zbx = Zabbix()
    api_version = zbx.call("apiinfo.version", auth=False)
    zbx.login()
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "api_version": api_version,
        "mode": "somente leitura via zabbix_get + WMI Hyper-V",
        "hosts": {},
        "safety": {
            "allowed": ["wmi.getall", "zabbix_get", "Zabbix API host/item read"],
            "blocked": ["Stop-VM", "Start-VM", "Restart-VM", "Save-VM", "Suspend-VM", "Move-VM", "Remove-VM", "Set-VM", "Checkpoint-VM"],
            "vm_operational_changes": False,
        },
    }
    vm_query = 'wmi.getall[root\\virtualization\\v2,"select ElementName,EnabledState,HealthState,Name,OnTimeInMilliseconds from Msvm_ComputerSystem where Caption=\\"Virtual Machine\\""]'
    for host in HOSTS:
        matched = find_host(zbx, host)
        host_report = {"found": bool(matched), "vms": [], "query": vm_query}
        if not matched:
            host_report["error"] = "Host nao encontrado no Zabbix"
            report["hosts"][host] = host_report
            continue
        iface = next((i for i in matched.get("interfaces", []) if i.get("main") == "1"), matched.get("interfaces", [{}])[0])
        ip = iface.get("ip") or iface.get("dns")
        host_report.update({"hostid": matched["hostid"], "zabbix_host": matched.get("host"), "visible_name": matched.get("name"), "interface": iface})
        result = zabbix_get(ip, vm_query)
        host_report["raw_status"] = {"ok": result["ok"], "rc": result["rc"], "stderr": result["stderr"]}
        host_report["vms"] = parse_json_result(result)
        host_report["vm_count"] = len(host_report["vms"])
        report["hosts"][host] = host_report
    output = LOGS / "hyperv-vms-discovery.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "hosts": {h: report["hosts"][h].get("vm_count", 0) for h in HOSTS}}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
