#!/usr/bin/env python3
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://SEU_SERVIDOR_INTERNO").rstrip("/")
ZABBIX_USER = SEU_USUARIO
ZABBIX_PASSWORD = SUA_SENHA
PRINTERS_FILE = ROOT / "scripts" / "printers_list.txt"
OUTPUT_JSON = ROOT / "dashboards" / "printers-inventory.json"
OUTPUT_CSV = ROOT / "dashboards" / "printers-inventory.csv"
SUMMARY = ROOT / "dashboards" / "printers-summary.json"


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
        print(f"API Zabbix: {self.call('apiinfo.version', {}, auth=False)}")
        try:
            self.auth = self.call("user.login", {"username": ZABBIX_USER, "password": ZABBIX_PASSWORD}, auth=False)
        except RuntimeError:
            self.auth = self.call("user.login", {"user": ZABBIX_USER, "password": ZABBIX_PASSWORD}, auth=False)
        if not self.auth:
            raise RuntimeError("user.login nao retornou token")


def read_official():
    rows = []
    with PRINTERS_FILE.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "name": (row.get("Nome") or "").strip(),
                    "sector": (row.get("Setor") or "").strip(),
                    "model": (row.get("Modelo") or "").strip(),
                    "serial": (row.get("Serial") or "").strip(),
                    "ip": (row.get("IP") or "").strip(),
                    "official_status": (row.get("Status") or "").strip(),
                }
            )
    return [row for row in rows if row["name"] and row["ip"]]


def compact(item):
    return {
        "itemid": item.get("itemid"),
        "name": item.get("name"),
        "key": item.get("key_"),
        "lastvalue": item.get("lastvalue"),
        "lastclock": item.get("lastclock"),
        "status": item.get("status"),
        "value_type": item.get("value_type"),
    }


def main():
    api = Zabbix()
    version = api.call("apiinfo.version", {}, auth=False)
    api.login()
    official = read_official()
    hosts = api.call(
        "host.get",
        {
            "output": ["hostid", "host", "name", "status", "available", "snmp_available"],
            "selectInterfaces": ["ip", "dns", "type", "main"],
            "selectInventory": ["model", "tag", "serialno_a", "location"],
            "selectItems": ["itemid", "name", "key_", "lastvalue", "lastclock", "status", "value_type"],
        },
    )
    by_ip = {}
    for host in hosts:
        for interface in host.get("interfaces", []):
            ip = interface.get("ip") or interface.get("dns")
            if ip:
                by_ip[ip] = host

    printers = []
    snmp_items = 0
    for row in official:
        host = by_ip.get(row["ip"], {})
        by_key = {}
        for item in host.get("items", []):
            if item.get("key_") in ("printer.ping", "icmpping", "printer.snmp.available"):
                by_key[item["key_"]] = compact(item)
                snmp_items += 1
        printers.append(
            {
                "hostid": host.get("hostid"),
                "technical_name": host.get("host") or row["name"],
                "name": row["name"],
                "sector": row["sector"],
                "model": row["model"],
                "serial": row["serial"],
                "ip": row["ip"],
                "official_status": row["official_status"],
                "zabbix_available": host.get("available"),
                "snmp_available": host.get("snmp_available"),
                "items_by_key": by_key,
            }
        )

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zabbix_api_version": version,
        "zabbix_url": api.endpoint,
        "count": len(printers),
        "snmp_items_found": snmp_items,
        "printers": printers,
    }
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Nome", "Setor", "Modelo", "Serial", "IP", "Status"])
        writer.writeheader()
        for row in official:
            writer.writerow({"Nome": row["name"], "Setor": row["sector"], "Modelo": row["model"], "Serial": row["serial"], "IP": row["ip"], "Status": row["official_status"]})
    SUMMARY.write_text(json.dumps({"printers": len(printers), "snmp_items_found": snmp_items}, indent=2) + "\n", encoding="utf-8")
    print(f"Inventario JSON: {OUTPUT_JSON}")
    print(f"Inventario CSV: {OUTPUT_CSV}")
    print(f"Total oficial: {len(printers)}")
    return 0 if len(printers) == 41 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro na descoberta Zabbix: {exc}", file=sys.stderr)
        sys.exit(1)
