#!/usr/bin/env python3
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DVRS_FILE = ROOT / "scripts" / "dvrs_list.csv"
OUT = ROOT / "dashboards" / "dvrs-inventory.json"


def load_env(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env(ROOT / ".env")
ZABBIX_URL = os.getenv("ZABBIX_URL", "http://SEU_SERVIDOR_INTERNO").rstrip("/")
ZABBIX_USER = SEU_USUARIO
ZABBIX_PASSWORD = SUA_SENHA


class Zabbix:
    def __init__(self):
        self.endpoint = ZABBIX_URL if ZABBIX_URL.endswith("/api_jsonrpc.php") else ZABBIX_URL + "/api_jsonrpc.php"
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
        return data.get("result")

    def login(self):
        try:
            self.auth = self.call("user.login", {"username": ZABBIX_USER, "password": ZABBIX_PASSWORD}, auth=False)
        except RuntimeError:
            self.auth = self.call("user.login", {"user": ZABBIX_USER, "password": ZABBIX_PASSWORD}, auth=False)


def official_rows():
    with DVRS_FILE.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("Nome") and row.get("IP")]


def compact(item):
    return {
        "itemid": item.get("itemid"),
        "name": item.get("name"),
        "key": item.get("key_"),
        "lastvalue": item.get("lastvalue"),
        "lastclock": item.get("lastclock"),
        "value_type": item.get("value_type"),
    }


def main():
    api = Zabbix()
    version = api.call("apiinfo.version", {}, auth=False)
    api.login()
    hosts = api.call(
        "host.get",
        {
            "output": ["hostid", "host", "name", "status", "available", "snmp_available"],
            "selectInterfaces": ["ip", "dns", "type", "main"],
            "selectInventory": ["model", "tag", "location"],
            "selectItems": ["itemid", "name", "key_", "lastvalue", "lastclock", "value_type"],
        },
    )
    by_ip = {}
    for host in hosts:
        for interface in host.get("interfaces", []):
            ip = interface.get("ip") or interface.get("dns")
            if ip:
                by_ip[ip] = host

    dvrs = []
    for row in official_rows():
        ip = row["IP"].strip()
        channels = int((row.get("Canais") or "16").strip())
        host = by_ip.get(ip, {})
        items_by_key = {item["key_"]: compact(item) for item in host.get("items", []) if item.get("key_", "").startswith("dvr.") or item.get("key_") == "icmpping"}
        dvrs.append(
            {
                "hostid": host.get("hostid"),
                "technical_name": host.get("host") or f"DVR-{row['Nome'].strip()}",
                "name": row["Nome"].strip(),
                "location": (row.get("Local") or "").strip(),
                "ip": ip,
                "model": (row.get("Modelo") or "").strip(),
                "channels": channels,
                "official_status": (row.get("Status") or "").strip(),
                "zabbix_available": host.get("available"),
                "snmp_available": host.get("snmp_available"),
                "items_by_key": items_by_key,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "zabbix_api_version": version, "count": len(dvrs), "dvrs": dvrs}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Inventario: {OUT}")
    print(f"DVRs: {len(dvrs)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
