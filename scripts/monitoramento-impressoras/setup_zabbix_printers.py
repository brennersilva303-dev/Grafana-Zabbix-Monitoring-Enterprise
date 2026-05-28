#!/usr/bin/env python3
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import csv
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

ZABBIX_URL = os.getenv("ZABBIX_URL", "http://SEU_SERVIDOR_INTERNO").rstrip("/")
ZABBIX_USER = SEU_USUARIO
ZABBIX_PASSWORD = SUA_SENHA
SNMP_COMMUNITY = os.getenv("SNMP_COMMUNITY", "public")
PRINTERS_FILE = ROOT / "scripts" / "printers_list.txt"
REPORT_FILE = ROOT / "dashboards" / "zabbix-printers-setup-report.json"

GROUP_NAME = "Impressoras"
IGNORED_GROUP_NAME = "Impressoras - Ignoradas"

SNMP_ITEMS = [
    {"name": "Printer sysDescr", "key": "printer.sysdescr", "oid": "1.3.6.1.2.1.1.1.0", "value_type": 4, "delay": "1h"},
    {"name": "SNMP availability", "key": "printer.snmp.available", "oid": "1.3.6.1.2.1.1.3.0", "value_type": 3, "delay": "1m"},
]

SIMPLE_ITEMS = [
    {"name": "ICMP ping", "key": "icmpping", "delay": "1m", "value_type": 3},
]

CALCULATED_ITEMS = [
    {"name": "Printer ping", "key": "printer.ping", "delay": "1m", "value_type": 3, "params": 'last("icmpping")'},
]

TRIGGERS = [
    {"description": "Impressora offline", "expression": "{HOST:printer.ping.last()}=0", "priority": 4},
    {"description": "SNMP indisponivel", "expression": "{HOST:printer.snmp.available.nodata(5m)}=1", "priority": 4},
]


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
        print(f"Validando API Zabbix em {self.endpoint}: {self.call('apiinfo.version', {}, auth=False)}")
        try:
            self.auth = self.call("user.login", {"username": ZABBIX_USER, "password": ZABBIX_PASSWORD}, auth=False)
        except RuntimeError:
            self.auth = self.call("user.login", {"user": ZABBIX_USER, "password": ZABBIX_PASSWORD}, auth=False)
        if not self.auth:
            raise RuntimeError("user.login nao retornou token")
        print("Login Zabbix OK")


def read_printers():
    rows = []
    seen_ips = set()
    name_count = {}
    raw_rows = []
    with PRINTERS_FILE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("Nome") or "").strip()
            ip = (row.get("IP") or "").strip()
            model = (row.get("Modelo") or "").strip()
            status = (row.get("Status") or "").strip()
            if not name or not ip:
                continue
            if ip in seen_ips:
                continue
            seen_ips.add(ip)
            raw_rows.append(
                {
                    "name": name,
                    "sector": (row.get("Setor") or "").strip(),
                    "ip": ip,
                    "model": model,
                    "serial": (row.get("Serial") or "").strip(),
                    "status": status if status in ("Online", "Offline") else "Offline",
                }
            )
            name_count[name] = name_count.get(name, 0) + 1
    for row in raw_rows:
        row["host"] = row["name"] if name_count.get(row["name"], 0) == 1 else f"{row['name']} - {row['ip']}"
        rows.append(row)
    return rows


def ping_ip(ip):
    flag = "-n" if platform.system().lower().startswith("win") else "-c"
    timeout_flag = "-W"
    try:
        return subprocess.run(["ping", flag, "1", timeout_flag, "1", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3).returncode == 0
    except Exception:
        return False


def snmp_probe(ip):
    snmpget = shutil.which("snmpget")
    if snmpget:
        try:
            return subprocess.run(
                [snmpget, "-v2c", "-c", SNMP_COMMUNITY, "-t", "1", "-r", "0", ip, "1.3.6.1.2.1.1.1.0"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            ).returncode == 0
        except Exception:
            return False
    if SNMP_COMMUNITY != "public":
        print("Aviso: snmpget nao encontrado; validacao SNMP via socket interno suporta apenas community public", file=sys.stderr)
        return False
    packet = bytes.fromhex(
        "302602010104067075626c6963a019020104020100020100300e300c06082b060102010101000500"
    )
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        sock.sendto(packet, (ip, 161))
        sock.recvfrom(4096)
        return True
    except Exception:
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass


def get_group(api, name=GROUP_NAME):
    groups = api.call("hostgroup.get", {"filter": {"name": [name]}})
    if groups:
        return groups[0]["groupid"], False
    result = api.call("hostgroup.create", {"name": name})
    return result["groupids"][0], True


def find_template(api):
    patterns = ["Printer", "Impressora", "SNMP Printer", "Template Module Printer", "Generic SNMP"]
    for pattern in patterns:
        templates = api.call("template.get", {"search": {"host": pattern}, "output": ["templateid", "host", "name"]})
        if templates:
            return templates[0]
    return None


def get_host(api, name, ip):
    hosts = api.call("host.get", {"filter": {"host": [name]}, "selectInterfaces": ["interfaceid", "type", "ip", "main"]})
    if hosts:
        return hosts[0]
    legacy = f"PRINTER-{ip}"
    hosts = api.call("host.get", {"filter": {"host": [legacy]}, "selectInterfaces": ["interfaceid", "type", "ip", "main"]})
    if hosts:
        return hosts[0]
    hosts = api.call("host.get", {"search": {"name": ip}, "selectInterfaces": ["interfaceid", "type", "ip", "main"]})
    return hosts[0] if hosts else None


def snmp_interface(host):
    for interface in host.get("interfaces", []):
        if str(interface.get("type")) == "2":
            return interface["interfaceid"]
    return None


def ensure_host(api, groupid, template, printer):
    name = printer["host"]
    visible_name = printer["host"]
    ip = printer["ip"]
    host = get_host(api, name, ip)
    payload = {
        "host": name,
        "name": visible_name,
        "groups": [{"groupid": groupid}],
        "inventory_mode": 0,
        "inventory": {"type": "Printer", "model": printer["model"], "tag": printer["status"], "serialno_a": printer["serial"], "location": printer["sector"]},
        "interfaces": [
            {"type": 2, "main": 1, "useip": 1, "ip": ip, "dns": "", "port": "161", "details": {"version": 2, "community": SNMP_COMMUNITY}}
        ],
    }
    if template:
        payload["templates"] = [{"templateid": template["templateid"]}]
    if host:
        hostid = host["hostid"]
        update = {
            "hostid": hostid,
            "host": name,
            "name": visible_name,
            "groups": [{"groupid": groupid}],
            "inventory_mode": 0,
            "inventory": {"type": "Printer", "model": printer["model"], "tag": printer["status"], "serialno_a": printer["serial"], "location": printer["sector"]},
        }
        if template:
            update["templates"] = [{"templateid": template["templateid"]}]
        api.call("host.update", update)
        interfaceid = snmp_interface(host)
        if not interfaceid:
            res = api.call("hostinterface.create", {"hostid": hostid, **payload["interfaces"][0]})
            interfaceid = res["interfaceids"][0]
        else:
            api.call(
                "hostinterface.update",
                {
                    "interfaceid": interfaceid,
                    "type": 2,
                    "main": 1,
                    "useip": 1,
                    "ip": ip,
                    "dns": "",
                    "port": "161",
                    "details": {"version": 2, "community": SNMP_COMMUNITY},
                },
            )
        return hostid, interfaceid, False
    result = api.call("host.create", payload)
    hostid = result["hostids"][0]
    host = get_host(api, name, ip)
    return hostid, snmp_interface(host), True


def item_exists(api, hostid, key):
    items = api.call("item.get", {"hostids": hostid, "filter": {"key_": key}, "output": ["itemid"]})
    return items[0]["itemid"] if items else None


def ensure_items(api, hostid, interfaceid):
    created = 0
    updated = 0
    for item in SIMPLE_ITEMS:
        existing = item_exists(api, hostid, item["key"])
        params = {"hostid": hostid, "name": item["name"], "key_": item["key"], "type": 3, "value_type": item["value_type"], "delay": item["delay"]}
        if existing:
            api.call("item.update", {"itemid": existing, "name": item["name"], "delay": item["delay"]})
            updated += 1
        else:
            api.call("item.create", params)
            created += 1
    for item in CALCULATED_ITEMS:
        existing = item_exists(api, hostid, item["key"])
        params = {
            "hostid": hostid,
            "name": item["name"],
            "key_": item["key"],
            "type": 15,
            "value_type": item["value_type"],
            "delay": item["delay"],
            "params": item["params"],
        }
        if existing:
            api.call("item.update", {"itemid": existing, "name": item["name"], "delay": item["delay"], "params": item["params"]})
            updated += 1
        else:
            api.call("item.create", params)
            created += 1
    for item in SNMP_ITEMS:
        existing = item_exists(api, hostid, item["key"])
        params = {
            "hostid": hostid,
            "interfaceid": interfaceid,
            "name": item["name"],
            "key_": item["key"],
            "type": 4,
            "snmp_oid": item["oid"],
            "snmp_community": SNMP_COMMUNITY,
            "value_type": item["value_type"],
            "delay": item["delay"],
            "units": item.get("units", ""),
        }
        if existing:
            api.call("item.update", {"itemid": existing, **{k: v for k, v in params.items() if k not in ("hostid",)}})
            updated += 1
        else:
            api.call("item.create", params)
            created += 1
    return created, updated


def trigger_exists(api, hostid, description):
    triggers = api.call("trigger.get", {"hostids": hostid, "filter": {"description": description}, "output": ["triggerid"]})
    return triggers[0]["triggerid"] if triggers else None


def ensure_triggers(api, hostid, host_name):
    created = 0
    updated = 0
    for trigger in TRIGGERS:
        expression = trigger["expression"].replace("HOST", host_name)
        existing = trigger_exists(api, hostid, trigger["description"])
        params = {"description": trigger["description"], "expression": expression, "priority": trigger["priority"]}
        if existing:
            api.call("trigger.update", {"triggerid": existing, **params})
            updated += 1
        else:
            api.call("trigger.create", params)
            created += 1
    return created, updated


def cleanup_non_official_hosts(api, groupid, ignored_groupid, official_names, official_ips):
    hosts = api.call(
        "host.get",
        {
            "groupids": groupid,
            "output": ["hostid", "host", "name"],
            "selectInterfaces": ["ip", "dns", "type"],
            "selectGroups": ["groupid", "name"],
        },
    )
    moved = 0
    for host in hosts:
        ips = {interface.get("ip") for interface in host.get("interfaces", []) if interface.get("ip")}
        if host.get("host") in official_names or host.get("name") in official_names or ips.intersection(official_ips):
            continue
        api.call("host.update", {"hostid": host["hostid"], "groups": [{"groupid": ignored_groupid}]})
        moved += 1
    return moved


def main():
    api = Zabbix()
    api.login()
    printers = read_printers()
    groupid, group_created = get_group(api)
    ignored_groupid, _ = get_group(api, IGNORED_GROUP_NAME)
    template = find_template(api)
    print(f"Grupo: {GROUP_NAME} ({'criado' if group_created else 'existente'})")
    print(f"Template aplicado: {template['name'] if template else 'nenhum; criando itens manuais'}")

    summary = {
        "total_ips_read": len([line for line in PRINTERS_FILE.read_text().splitlines()[1:] if line.strip()]),
        "total_unique_ips": len(printers),
        "official_printers": len(printers),
        "ignored_old_hosts": 0,
        "hosts_created": 0,
        "hosts_updated": 0,
        "hosts_offline": 0,
        "hosts_without_snmp": 0,
        "items_created": 0,
        "items_updated": 0,
        "triggers_created": 0,
        "triggers_updated": 0,
        "template": template,
        "printers": [],
    }

    official_names = {printer["host"] for printer in printers} | {printer["name"] for printer in printers}
    official_ips = {printer["ip"] for printer in printers}
    summary["ignored_old_hosts"] = cleanup_non_official_hosts(api, groupid, ignored_groupid, official_names, official_ips)

    for printer in printers:
        host_name = printer["host"]
        ip = printer["ip"]
        ping_ok = ping_ip(ip)
        snmp_ok = snmp_probe(ip)
        if not ping_ok:
            summary["hosts_offline"] += 1
        if not snmp_ok:
            summary["hosts_without_snmp"] += 1
        hostid, interfaceid, created = ensure_host(api, groupid, template, printer)
        if created:
            summary["hosts_created"] += 1
        else:
            summary["hosts_updated"] += 1
        item_created, item_updated = ensure_items(api, hostid, interfaceid)
        trigger_created, trigger_updated = ensure_triggers(api, hostid, host_name)
        summary["items_created"] += item_created
        summary["items_updated"] += item_updated
        summary["triggers_created"] += trigger_created
        summary["triggers_updated"] += trigger_updated
        summary["printers"].append({"ip": ip, "host": host_name, "name": printer["name"], "sector": printer["sector"], "model": printer["model"], "serial": printer["serial"], "status": printer["status"], "hostid": hostid, "ping_ok": ping_ok, "snmp_ok": snmp_ok})
        print(f"{printer['name']} ({ip}): {'criado' if created else 'atualizado'} | ping={ping_ok} | snmp={snmp_ok}")

    REPORT_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("printers", "template")}, indent=2))
    print(f"Relatorio: {REPORT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
