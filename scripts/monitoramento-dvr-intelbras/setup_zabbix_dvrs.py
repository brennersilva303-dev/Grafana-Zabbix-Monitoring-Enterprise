#!/usr/bin/env python3
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DVRS_FILE = ROOT / "scripts" / "dvrs_list.csv"
OID_FILE = ROOT / "config" / "oids_intelbras_imhdx3116.json"
REPORT_FILE = ROOT / "dashboards" / "zabbix-dvrs-setup-report.json"
GROUP_NAME = "DVRs Intelbras"
SNMP_ITEM_TYPE = 20
SIMPLE_CHECK_TYPE = 3
SIA_IP_CAMERAS = [
    {"name": "SIA-IP-01", "location": "SIA-IP", "ip": "SEU_IP_PRIVADO"},
    {"name": "SIA-IP-02", "location": "SIA-IP", "ip": "SEU_IP_PRIVADO"},
    {"name": "SIA-IP-03", "location": "SIA-IP", "ip": "SEU_IP_PRIVADO"},
    {"name": "SIA-IP-04", "location": "SIA-IP", "ip": "SEU_IP_PRIVADO"},
    {"name": "SIA-IP-05", "location": "SIA-IP", "ip": "SEU_IP_PRIVADO"},
]


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env(ROOT / ".env")
ZABBIX_URL = os.getenv("ZABBIX_URL", "http://SEU_SERVIDOR_INTERNO").rstrip("/")
ZABBIX_USER = SEU_USUARIO
ZABBIX_PASSWORD = SUA_SENHA
SNMP_COMMUNITY = os.getenv("DVR_SNMP_COMMUNITY", "Publico")
SNMP_PORT = os.getenv("DVR_SNMP_PORT", "161")
ZABBIX_PROXY_NAME = os.getenv("ZABBIX_PROXY_NAME", "zabbixProxy")


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


def read_dvrs():
    with DVRS_FILE.open(newline="", encoding="utf-8") as handle:
        rows = []
        for row in csv.DictReader(handle):
            rows.append({
                "name": (row.get("Nome") or "").strip(),
                "location": (row.get("Local") or "").strip(),
                "ip": (row.get("IP") or "").strip(),
                "model": (row.get("Modelo") or "").strip(),
                "channels": int((row.get("Canais") or "16").strip()),
                "status": (row.get("Status") or "").strip() or "Online",
            })
        return [row for row in rows if row["name"] and row["ip"]]


def ping_ip(ip):
    try:
        return subprocess.run(["ping", "-c", "1", "-W", "1", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3).returncode == 0
    except Exception:
        return False


def snmp_probe(ip):
    return None


def is_nvd(dvr):
    return "NVD" in dvr.get("model", "").upper()


def hdd_oids_for(dvr, default_hdd_oids):
    if not is_nvd(dvr):
        return default_hdd_oids
    return {
        "device": "1.3.6.1.4.1.1004849.2.4.1.1.4.1",
        "status": "1.3.6.1.4.1.1004849.2.4.1.1.2.1",
        "error": "1.3.6.1.4.1.1004849.2.4.1.1.3.1",
        "capacity": "1.3.6.1.4.1.1004849.2.4.1.1.6.1",
        "used": "1.3.6.1.4.1.1004849.2.4.1.1.7.1",
        "free_percent": "1.3.6.1.4.1.1004849.2.4.3.0",
        "volume_status": "1.3.6.1.4.1.1004849.2.4.1.1.5.1",
        "capacity_units": "GB",
    }


def get_group(api):
    groups = api.call("hostgroup.get", {"filter": {"name": [GROUP_NAME]}})
    if groups:
        return groups[0]["groupid"], False
    result = api.call("hostgroup.create", {"name": GROUP_NAME})
    return result["groupids"][0], True


def get_proxy(api):
    proxies = api.call("proxy.get", {"filter": {"host": [ZABBIX_PROXY_NAME]}, "output": ["proxyid", "host"]})
    if not proxies:
        raise RuntimeError(f"Proxy Zabbix nao encontrado: {ZABBIX_PROXY_NAME}")
    return proxies[0]


def get_host(api, host_name, ip):
    hosts = api.call("host.get", {"filter": {"host": [host_name]}, "selectInterfaces": ["interfaceid", "type", "ip"]})
    if hosts:
        return hosts[0]
    interfaces = api.call(
        "hostinterface.get",
        {"filter": {"ip": [ip]}, "output": ["interfaceid", "hostid", "type", "ip"], "selectHosts": ["hostid", "host", "name"]},
    )
    if interfaces and interfaces[0].get("hosts"):
        hostid = interfaces[0]["hosts"][0]["hostid"]
        hosts = api.call("host.get", {"hostids": hostid, "output": ["hostid", "host", "name"], "selectInterfaces": ["interfaceid", "type", "ip"]})
        return hosts[0] if hosts else None
    return None


def snmp_interface(host):
    for interface in host.get("interfaces", []):
        if str(interface.get("type")) == "2":
            return interface["interfaceid"]
    return None


def ensure_host(api, groupid, proxy, dvr):
    host_name = f"DVR-{dvr['name']}"
    host = get_host(api, host_name, dvr["ip"])
    inventory = {"type": "DVR", "model": dvr["model"], "location": dvr["location"], "tag": dvr["status"]}
    interface = {"type": 2, "main": 1, "useip": 1, "ip": dvr["ip"], "dns": "", "port": SNMP_PORT, "details": {"version": 2, "community": SNMP_COMMUNITY}}
    if host:
        api.call(
            "host.update",
            {
                "hostid": host["hostid"],
                "host": host_name,
                "name": dvr["name"],
                "groups": [{"groupid": groupid}],
                "proxy_hostid": proxy["proxyid"],
                "inventory_mode": 0,
                "inventory": inventory,
            },
        )
        interfaceid = snmp_interface(host)
        if interfaceid:
            api.call("hostinterface.update", {"interfaceid": interfaceid, **interface})
        else:
            result = api.call("hostinterface.create", {"hostid": host["hostid"], **interface})
            interfaceid = result["interfaceids"][0]
        return host["hostid"], interfaceid, False
    result = api.call(
        "host.create",
        {
            "host": host_name,
            "name": dvr["name"],
            "groups": [{"groupid": groupid}],
            "proxy_hostid": proxy["proxyid"],
            "interfaces": [interface],
            "inventory_mode": 0,
            "inventory": inventory,
        },
    )
    hostid = result["hostids"][0]
    host = get_host(api, host_name, dvr["ip"])
    return hostid, snmp_interface(host), True


def agent_interface(host):
    for interface in host.get("interfaces", []):
        if str(interface.get("type")) == "1":
            return interface["interfaceid"]
    return None


def ensure_icmp_host(api, groupid, proxy, camera):
    host_name = camera["name"]
    host = get_host(api, host_name, camera["ip"])
    inventory = {"type": "Camera IP", "model": "ICMP Ping", "location": camera["location"], "tag": "Online"}
    interface = {"type": 1, "main": 1, "useip": 1, "ip": camera["ip"], "dns": "", "port": "10050"}
    if host:
        api.call(
            "host.update",
            {
                "hostid": host["hostid"],
                "host": host_name,
                "name": camera["name"],
                "groups": [{"groupid": groupid}],
                "proxy_hostid": proxy["proxyid"],
                "inventory_mode": 0,
                "inventory": inventory,
            },
        )
        interfaceid = agent_interface(host)
        if interfaceid:
            api.call("hostinterface.update", {"interfaceid": interfaceid, **interface})
        else:
            result = api.call("hostinterface.create", {"hostid": host["hostid"], **interface})
            interfaceid = result["interfaceids"][0]
        return host["hostid"], interfaceid, False
    result = api.call(
        "host.create",
        {
            "host": host_name,
            "name": camera["name"],
            "groups": [{"groupid": groupid}],
            "proxy_hostid": proxy["proxyid"],
            "interfaces": [interface],
            "inventory_mode": 0,
            "inventory": inventory,
        },
    )
    hostid = result["hostids"][0]
    host = get_host(api, host_name, camera["ip"])
    return hostid, agent_interface(host), True


def item_id(api, hostid, key):
    items = api.call("item.get", {"hostids": hostid, "filter": {"key_": key}, "output": ["itemid"]})
    return items[0]["itemid"] if items else None


def ensure_item(api, params):
    existing = item_id(api, params["hostid"], params["key_"])
    if existing:
        update = {"itemid": existing, **{k: v for k, v in params.items() if k != "hostid"}}
        if str(params.get("type")) not in {"4", str(SNMP_ITEM_TYPE)}:
            update["snmp_oid"] = ""
        api.call("item.update", update)
        return existing, False
    result = api.call("item.create", params)
    return result["itemids"][0], True


def trigger_id(api, hostid, description):
    triggers = api.call("trigger.get", {"hostids": hostid, "filter": {"description": description}, "output": ["triggerid"]})
    return triggers[0]["triggerid"] if triggers else None


def ensure_trigger(api, hostid, description, expression, priority):
    existing = trigger_id(api, hostid, description)
    payload = {"description": description, "expression": expression, "priority": priority}
    if existing:
        api.call("trigger.update", {"triggerid": existing, **payload})
        return False
    api.call("trigger.create", payload)
    return True


def disable_item(api, hostid, key):
    existing = item_id(api, hostid, key)
    if existing:
        api.call("item.update", {"itemid": existing, "status": 1})
        return True
    return False


def main():
    api = Zabbix()
    api.login()
    groupid, group_created = get_group(api)
    proxy = get_proxy(api)
    oids = json.loads(OID_FILE.read_text(encoding="utf-8"))
    device_oids = oids["device"]
    system_oids = oids["system"]
    channel_oids = oids["all_channel_status"]
    default_hdd_oids = oids["hdd"]
    report = {"group": GROUP_NAME, "group_created": group_created, "proxy": proxy, "dvrs": [], "items_created": 0, "items_updated": 0, "triggers_created": 0}

    for dvr in read_dvrs():
        hostid, interfaceid, created = ensure_host(api, groupid, proxy, dvr)
        ping_ok = ping_ip(dvr["ip"])
        snmp_ok = snmp_probe(dvr["ip"])
        host = f"DVR-{dvr['name']}"
        hdd_oids = hdd_oids_for(dvr, default_hdd_oids)
        item_defs = [
            {"hostid": hostid, "interfaceid": interfaceid, "name": "dvr.snmp.sysdescr", "key_": "dvr.snmp.sysdescr", "type": SNMP_ITEM_TYPE, "snmp_oid": system_oids["sysdescr"], "snmp_community": SNMP_COMMUNITY, "value_type": 4, "delay": "1h"},
            {"hostid": hostid, "interfaceid": interfaceid, "name": "dvr.snmp.uptime", "key_": "dvr.snmp.uptime", "type": SNMP_ITEM_TYPE, "snmp_oid": system_oids["sysuptime"], "snmp_community": SNMP_COMMUNITY, "value_type": 3, "delay": "1m"},
            {"hostid": hostid, "interfaceid": interfaceid, "name": "dvr.device.model", "key_": "dvr.device.model", "type": SNMP_ITEM_TYPE, "snmp_oid": device_oids["model"], "snmp_community": SNMP_COMMUNITY, "value_type": 4, "delay": "1h"},
            {"hostid": hostid, "interfaceid": interfaceid, "name": "dvr.online", "key_": "dvr.online", "type": SNMP_ITEM_TYPE, "snmp_oid": device_oids["online"], "snmp_community": SNMP_COMMUNITY, "value_type": 3, "delay": "1m"},
        ]
        for channel in range(1, dvr["channels"] + 1):
            if is_nvd(dvr):
                name_oid = f"1.3.6.1.4.1.1004849.2.SEU_IP_PRIVADO.4.{channel}"
                item_defs.append({"hostid": hostid, "name": f"dvr.channel.status[{channel}]", "key_": f"dvr.channel.status[{channel}]", "type": 15, "value_type": 3, "delay": "1m", "params": "last(dvr.online)"})
            else:
                index = channel + int(channel_oids.get("index_offset", -1))
                status_oid = f"{channel_oids['base_status_int']}.{index}"
                name_oid = f"{channel_oids['base_name']}.{channel}"
                item_defs.append({"hostid": hostid, "interfaceid": interfaceid, "name": f"dvr.channel.status[{channel}]", "key_": f"dvr.channel.status[{channel}]", "type": SNMP_ITEM_TYPE, "snmp_oid": status_oid, "snmp_community": SNMP_COMMUNITY, "value_type": 3, "delay": "1m"})
            item_defs.append({"hostid": hostid, "name": f"dvr.channel.video_loss[{channel}]", "key_": f"dvr.channel.video_loss[{channel}]", "type": 15, "value_type": 3, "delay": "1m", "params": f"1-last(dvr.channel.status[{channel}])"})
            item_defs.append({"hostid": hostid, "interfaceid": interfaceid, "name": f"dvr.channel.name[{channel}]", "key_": f"dvr.channel.name[{channel}]", "type": SNMP_ITEM_TYPE, "snmp_oid": name_oid, "snmp_community": SNMP_COMMUNITY, "value_type": 4, "delay": "1h"})
        ok_terms = [f"last(dvr.channel.status[{channel}])" for channel in range(1, dvr["channels"] + 1)]
        item_defs.extend(
            [
                {"hostid": hostid, "name": "dvr.cameras.ok_count", "key_": "dvr.cameras.ok_count", "type": 15, "value_type": 3, "delay": "1m", "params": "+".join(ok_terms)},
                {"hostid": hostid, "name": "dvr.cameras.total", "key_": "dvr.cameras.total", "type": 15, "value_type": 3, "delay": "1h", "params": str(dvr["channels"])},
                {"hostid": hostid, "name": "dvr.total_count", "key_": "dvr.total_count", "type": 15, "value_type": 3, "delay": "1m", "params": "last(dvr.online)+1-last(dvr.online)"},
                {"hostid": hostid, "name": "dvr.online_count", "key_": "dvr.online_count", "type": 15, "value_type": 3, "delay": "1m", "params": "last(dvr.online)"},
                {"hostid": hostid, "name": "dvr.offline_count", "key_": "dvr.offline_count", "type": 15, "value_type": 3, "delay": "1m", "params": "1-last(dvr.online)"},
                {"hostid": hostid, "interfaceid": interfaceid, "name": "dvr.hdd.device", "key_": "dvr.hdd.device", "type": SNMP_ITEM_TYPE, "snmp_oid": hdd_oids["device"], "snmp_community": SNMP_COMMUNITY, "value_type": 4, "delay": "1h"},
                {"hostid": hostid, "interfaceid": interfaceid, "name": "dvr.hdd.status", "key_": "dvr.hdd.status", "type": SNMP_ITEM_TYPE, "snmp_oid": hdd_oids["status"], "snmp_community": SNMP_COMMUNITY, "value_type": 3, "delay": "1m"},
                {"hostid": hostid, "interfaceid": interfaceid, "name": "dvr.hdd.error", "key_": "dvr.hdd.error", "type": SNMP_ITEM_TYPE, "snmp_oid": hdd_oids["error"], "snmp_community": SNMP_COMMUNITY, "value_type": 3, "delay": "1m"},
                {"hostid": hostid, "name": "dvr.hdd.ok", "key_": "dvr.hdd.ok", "type": 15, "value_type": 3, "delay": "1m", "params": "last(dvr.hdd.status)*(1-last(dvr.hdd.error))"},
                {"hostid": hostid, "interfaceid": interfaceid, "name": "dvr.hdd.capacity", "key_": "dvr.hdd.capacity", "type": SNMP_ITEM_TYPE, "snmp_oid": hdd_oids["capacity"], "snmp_community": SNMP_COMMUNITY, "value_type": 3, "delay": "5m", "units": hdd_oids.get("capacity_units", "MB")},
                {"hostid": hostid, "interfaceid": interfaceid, "name": "dvr.hdd.used", "key_": "dvr.hdd.used", "type": SNMP_ITEM_TYPE, "snmp_oid": hdd_oids["used"], "snmp_community": SNMP_COMMUNITY, "value_type": 3, "delay": "5m", "units": hdd_oids.get("capacity_units", "MB")},
                {"hostid": hostid, "interfaceid": interfaceid, "name": "dvr.hdd.free_percent", "key_": "dvr.hdd.free_percent", "type": SNMP_ITEM_TYPE, "snmp_oid": hdd_oids["free_percent"], "snmp_community": SNMP_COMMUNITY, "value_type": 3, "delay": "5m", "units": "%"},
                {"hostid": hostid, "interfaceid": interfaceid, "name": "dvr.hdd.volume_status", "key_": "dvr.hdd.volume_status", "type": SNMP_ITEM_TYPE, "snmp_oid": hdd_oids["volume_status"], "snmp_community": SNMP_COMMUNITY, "value_type": 4, "delay": "5m"},
            ]
        )

        keys = {}
        for item in item_defs:
            iid, was_created = ensure_item(api, item)
            keys[item["key_"]] = iid
            report["items_created" if was_created else "items_updated"] += 1

        trigger_defs = [
            ("DVR offline", f"{{{host}:dvr.online.nodata(5m)}}=1 or {{{host}:dvr.online.last()}}<>1", 4),
            ("SNMP DVR sem resposta", f"{{{host}:dvr.snmp.uptime.nodata(5m)}}=1", 3),
            ("HD ausente", f"{{{host}:dvr.hdd.status.nodata(5m)}}=1 or {{{host}:dvr.hdd.status.last()}}<>1", 4),
            ("HD do DVR com falha", f"{{{host}:dvr.hdd.error.last()}}<>0", 4),
        ]
        for channel in range(1, dvr["channels"] + 1):
            trigger_defs.append((f"Canal {channel:02d} com perda de video", f"{{{host}:dvr.channel.status[{channel}].min(3m)}}=0", 4))
        for description, expression, priority in trigger_defs:
            if ensure_trigger(api, hostid, description, expression, priority):
                report["triggers_created"] += 1

        disabled = []
        for legacy_key in ("dvr.ping", "dvr.status.online", "dvr.sysdescr"):
            if disable_item(api, hostid, legacy_key):
                disabled.append(legacy_key)
        report["dvrs"].append({"host": host, "hostid": hostid, "created": created, "ip": dvr["ip"], "proxy": proxy, "ping_ok_from_server": ping_ok, "snmp_checked_by_proxy": True, "items_by_key": keys, "disabled_legacy_items": disabled})
        print(f"{host} ({dvr['ip']}): {'criado' if created else 'atualizado'} | proxy={proxy['host']} | community={SNMP_COMMUNITY}")

    for camera in SIA_IP_CAMERAS:
        hostid, interfaceid, created = ensure_icmp_host(api, groupid, proxy, camera)
        ping_ok = ping_ip(camera["ip"])
        item_defs = [
            {"hostid": hostid, "interfaceid": interfaceid, "name": "icmpping", "key_": "icmpping", "type": SIMPLE_CHECK_TYPE, "value_type": 3, "delay": "1m"},
        ]
        keys = {}
        for item in item_defs:
            iid, was_created = ensure_item(api, item)
            keys[item["key_"]] = iid
            report["items_created" if was_created else "items_updated"] += 1
        if ensure_trigger(api, hostid, "Camera IP offline", f"{{{camera['name']}:icmpping.max(3m)}}=0", 4):
            report["triggers_created"] += 1
        report["dvrs"].append({"host": camera["name"], "hostid": hostid, "created": created, "ip": camera["ip"], "proxy": proxy, "ping_ok_from_server": ping_ok, "items_by_key": keys})
        print(f"{camera['name']} ({camera['ip']}): {'criado' if created else 'atualizado'} | proxy={proxy['host']} | ICMP")

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Relatorio: {REPORT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
