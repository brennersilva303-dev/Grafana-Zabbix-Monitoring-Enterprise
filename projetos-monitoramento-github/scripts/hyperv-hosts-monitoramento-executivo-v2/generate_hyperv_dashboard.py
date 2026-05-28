#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
DASHBOARD = ROOT / "dashboard-hyperv-hosts.json"
DISCOVERY = LOGS / "hyperv-items-discovery.json"
VALIDATION = LOGS / "dashboard-data-validation.json"
RENDER_VALIDATION = LOGS / "dashboard-render-validation.json"
HOSTS = ["HYPERV_HOST_A", "HYPERV-HYPERV_HOST_B"]
HOSTNAME_FALLBACK = {
    "HYPERV_HOST_A": "HYPERV_HOST_A",
    "HYPERV-HYPERV_HOST_B": "HYPERV-HYPERV_HOST_B",
}

FALLBACK_FILTERS = {
    "availability": "/^(Zabbix agent ping|Agent availability|ICMP ping)$/",
    "uptime": "/^(System uptime|Uptime)$/",
    "cpu_user": "/^(CPU user time)$/",
    "cpu_privileged": "/^(CPU privileged time)$/",
    "cpu_interrupt": "/^(CPU interrupt time)$/",
    "cpu_dpc": "/^(CPU DPC time)$/",
    "cpu_queue": "/^(CPU queue length)$/",
    "cpu_current": "/(Hyper-V Hypervisor|Logical Processor|Root Virtual Processor|Virtual Processor|Total Run Time|Processor Time)/",
    "cpu_hyperv_logical_total": "/(Hyper-V Hypervisor Logical Processor.*Total Run Time|Logical Processor.*Total Run Time)/",
    "cpu_hyperv_root_total": "/(Hyper-V Hypervisor Root Virtual Processor.*Total Run Time|Root Virtual Processor.*Total Run Time|Hyper-V Hypervisor Root Partition.*Total Run Time)/",
    "cpu_hyperv_virtual_total": "/(Hyper-V Hypervisor Virtual Processor.*Total Run Time|Virtual Processor.*Total Run Time)/",
    "cpu_processor_total": "/(Processor Information.*Processor Time|Processor\\(_Total\\).*Processor Time)/",
    "cpu_utilization": "/^(CPU utilization|Processor utilization|Utilization of processor time|CPU usage)$/",
    "memory_used": "/(vm\\.memory\\.size\\[used\\]|Used memory|Memory.*used)/",
    "memory_available": "/(vm\\.memory\\.size\\[available\\]|Available memory|Free memory)/",
    "memory_total": "/(vm\\.memory\\.size\\[total\\]|Total memory|Memory total)/",
    "disk_percent": "/^(.*Space utilization)$/",
    "disk_used": "/^(.*Used space)$/",
    "disk_total": "/^(.*Total space)$/",
    "net_in": "/(Bits received|Incoming network traffic|Interface.*received|Network.*In)/",
    "net_out": "/(Bits sent|Outgoing network traffic|Interface.*sent|Network.*Out)/",
    "net_errors": "/(Errors|Error packets)/",
    "net_drops": "/(Dropped|Drops|discarded|Packets dropped)/",
    "net_interfaces": "/(net\\.if\\.|Bits received|Bits sent|Interface|Network|vEthernet|Hyper-V Virtual Ethernet Adapter|NIC Team|Team|iSCSI|Ethernet)/",
    "hyperv_services": "/(Hyper-V|vmms|vmcompute|vmictimesync|Virtual Machine Management)/",
}


def load_discovery():
    if DISCOVERY.exists():
        return json.loads(DISCOVERY.read_text())
    return {"hosts": {}, "missing": {h: list(FALLBACK_FILTERS) for h in HOSTS}, "problems": ["Discovery nao executada. Usando filtros padrao."]}


def load_validation():
    if VALIDATION.exists():
        return json.loads(VALIDATION.read_text())
    return {"hosts": {}}


VALIDATED = {}
RENDERED = {}


def load_render_validation():
    if RENDER_VALIDATION.exists():
        return json.loads(RENDER_VALIDATION.read_text())
    return {"panels_without_frames": []}


def panel_failed_render(host_key, category):
    panel = {"net_in": "net_in", "net_out": "net_out"}.get(category, category)
    for item in RENDERED.get("panels_without_frames", []):
        if item.get("host") == host_key and item.get("panel") == panel:
            return True
    for item in RENDERED.get("panels_rendered_with_data", []):
        if item.get("host") == host_key and item.get("panel") == panel and item.get("status") in ("api_lastvalue_no_frames", "zabbix_get_validated_no_history"):
            return True
    return False


def selected_item(host_key, category):
    host = VALIDATED.get("hosts", {}).get(host_key, {})
    selected = host.get("selected", {})
    if category == "availability":
        category = "status"
    if category == "disk_percent":
        item = selected.get("disk_all_percent") or selected.get("disk_percent")
        if isinstance(item, list):
            return item
        return item
    return selected.get(category)


def disk_volumes(host_key):
    return VALIDATED.get("hosts", {}).get(host_key, {}).get("selected", {}).get("disk_volumes", []) or []


def item_has_data(host_key, category):
    item = selected_item(host_key, category)
    if isinstance(item, list):
        return bool(item)
    return item is not None


def item_can_query(item):
    return bool(item and not item.get("synthetic") and int(item.get("lastclock") or 0) > 0)


def selected_items(host_key, category, name_pattern=None):
    item = selected_item(host_key, category)
    items = item if isinstance(item, list) else [item]
    items = [i for i in items if i]
    if name_pattern:
        compiled = re.compile(name_pattern, re.I)
        items = [i for i in items if compiled.search(i.get("name", ""))]
    return items


def category_can_query(host_key, category, name_pattern=None):
    return any(item_can_query(item) for item in selected_items(host_key, category, name_pattern))


def fmt_value(item, unit=None):
    if not item:
        return "sem valor"
    raw = item.get("lastvalue")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return str(raw)
    if unit == "bytes" or item.get("units") == "B":
        for suffix in ["B", "KB", "MB", "GB", "TB"]:
            if abs(value) < 1024 or suffix == "TB":
                return f"{value:.1f} {suffix}"
            value /= 1024
    if unit == "percent" or item.get("units") == "%":
        return f"{value:.2f}%"
    if unit == "bps" or item.get("units") == "bps":
        for suffix in ["bps", "Kbps", "Mbps", "Gbps", "Tbps"]:
            if abs(value) < 1000 or suffix == "Tbps":
                return f"{value:.1f} {suffix}"
            value /= 1000
    if unit == "s":
        days = int(value // 86400)
        hours = int((value % 86400) // 3600)
        return f"{days}d {hours}h"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def fmt_clock(value):
    try:
        clock = int(value or 0)
    except (TypeError, ValueError):
        return ""
    if clock <= 0:
        return ""
    return datetime.fromtimestamp(clock).strftime("%Y-%m-%d %H:%M:%S")


def short_text(value, limit=58):
    text = str(value or "").replace("|", "/").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def interface_label(item):
    name = item.get("name", "")
    key = item.get("key_", "")
    match = re.search(r'Interface\s+(.+?):\s+Bits\s+(received|sent)', name, re.I)
    if match:
        return short_text(match.group(1), 54)
    match = re.search(r'net\.if\.(?:in|out)\["?([^",\]]+)', key, re.I)
    if match:
        return short_text(match.group(1), 54)
    return short_text(name or key, 54)


def traffic_direction(item):
    haystack = f"{item.get('name', '')} {item.get('key_', '')}".lower()
    if "bits sent" in haystack or "net.if.out" in haystack or "outgoing" in haystack:
        return "Saida"
    if "bits received" in haystack or "net.if.in" in haystack or "incoming" in haystack:
        return "Entrada"
    return "-"


def online_hosts_count():
    total = 0
    for host_key in HOSTS:
        status = selected_item(host_key, "availability") or {}
        if str(status.get("lastvalue")) == "1":
            total += 1
    return total


def total_active_problems():
    return sum(active_problems_count(host_key) for host_key in HOSTS)


def disk_status(percent):
    try:
        value = float(percent)
    except (TypeError, ValueError):
        return "sem dado"
    if value >= 90:
        return "critico"
    if value >= 80:
        return "atencao"
    return "normal"


def disk_volume_percent(volume):
    item = volume.get("pused")
    try:
        return float(item.get("lastvalue")) if item else None
    except (TypeError, ValueError):
        return None


def critical_disk(host_key):
    volumes = [v for v in disk_volumes(host_key) if disk_volume_percent(v) is not None]
    if not volumes:
        return None
    return max(volumes, key=disk_volume_percent)


def disk_inventory_content(host_key):
    rows = [
        "| Host | Volume/disco | Uso % | Usado | Total | Livre | Ultima coleta | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for volume in disk_volumes(host_key):
        percent = disk_volume_percent(volume)
        pused = f"{percent:.2f}%" if percent is not None else "sem dado"
        free_value = None
        if volume.get("free"):
            free_value = fmt_value(volume.get("free"), "bytes")
        elif volume.get("total") and volume.get("used"):
            try:
                free_value = fmt_value({"lastvalue": float(volume["total"]["lastvalue"]) - float(volume["used"]["lastvalue"]), "units": "B"}, "bytes")
            except (TypeError, ValueError):
                free_value = None
        rows.append(
            "| "
            + " | ".join([
                host_key,
                f"`{volume.get('volume', '')}`",
                pused,
                fmt_value(volume.get("used"), "bytes") if volume.get("used") else "sem dado",
                fmt_value(volume.get("total"), "bytes") if volume.get("total") else "sem dado",
                free_value or "sem dado",
                fmt_clock(volume.get("pused", {}).get("lastclock") or volume.get("used", {}).get("lastclock")),
                disk_status(percent),
            ])
            + " |"
        )
    if len(rows) == 2:
        rows.append(f"| {host_key} | sem volume validado | - | - | - | - | - | sem dado |")
    return "\n".join(rows)


def disk_inventory_panel(pid, title, x, y, w, h, host_key):
    return text_panel(pid, title, x, y, w, h, disk_inventory_content(host_key))


def critical_disk_panel(pid, title, x, y, w, uid, discovery, host_key):
    volume = critical_disk(host_key)
    if not volume:
        return text_panel(pid, title, x, y, w, 5, "Sem volume validado.")
    value = disk_volume_percent(volume)
    item = volume.get("pused") or {}
    target = host_item_target(uid, discovery, host_key, "disk_percent", name_pattern=f"^{re.escape(item.get('name', ''))}$")
    panel = stat_panel(
        pid,
        title,
        x,
        y,
        w,
        target,
        "percent",
        thresholds(disk=True),
        no_value=f"{volume.get('volume')}: {value:.2f}%" if value is not None else "-",
        description=f"Volume mais cheio detectado: {volume.get('volume')}",
    )
    panel["fieldConfig"]["defaults"]["displayName"] = str(volume.get("volume") or "Volume")
    panel["options"]["textMode"] = "auto"
    return panel


def network_interfaces_content(host_key):
    rows = [
        "| Host | Interface | Direcao | Ultimo valor | Ultima coleta | Fonte |",
        "|---|---|---|---:|---:|---|",
    ]
    items = [
        item for item in selected_items(host_key, "net_interfaces")
        if "bits received" in item.get("name", "").lower()
        or "bits sent" in item.get("name", "").lower()
        or (item.get("key_", "").startswith(("net.if.in", "net.if.out")) and "," not in item.get("key_", ""))
    ]
    seen = set()
    for item in items[:18]:
        ident = (item.get("name"), item.get("key_"))
        if ident in seen:
            continue
        seen.add(ident)
        rows.append(
            "| "
            + " | ".join([
                host_key,
                interface_label(item),
                traffic_direction(item),
                fmt_value(item, "bps" if item.get("units") == "bps" else None),
                fmt_clock(item.get("lastclock")),
                item.get("validation_source") or "zabbix_api",
            ])
            + " |"
        )
    if len(rows) == 2:
        rows.append(f"| {host_key} | sem interface validada | - | - | - | consulte `logs/dashboard-data-validation.json` |")
    return "\n".join(rows)


def network_interfaces_panel(pid, title, x, y, w, h, host_key):
    return text_panel(pid, title, x, y, w, h, network_interfaces_content(host_key))


def network_errors_drops_content(host_key):
    rows = [
        "| Host | Item | Tipo | Ultimo valor | Ultima coleta |",
        "|---|---|---|---:|---:|",
    ]
    items = selected_items(host_key, "net_errors") + selected_items(host_key, "net_drops")
    seen = set()
    unique_items = []
    for item in items:
        ident = (item.get("name"), item.get("key_"))
        if ident in seen:
            continue
        seen.add(ident)
        unique_items.append(item)

    def sort_key(item):
        haystack = f"{item.get('name', '')} {item.get('key_', '')}".lower()
        try:
            value = float(item.get("lastvalue") or 0)
        except (TypeError, ValueError):
            value = 0
        kind_rank = 0 if "error" in haystack or "erro" in haystack else 1
        normal_rank = 0 if value > 0 else 1
        return (normal_rank, kind_rank, -value)

    for item in sorted(unique_items, key=sort_key)[:10]:
        lname = (item.get("name", "") + " " + item.get("key_", "")).lower()
        kind = "erro" if "error" in lname else "drop/discard"
        try:
            numeric_value = float(item.get("lastvalue") or 0)
        except (TypeError, ValueError):
            numeric_value = 0
        display_value = fmt_value(item)
        if numeric_value > 0:
            display_value = f"**{display_value}**"
        rows.append(
            "| "
            + " | ".join([
                host_key,
                short_text(item.get("name", ""), 62),
                kind,
                display_value,
                fmt_clock(item.get("lastclock")),
            ])
            + " |"
        )
    if len(rows) == 2:
        rows.append(f"| {host_key} | Sem erros/drops detectados | - | 0 | - |")
    return "\n".join(rows)


def network_errors_drops_panel(pid, title, x, y, w, h, host_key):
    return text_panel(pid, title, x, y, w, h, network_errors_drops_content(host_key))


def memory_used_total_content(host_key):
    used = selected_item(host_key, "memory_used")
    total = selected_item(host_key, "memory_total")
    available = selected_item(host_key, "memory_available")
    pct = None
    if used and total:
        try:
            pct = (float(used.get("lastvalue") or 0) / float(total.get("lastvalue") or 1)) * 100
        except (TypeError, ValueError, ZeroDivisionError):
            pct = None
    rows = [
        "| Host | Usada | Total | Disponivel | Uso % |",
        "|---|---:|---:|---:|---:|",
        "| "
        + " | ".join([
            host_key,
            fmt_value(used, "bytes") if used else "-",
            fmt_value(total, "bytes") if total else "-",
            fmt_value(available, "bytes") if available else "-",
            f"{pct:.2f}%" if pct is not None else "-",
        ])
        + " |",
    ]
    return "\n".join(rows)


def memory_used_total_panel(pid, title, x, y, w, h, host_key):
    return text_panel(pid, title, x, y, w, h, memory_used_total_content(host_key))


def active_problems_count(host_key):
    return VALIDATED.get("hosts", {}).get(host_key, {}).get("problems_active", 0) or 0


def operational_summary_content(host_key):
    status = selected_item(host_key, "availability") or {}
    uptime = selected_item(host_key, "uptime")
    cpu = selected_item(host_key, "cpu_any")
    used = selected_item(host_key, "memory_used")
    total = selected_item(host_key, "memory_total")
    critical = critical_disk(host_key)
    mem_pct = "-"
    if used and total:
        try:
            mem_pct = f"{(float(used.get('lastvalue') or 0) / float(total.get('lastvalue') or 1)) * 100:.2f}%"
        except (TypeError, ValueError, ZeroDivisionError):
            mem_pct = "-"
    disk_text = "-"
    if critical:
        percent = disk_volume_percent(critical)
        disk_text = f"{critical.get('volume')} ({percent:.2f}%)" if percent is not None else str(critical.get("volume"))
    rows = [
        "| Host | Status | CPU | RAM | Disco mais cheio | Uptime | Problemas ativos | Ultima coleta |",
        "|---|---|---:|---:|---|---:|---:|---:|",
        "| "
        + " | ".join([
            host_key,
            "Online" if str(status.get("lastvalue")) == "1" else "Offline",
            fmt_value(cpu, "percent") if cpu else "-",
            mem_pct,
            disk_text,
            fmt_value(uptime, "s") if uptime else "-",
            str(active_problems_count(host_key)),
            fmt_clock(status.get("lastclock") or (uptime or {}).get("lastclock")),
        ])
        + " |",
    ]
    return "\n".join(rows)


def operational_summary_panel(pid, title, x, y, w, h, host_key):
    return text_panel(pid, title, x, y, w, h, operational_summary_content(host_key))


def events_recent_panel(pid, title, x, y, w, h, uid, discovery, host_key, host):
    if active_problems_count(host_key) == 0:
        return text_panel(pid, title, x, y, w, h, "## Sem eventos recentes\n\nNenhum evento ativo ou recente foi validado para este host.")
    return table_panel(
        pid,
        title,
        x,
        y,
        w,
        h,
        [problem_target(uid, query_type="events", limit=20, host=host, discovery=discovery)],
        "short",
    )


def validation_value_panel(pid, title, x, y, w, h, host_key, category, unit=None, name_pattern=None):
    items = selected_items(host_key, category, name_pattern)
    if not items:
        return missing_panel(pid, title, x, y, w, h, host_key, category)
    lines = [f"## {fmt_value(items[0], unit)}", "", f"Host: `{host_key}`"]
    for item in items[:4]:
        lines.append(f"Item: `{item.get('name')}`")
        lines.append(f"Fonte: `{item.get('validation_source', 'zabbix_api')}`")
    lines.append("")
    lines.append("Valor exibido a partir de `logs/dashboard-data-validation.json`; o Zabbix Server ainda nao possui historico para este item.")
    return text_panel(pid, title, x, y, w, h, "\n".join(lines))


def computed_value_panel(pid, title, x, y, w, h, host_key, unit, value, source_items):
    try:
        numeric = float(value)
        display = fmt_value({"lastvalue": numeric, "units": "B" if unit == "bytes" else "%"}, unit)
    except (TypeError, ValueError):
        display = str(value)
    lines = [f"## {display}", "", f"Host: `{host_key}`"]
    for item in source_items:
        if item:
            lines.append(f"Item base: `{item.get('name')}`")
    lines.append("")
    lines.append("Valor calculado com itens validados; sem consulta a serie historica quando o Zabbix ainda nao gravou `lastclock`.")
    return text_panel(pid, title, x, y, w, h, "\n".join(lines))


def zabbix_hostname(discovery, host_key):
    return discovery.get("hosts", {}).get(host_key, {}).get("query_host") or HOSTNAME_FALLBACK[host_key]


def host_regex(discovery):
    names = [re.escape(zabbix_hostname(discovery, host)) for host in HOSTS]
    return f"/^({'|'.join(names)})$/"


def zabbix_group(discovery, host_key=None):
    groups = []
    selected_hosts = [host_key] if host_key else HOSTS
    for host in selected_hosts:
        for group in discovery.get("hosts", {}).get(host, {}).get("groups", []):
            name = group.get("name")
            if name and name not in groups:
                groups.append(name)
    if not groups:
        return ""
    if len(groups) == 1:
        return groups[0]
    return f"/^({'|'.join(re.escape(g) for g in groups)})$/"


def discovered_filter(discovery, category, host_key=None, name_pattern=None):
    if host_key:
        validated = selected_item(host_key, category)
        if isinstance(validated, list):
            names = [i.get("name") for i in validated if i and i.get("name")]
            if name_pattern:
                compiled = re.compile(name_pattern, re.I)
                names = [n for n in names if compiled.search(n)]
            if names:
                return f"/^({'|'.join(re.escape(n) for n in names)})$/"
        elif validated and validated.get("name"):
            return validated["name"]

    if not host_key:
        names = []
        compiled = re.compile(name_pattern, re.I) if name_pattern else None
        for host in HOSTS:
            validated = selected_item(host, category)
            validated_items = validated if isinstance(validated, list) else [validated]
            for item in validated_items:
                name = item.get("name") if item else None
                if name and compiled and not compiled.search(name):
                    continue
                if name and name not in names:
                    names.append(name)
        if names:
            escaped = [re.escape(n) for n in names[:60]]
            return f"/^({'|'.join(escaped)})$/"

    names = []
    selected_hosts = [host_key] if host_key else HOSTS
    compiled = re.compile(name_pattern, re.I) if name_pattern else None
    for host in selected_hosts:
        for item in discovery.get("hosts", {}).get(host, {}).get("categories", {}).get(category, []):
            name = item.get("name")
            if name and compiled and not compiled.search(name):
                continue
            if name and name not in names:
                names.append(name)
    if not names:
        return "/^__NO_VALIDATED_ITEM__$/" 
    escaped = [re.escape(n) for n in names[:60]]
    return f"/^({'|'.join(escaped)})$/"


def ds(uid):
    return {"type": "alexanderzobnin-zabbix-datasource", "uid": uid}


def item_target(uid, category, host="$host", ref="A", result="time_series", discovery=None, host_key=None, name_pattern=None):
    discovery = discovery or {}
    return {
        "refId": ref,
        "datasource": ds(uid),
        "mode": 0,
        "group": {"filter": zabbix_group(discovery, host_key)},
        "host": {"filter": host},
        "application": {"filter": ""},
        "item": {"filter": discovered_filter(discovery, category, host_key=host_key, name_pattern=name_pattern)},
        "functions": [],
        "options": {"showDisabledItems": False, "skipEmptyValues": True},
        "resultFormat": result,
    }


def expression_target(ref, expression):
    return {
        "refId": ref,
        "datasource": {"type": "__expr__", "uid": "__expr__"},
        "type": "math",
        "expression": expression,
        "hide": False,
    }


def memory_percent_targets(uid, discovery, host_key, result="time_series"):
    used = host_item_target(uid, discovery, host_key, "memory_used", "A", result)
    total = host_item_target(uid, discovery, host_key, "memory_total", "B", result)
    used["hide"] = True
    total["hide"] = True
    return [used, total, expression_target("C", "$A / $B * 100")]


def memory_available_targets(uid, discovery, host_key, result="time_series"):
    item = selected_item(host_key, "memory_available") or {}
    if item.get("synthetic_expression") == "memory_total_minus_used":
        total = host_item_target(uid, discovery, host_key, "memory_total", "A", result)
        used = host_item_target(uid, discovery, host_key, "memory_used", "B", result)
        total["hide"] = True
        used["hide"] = True
        return [total, used, expression_target("C", "$A - $B")]
    return [host_item_target(uid, discovery, host_key, "memory_available", "A", result)]


def memory_available_stat_panel(pid, title, x, y, w, uid, discovery, host_key):
    if not item_has_data(host_key, "memory_available"):
        return missing_panel(pid, title, x, y, w, 5, host_key, "memory_available")
    target = host_item_target(uid, discovery, host_key, "memory_available")
    panel = stat_panel(pid, title, x, y, w, target, "bytes", thresholds(mem=True))
    item = selected_item(host_key, "memory_available") or {}
    if item.get("synthetic_expression") == "memory_total_minus_used":
        if category_can_query(host_key, "memory_total") and category_can_query(host_key, "memory_used"):
            panel["targets"] = memory_available_targets(uid, discovery, host_key)
            panel["datasource"] = {"type": "mixed", "uid": "-- Mixed --"}
        else:
            total = selected_item(host_key, "memory_total")
            used = selected_item(host_key, "memory_used")
            value = float(total.get("lastvalue") or 0) - float(used.get("lastvalue") or 0) if total and used else item.get("lastvalue")
            return stat_value_from_validation(pid, title, x, y, w, uid, discovery, host_key, "memory_total", "bytes", value=value)
    elif not item_can_query(item):
        return stat_value_from_validation(pid, title, x, y, w, uid, discovery, host_key, "memory_available", "bytes")
    return panel


def consolidated_memory_percent_targets(uid, discovery, result="time_series"):
    host = host_regex(discovery)
    used = item_target(uid, "memory_used", host, "A", result, discovery)
    total = item_target(uid, "memory_total", host, "B", result, discovery)
    used["hide"] = True
    total["hide"] = True
    return [used, total, expression_target("C", "$A / $B * 100")]


def cpu_fallback_targets(uid, discovery, host_key, result="time_series"):
    user = host_item_target(uid, discovery, host_key, "cpu_user", "A", result)
    privileged = host_item_target(uid, discovery, host_key, "cpu_privileged", "B", result)
    user["hide"] = True
    privileged["hide"] = True
    return [user, privileged, expression_target("C", "$A + $B")]


def cpu_current_targets(uid, discovery, host_key, result="time_series"):
    if category_can_query(host_key, "cpu_current"):
        return [host_item_target(uid, discovery, host_key, "cpu_current", "A", result)]
    return cpu_fallback_targets(uid, discovery, host_key, result)


def consolidated_cpu_current_targets(uid, discovery, result="time_series"):
    host = host_regex(discovery)
    user = item_target(uid, "cpu_user", host, "A", result, discovery)
    privileged = item_target(uid, "cpu_privileged", host, "B", result, discovery)
    user["hide"] = True
    privileged["hide"] = True
    return [user, privileged, expression_target("C", "$A + $B")]


def problem_target(uid, ref="A", query_type="problems", min_severity="$severidade", limit=None, host="$host", discovery=None):
    options = {
        "acknowledged": 2,
        "minSeverity": min_severity,
        "sortProblems": "lastchange",
        "showProblems": "problems",
    }
    if query_type == "events":
        options = {"acknowledged": 2, "minSeverity": min_severity, "showEvents": "events"}
    if limit:
        options["limit"] = limit
    return {
        "refId": ref,
        "datasource": ds(uid),
        "queryType": query_type,
        "group": {"filter": zabbix_group(discovery or {})},
        "host": {"filter": host},
        "trigger": {"filter": ""},
        "options": options,
        "resultFormat": "table",
    }


def thresholds(cpu=False, mem=False, disk=False):
    if cpu:
        return {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "yellow", "value": 70}, {"color": "red", "value": 85}]}
    if mem:
        return {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "yellow", "value": 75}, {"color": "red", "value": 90}]}
    if disk:
        return {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "yellow", "value": 80}, {"color": "red", "value": 90}]}
    return {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "yellow", "value": 1}, {"color": "red", "value": 3}]}


def status_thresholds():
    return {"mode": "absolute", "steps": [{"color": "red", "value": None}, {"color": "green", "value": 1}]}


def ok_thresholds():
    return {"mode": "absolute", "steps": [{"color": "green", "value": None}]}


def stat_panel(pid, title, x, y, w, target, unit="short", th=None, color_mode="background", description="", no_value="-"):
    return {
        "id": pid,
        "type": "stat",
        "title": title,
        "description": description,
        "datasource": target["datasource"],
        "gridPos": {"x": x, "y": y, "w": w, "h": 5},
        "targets": [target],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "decimals": 1,
                "noValue": no_value,
                "color": {"mode": "thresholds"},
                "thresholds": th or thresholds(),
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {"values": False, "calcs": ["lastNotNull"], "fields": ""},
            "orientation": "auto",
            "textMode": "auto",
            "wideLayout": True,
            "colorMode": color_mode,
            "graphMode": "area",
            "justifyMode": "center",
        },
    }


def constant_stat_panel(pid, title, x, y, w, value, text=None, unit="short", th=None, color_mode="background"):
    target = expression_target("A", str(value))
    panel = stat_panel(pid, title, x, y, w, target, unit, th or ok_thresholds(), color_mode=color_mode, no_value=text or str(value))
    panel["datasource"] = target["datasource"]
    panel["targets"] = [target]
    if text is not None:
        panel["fieldConfig"]["defaults"]["mappings"] = [
            {"type": "value", "options": {str(value): {"text": text, "color": "green"}}}
        ]
    panel["options"]["graphMode"] = "none"
    panel["options"]["textMode"] = "value"
    return panel


def status_panel(pid, title, x, y, w, target):
    panel = stat_panel(pid, title, x, y, w, target, "none", status_thresholds(), no_value="Offline")
    panel["fieldConfig"]["defaults"]["mappings"] = [
        {"type": "value", "options": {"1": {"text": "Online", "color": "green"}}},
        {"type": "value", "options": {"0": {"text": "Offline", "color": "red"}}},
    ]
    panel["options"]["textMode"] = "value"
    return panel


def timeseries_panel(pid, title, x, y, w, h, targets, unit, th=None):
    return {
        "id": pid,
        "type": "timeseries",
        "title": title,
        "datasource": targets[0]["datasource"],
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "decimals": 2,
                "min": 0 if unit == "percent" else None,
                "max": 100 if unit == "percent" else None,
                "color": {"mode": "palette-classic"},
                "thresholds": th or thresholds(),
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "smooth",
                    "lineWidth": 2,
                    "fillOpacity": 18,
                    "gradientMode": "opacity",
                    "showPoints": "never",
                    "spanNulls": False,
                    "insertNulls": False,
                    "axisPlacement": "auto",
                    "axisColorMode": "text",
                    "axisBorderShow": False,
                    "axisCenteredZero": False,
                    "scaleDistribution": {"type": "linear"},
                    "stacking": {"mode": "none", "group": "A"},
                    "thresholdsStyle": {"mode": "line" if unit == "percent" else "off"},
                    "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                },
            },
            "overrides": [],
        },
        "options": {
            "legend": {"showLegend": True, "displayMode": "table", "placement": "bottom", "calcs": ["lastNotNull", "max", "mean"]},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
    }


def table_panel(pid, title, x, y, w, h, targets, unit="short", th=None, transformations=None, description=""):
    return {
        "id": pid,
        "type": "table",
        "title": title,
        "description": description,
        "datasource": targets[0]["datasource"],
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "transformations": transformations or [],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "decimals": 1,
                "noValue": "-",
                "color": {"mode": "thresholds"},
                "thresholds": th or thresholds(),
                "custom": {"align": "auto", "cellOptions": {"type": "color-background"}, "inspect": False},
            },
            "overrides": [],
        },
        "options": {"showHeader": True, "cellHeight": "sm", "footer": {"show": False}},
    }


def row(pid, title, y):
    return {"id": pid, "type": "row", "title": title, "collapsed": False, "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}


def text_panel(pid, title, x, y, w, h, content):
    return {
        "id": pid,
        "type": "text",
        "title": title,
        "datasource": {"type": "grafana", "uid": "-- Grafana --"},
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "options": {"mode": "markdown", "content": content},
        "fieldConfig": {"defaults": {}, "overrides": []},
    }


def stat_value_from_validation(pid, title, x, y, w, uid, discovery, host_key, category, unit="short", source_category=None, value=None):
    source_category = source_category or category
    item = selected_item(host_key, source_category)
    if isinstance(item, list):
        item = item[0] if item else None
    if not item:
        return missing_panel(pid, title, x, y, w, 5, host_key, category)
    display_item = {"lastvalue": value, "units": "B" if unit == "bytes" else "%"} if value is not None else item
    target_category = source_category if not item.get("synthetic") else "memory_total"
    target = host_item_target(uid, discovery, host_key, target_category)
    return stat_panel(
        pid,
        title,
        x,
        y,
        w,
        target,
        unit,
        thresholds(cpu=unit == "percent" and "CPU" in title, mem="Memoria" in title, disk="Disco" in title),
        no_value=fmt_value(display_item, unit),
        description="Valor validado por zabbix_get enquanto o Zabbix Server ainda nao disponibiliza serie historica.",
    )


def missing_reason(host_key, category):
    host = VALIDATED.get("hosts", {}).get(host_key, {})
    missing = host.get("missing", {})
    aliases = {
        "availability": "status",
        "disk_percent": "disk_percent",
        "net_errors": "net_errors",
        "net_drops": "net_drops",
    }
    key = aliases.get(category, category)
    if key in ("net_in", "net_out", "net_interfaces"):
        return (
            "Nenhum item historico de rede foi confirmado para este painel. "
            "Crie/ative itens net.if.in/net.if.out, Bits received/Bits sent ou counters PowerShell de Network Interface."
        )
    if key in ("cpu_current", "cpu_hyperv_logical_total", "cpu_hyperv_root_total", "cpu_hyperv_virtual_total"):
        return (
            "Nenhum counter Hyper-V/Processor Time validado. Recomenda-se coletar Hyper-V Hypervisor Logical Processor(_Total) "
            "% Total Run Time ou Processor Information(_Total)% Processor Time."
        )
    return missing.get(key) or "Nenhum item validado por API Zabbix ou zabbix_get para este painel."


def missing_panel(pid, title, x, y, w, h, host_key, category):
    host = HOSTNAME_FALLBACK.get(host_key, host_key)
    content = (
        "**Item nao validado**\n\n"
        f"- Host: `{host}`\n"
        f"- Painel: `{title}`\n"
        f"- Motivo: {missing_reason(host_key, category)}\n"
        "- Log: `logs/dashboard-data-validation.json`\n\n"
        "O painel tecnico nao consulta o Grafana enquanto nao existir item validado por API Zabbix ou `zabbix_get`."
    )
    return text_panel(pid, title, x, y, w, h, content)


def filter_transform(min_value):
    return [
        {"id": "reduce", "options": {"reducers": ["lastNotNull"]}},
        {
            "id": "filterByValue",
            "options": {
                "type": "include",
                "match": "any",
                "filters": [{"fieldName": "Last *", "config": {"id": "greaterOrEqual", "options": {"value": min_value}}}],
            },
        },
    ]


def host_item_target(uid, discovery, host_key, category, ref="A", result="time_series", name_pattern=None):
    return item_target(
        uid,
        category,
        zabbix_hostname(discovery, host_key),
        ref,
        result,
        discovery,
        host_key=host_key,
        name_pattern=name_pattern,
    )


def add_metric_stat(panels, pid, uid, discovery, host_key, category, title, x, y, w, unit="short", th=None):
    if category_can_query(host_key, category):
        panels.append(stat_panel(pid, title, x, y, w, host_item_target(uid, discovery, host_key, category), unit, th or thresholds()))
    elif item_has_data(host_key, category):
        panels.append(stat_value_from_validation(pid, title, x, y, w, uid, discovery, host_key, category, unit))
    else:
        panels.append(missing_panel(pid, title, x, y, w, 5, host_key, category))
    return pid + 1


def add_metric_timeseries(panels, pid, uid, discovery, host_key, category, title, x, y, w, h, unit="short", th=None, name_pattern=None):
    target_filter = discovered_filter(discovery, category, host_key=host_key, name_pattern=name_pattern)
    if category_can_query(host_key, category, name_pattern) and target_filter != "/^__NO_VALIDATED_ITEM__$/":
        panels.append(timeseries_panel(pid, title, x, y, w, h, [host_item_target(uid, discovery, host_key, category, "A", "time_series", name_pattern)], unit, th or thresholds()))
    elif item_has_data(host_key, category):
        panels.append(timeseries_panel(pid, title, x, y, w, h, [host_item_target(uid, discovery, host_key, category, "A", "time_series", name_pattern)], unit, th or thresholds()))
    else:
        panels.append(missing_panel(pid, title, x, y, w, h, host_key, category))
    return pid + 1


def add_host_section(panels, pid, uid, discovery, host_key, title, y, include_named_disks=False):
    host = zabbix_hostname(discovery, host_key)
    panels.append(row(pid, title, y)); pid += 1
    y += 1

    if category_can_query(host_key, "availability"):
        panels.append(status_panel(pid, f"{host} - Status", 0, y, 4, host_item_target(uid, discovery, host_key, "availability")))
    elif item_has_data(host_key, "availability"):
        panels.append(status_panel(pid, f"{host} - Status", 0, y, 4, host_item_target(uid, discovery, host_key, "availability")))
    else:
        panels.append(text_panel(pid, f"{host} - Status", 0, y, 4, 5, "## Offline"))
    pid += 1

    if category_can_query(host_key, "uptime"):
        panels.append(stat_panel(pid, f"{host} - Uptime", 4, y, 4, host_item_target(uid, discovery, host_key, "uptime"), "s", ok_thresholds()))
    elif item_has_data(host_key, "uptime"):
        panels.append(stat_value_from_validation(pid, f"{host} - Uptime", 4, y, 4, uid, discovery, host_key, "uptime", "s"))
        panels[-1]["fieldConfig"]["defaults"]["thresholds"] = ok_thresholds()
    else:
        panels.append(text_panel(pid, f"{host} - Uptime", 4, y, 4, 5, "Sem coleta de uptime."))
    pid += 1

    if category_can_query(host_key, "cpu_user") and category_can_query(host_key, "cpu_privileged"):
        panels.append(stat_panel(pid, f"{host} - CPU", 8, y, 4, host_item_target(uid, discovery, host_key, "cpu_user"), "percent", thresholds(cpu=True), description="CPU baseada em user time + privileged time."))
        panels[-1]["targets"] = cpu_fallback_targets(uid, discovery, host_key)
        panels[-1]["datasource"] = {"type": "mixed", "uid": "-- Mixed --"}
    elif item_has_data(host_key, "cpu_any"):
        panels.append(stat_value_from_validation(pid, f"{host} - CPU", 8, y, 4, uid, discovery, host_key, "cpu_any", "percent"))
    else:
        panels.append(text_panel(pid, f"{host} - CPU", 8, y, 4, 5, "Sem item de CPU validado."))
    pid += 1

    if category_can_query(host_key, "memory_used") and category_can_query(host_key, "memory_total"):
        panels.append(stat_panel(pid, f"{host} - Memória usada %", 12, y, 4, host_item_target(uid, discovery, host_key, "memory_used"), "percent", thresholds(mem=True)))
        panels[-1]["targets"] = memory_percent_targets(uid, discovery, host_key)
        panels[-1]["datasource"] = {"type": "mixed", "uid": "-- Mixed --"}
    elif item_has_data(host_key, "memory_used") and item_has_data(host_key, "memory_total"):
        used = selected_item(host_key, "memory_used")
        total = selected_item(host_key, "memory_total")
        value = (float(used.get("lastvalue") or 0) / float(total.get("lastvalue") or 1)) * 100
        panels.append(stat_value_from_validation(pid, f"{host} - Memória usada %", 12, y, 4, uid, discovery, host_key, "memory_used", "percent", value=value))
    else:
        panels.append(text_panel(pid, f"{host} - Memória usada %", 12, y, 4, 5, "Sem item de memoria validado."))
    pid += 1

    y += 5

    pid = add_metric_stat(panels, pid, uid, discovery, host_key, "memory_used", f"{host} - Memória usada", 0, y, 6, "bytes", thresholds(mem=True))
    pid = add_metric_stat(panels, pid, uid, discovery, host_key, "memory_total", f"{host} - Memória total", 6, y, 6, "bytes", thresholds(mem=True))
    panels.append(memory_available_stat_panel(pid, f"{host} - Memória disponível", 12, y, 6, uid, discovery, host_key)); pid += 1
    panels.append(memory_used_total_panel(pid, f"{host} - Memória usada/total", 18, y, 6, 5, host_key)); pid += 1
    y += 5

    panels.append(critical_disk_panel(pid, f"{host} - Disco mais crítico", 0, y, 24, uid, discovery, host_key)); pid += 1
    y += 5

    panels.append(disk_inventory_panel(pid, f"{host} - Todos os discos", 0, y, 24, 7, host_key)); pid += 1
    y += 7

    pid = add_metric_timeseries(panels, pid, uid, discovery, host_key, "net_in", f"{host} - Rede entrada", 0, y, 12, 7, "bps", thresholds())
    pid = add_metric_timeseries(panels, pid, uid, discovery, host_key, "net_out", f"{host} - Rede saída", 12, y, 12, 7, "bps", thresholds())
    y += 7

    panels.append(stat_panel(pid, f"{host} - Problemas ativos", 0, y, 24, problem_target(uid, host=host, discovery=discovery), "short", thresholds(), no_value="0")); pid += 1
    y += 5

    panels.append(events_recent_panel(pid, f"{host} - Eventos recentes", 0, y, 12, 6, uid, discovery, host_key, host)); pid += 1
    panels.append(operational_summary_panel(pid, f"{host} - Resumo operacional", 12, y, 12, 6, host_key)); pid += 1
    y += 6

    return pid, y


def build_dashboard(discovery, uid):
    panels = []
    pid = 1
    panels.append(text_panel(pid, "Cabecalho executivo", 0, 0, 18, 3, "## Hyper-V Hosts - Monitoramento Executivo\nMonitoramento executivo dos hosts fisicos Hyper-V **HYPERV_HOST_A** e **HYPERV-HYPERV_HOST_B**.\n\nOs detalhes tecnicos estao separados por host e usam o Host name real cadastrado no Zabbix.")); pid += 1
    panels.append(text_panel(pid, "Periodo", 18, 0, 6, 3, "**Periodo**\n\nUse o seletor superior do Grafana.  \nAuto-refresh: `$intervalo`")); pid += 1

    pid, next_y = add_host_section(panels, pid, uid, discovery, "HYPERV_HOST_A", "HYPERV_HOST_A", 3, include_named_disks=True)
    pid, next_y = add_host_section(panels, pid, uid, discovery, "HYPERV-HYPERV_HOST_B", "HYPERV-HYPERV_HOST_B", next_y, include_named_disks=False)

    return {
        "id": None,
        "uid": "hyperv-hosts-monitoramento-executivo",
        "title": "Hyper-V Hosts - Monitoramento Executivo",
        "tags": ["hyper-v", "zabbix", "windows", "noc", "executivo"],
        "timezone": "browser",
        "schemaVersion": 38,
        "version": 1,
        "style": "dark",
        "editable": True,
        "graphTooltip": 1,
        "refresh": "$intervalo",
        "time": {"from": "now-6h", "to": "now"},
        "timepicker": {"refresh_intervals": ["30s", "1m", "5m", "15m", "1h"], "time_options": ["1h", "6h", "12h", "24h", "7d", "30d"]},
        "templating": {
            "list": [
                {
                    "name": "intervalo",
                    "label": "Intervalo",
                    "type": "custom",
                    "query": "30s,1m,5m,15m,1h",
                    "includeAll": False,
                    "multi": False,
                    "current": {"selected": True, "text": "1m", "value": "1m"},
                    "options": [],
                },
                {
                    "name": "severidade",
                    "label": "Severidade",
                    "type": "custom",
                    "query": "1 : Information+,2 : Warning+,3 : Average+,4 : High+,5 : Disaster",
                    "includeAll": False,
                    "multi": False,
                    "current": {"selected": True, "text": "Warning+", "value": "2"},
                    "options": [],
                },
            ]
        },
        "annotations": {"list": [{"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": True, "hide": True, "iconColor": "rgba(0, 211, 255, 1)", "name": "Annotations & Alerts", "type": "dashboard"}]},
        "panels": panels,
    }


def build_minimal_dashboard(discovery, uid):
    panels = []
    pid = 1
    panels.append(text_panel(pid, "Validacao de dados Hyper-V", 0, 0, 24, 3, "## Validacao de dados Hyper-V\nDashboard minimo gerado somente com itens confirmados em `logs/dashboard-data-validation.json`.")); pid += 1
    y = 3
    for host_key in HOSTS:
        host = zabbix_hostname(discovery, host_key)
        panels.append(row(pid, host, y)); pid += 1
        y += 1
        if category_can_query(host_key, "uptime"):
            panels.append(stat_panel(pid, f"{host} - Uptime", 0, y, 6, host_item_target(uid, discovery, host_key, "uptime"), "s", thresholds())); pid += 1
        elif item_has_data(host_key, "uptime"):
            panels.append(stat_value_from_validation(pid, f"{host} - Uptime", 0, y, 6, uid, discovery, host_key, "uptime", "s")); pid += 1
        else:
            panels.append(missing_panel(pid, f"{host} - Uptime", 0, y, 6, 5, host_key, "uptime")); pid += 1
        if category_can_query(host_key, "memory_used"):
            panels.append(stat_panel(pid, f"{host} - Memoria usada", 6, y, 6, host_item_target(uid, discovery, host_key, "memory_used"), "bytes", thresholds(mem=True))); pid += 1
        elif item_has_data(host_key, "memory_used"):
            panels.append(stat_value_from_validation(pid, f"{host} - Memoria usada", 6, y, 6, uid, discovery, host_key, "memory_used", "bytes")); pid += 1
        else:
            panels.append(missing_panel(pid, f"{host} - Memoria usada", 6, y, 6, 5, host_key, "memory_used")); pid += 1
        if category_can_query(host_key, "memory_total"):
            panels.append(stat_panel(pid, f"{host} - Memoria total", 12, y, 6, host_item_target(uid, discovery, host_key, "memory_total"), "bytes", thresholds(mem=True))); pid += 1
        elif item_has_data(host_key, "memory_total"):
            panels.append(stat_value_from_validation(pid, f"{host} - Memoria total", 12, y, 6, uid, discovery, host_key, "memory_total", "bytes")); pid += 1
        else:
            panels.append(missing_panel(pid, f"{host} - Memoria total", 12, y, 6, 5, host_key, "memory_total")); pid += 1
        panels.append(memory_available_stat_panel(pid, f"{host} - Memoria disponivel", 18, y, 6, uid, discovery, host_key)); pid += 1
        y += 5
    return {
        "id": None,
        "uid": "hyperv-hosts-monitoramento-executivo",
        "title": "Hyper-V Hosts - Monitoramento Executivo",
        "tags": ["hyper-v", "zabbix", "validacao"],
        "timezone": "browser",
        "schemaVersion": 38,
        "version": 1,
        "style": "dark",
        "editable": True,
        "graphTooltip": 1,
        "refresh": "$intervalo",
        "time": {"from": "now-6h", "to": "now"},
        "templating": {"list": [{"name": "intervalo", "label": "Intervalo", "type": "custom", "query": "30s,1m,5m,15m,1h", "includeAll": False, "multi": False, "current": {"selected": True, "text": "1m", "value": "1m"}, "options": []}]},
        "annotations": {"list": [{"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": True, "hide": True, "iconColor": "rgba(0, 211, 255, 1)", "name": "Annotations & Alerts", "type": "dashboard"}]},
        "panels": panels,
    }


def main():
    global VALIDATED, RENDERED
    load_dotenv(ROOT / ".env")
    discovery = load_discovery()
    VALIDATED = load_validation()
    RENDERED = load_render_validation()
    uid = os.getenv("ZABBIX_DATASOURCE_UID", "zabbix") or "zabbix"
    mode = os.getenv("DASHBOARD_MODE", "full")
    dashboard = build_minimal_dashboard(discovery, uid) if mode == "minimal" else build_dashboard(discovery, uid)
    DASHBOARD.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False))
    missing = {host: sorted(data.get("missing", {}).keys()) for host, data in VALIDATED.get("hosts", {}).items()} or discovery.get("missing", {})
    report = {"datasource_uid": uid, "dashboard": str(DASHBOARD), "missing": missing, "discovery_problems": discovery.get("problems", [])}
    (LOGS / "dashboard-generation-summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
