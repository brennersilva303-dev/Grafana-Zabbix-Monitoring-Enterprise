#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
OUT = ROOT / "logs" / "test_zabbix_items.json"
KEYS = [
    "printer.ping",
    "icmpping",
    "printer.snmp.available",
]


class Zabbix:
    def __init__(self):
        url = os.getenv("ZABBIX_URL", "http://SEU_SERVIDOR_INTERNO").rstrip("/")
        self.endpoint = url if url.endswith("/api_jsonrpc.php") else url + "/api_jsonrpc.php"
        self.auth = None
        self.req_id = 1

    def call(self, method, params=None, auth=True):
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": self.req_id}
        self.req_id += 1
        if auth and self.auth:
            payload["auth"] = self.auth
        response = requests.post(self.endpoint, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(f"{method}: {data['error']}")
        return data["result"]

    def login(self):
        user = os.getenv("ZABBIX_USER", "SEU_USUARIO")
        password = os.getenv("ZABBIX_PASSWORD", "SUA_SENHA")
        try:
            self.auth = self.call("user.login", {"username": user, "password": password}, auth=False)
        except RuntimeError:
            self.auth = self.call("user.login", {"user": user, "password": password}, auth=False)


def main():
    api = Zabbix()
    print(f"Zabbix API: {api.call('apiinfo.version', {}, auth=False)}")
    api.login()
    groups = api.call("hostgroup.get", {"filter": {"name": ["Impressoras"]}, "output": ["groupid", "name"]})
    if not groups:
        raise SystemExit("Grupo Impressoras nao existe. Grafana tera No data.")
    hosts = api.call(
        "host.get",
        {
            "groupids": groups[0]["groupid"],
            "output": ["hostid", "host", "name"],
            "selectInterfaces": ["ip", "dns", "type"],
            "sortfield": "host",
        },
    )
    now = int(time.time())
    report = {"hosts": [], "missing_items": 0, "items_without_data": 0}
    for host in hosts:
        items = api.call(
            "item.get",
            {
                "hostids": host["hostid"],
                "filter": {"key_": KEYS},
                "output": ["itemid", "name", "key_", "lastvalue", "lastclock", "status", "state", "error"],
                "sortfield": "key_",
            },
        )
        by_key = {item["key_"]: item for item in items}
        host_report = {"host": host["host"], "items": []}
        for key in KEYS:
            item = by_key.get(key)
            if not item:
                report["missing_items"] += 1
                host_report["items"].append({"key": key, "problem": "missing"})
                continue
            lastclock = int(item.get("lastclock") or 0)
            age = now - lastclock if lastclock else None
            if not lastclock:
                report["items_without_data"] += 1
            host_report["items"].append(
                {
                    "key": key,
                    "itemid": item["itemid"],
                    "lastvalue": item.get("lastvalue"),
                    "lastclock": item.get("lastclock"),
                    "age_seconds": age,
                    "status": item.get("status"),
                    "state": item.get("state"),
                    "error": item.get("error"),
                    "grafana_no_data_reason": "sem lastclock ainda" if not lastclock else "",
                }
            )
        report["hosts"].append(host_report)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Hosts no grupo Impressoras: {len(hosts)}")
    print(f"Itens faltantes: {report['missing_items']}")
    print(f"Itens sem coleta: {report['items_without_data']}")
    print(f"Relatorio: {OUT}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
