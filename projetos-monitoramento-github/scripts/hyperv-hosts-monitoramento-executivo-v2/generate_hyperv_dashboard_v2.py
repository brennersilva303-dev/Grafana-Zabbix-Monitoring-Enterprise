#!/usr/bin/env python3
import json
import html
from datetime import datetime
from pathlib import Path

import generate_hyperv_dashboard as base


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dashboard-hyperv-hosts-v2.json"
SUMMARY = ROOT / "logs" / "dashboard-v2-generation-summary.json"
ACTIVE_PROBLEMS = ROOT / "logs" / "hyperv-active-problems.json"
HOSTS = ["HYPERV_HOST_A", "HYPERV-HYPERV_HOST_B"]
UID = "E2lQF-HGk"
DISCOVERY_DATA = {}
ACTIVE_PROBLEMS_DATA = {}


def gauge_panel(pid, title, x, y, w, h, targets, unit, thresholds, description=""):
    return {
        "id": pid,
        "type": "gauge",
        "title": title,
        "description": description,
        "datasource": targets[0]["datasource"],
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "decimals": 1,
                "min": 0,
                "max": 100 if unit == "percent" else None,
                "thresholds": thresholds,
                "color": {"mode": "thresholds"},
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {"values": False, "calcs": ["lastNotNull"], "fields": ""},
            "orientation": "auto",
            "showThresholdLabels": False,
            "showThresholdMarkers": True,
        },
    }


def html_panel(pid, title, x, y, w, h, content):
    panel = base.text_panel(pid, title, x, y, w, h, content)
    panel["transparent"] = True
    panel["options"] = {"mode": "html", "content": content}
    return panel


def polish_native_panel(panel):
    panel["transparent"] = True
    panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
    panel["fieldConfig"]["defaults"].setdefault("custom", {})
    panel["fieldConfig"]["defaults"]["custom"].update({
        "axisBorderShow": False,
        "axisColorMode": "text",
    })
    return panel


def esc(value):
    return html.escape(str(value or ""))


def short(value, limit=72):
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def card_css():
    return """
  <style>
    .hv-wrap { width:100%; box-sizing:border-box; background:#f4f7fb; color:#172033; font-family:'Segoe UI',Arial,sans-serif; overflow:hidden; }
    .hv-card { height:100%; box-sizing:border-box; border-radius:14px; background:#fff; border:1px solid #d7e0ec; border-left:8px solid #2f80ed; box-shadow:0 6px 14px rgba(15,23,42,.08); padding:13px 15px; overflow:hidden; }
    .hv-card.green { border-left-color:#22c55e; }
    .hv-card.red { border-left-color:#ef4444; }
    .hv-card.yellow { border-left-color:#facc15; }
    .hv-card.slate { border-left-color:#64748b; }
    .hv-title { display:flex; justify-content:space-between; align-items:center; gap:10px; margin-bottom:10px; }
    .hv-title strong { font-size:18px; color:#0f172a; font-weight:900; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .hv-title span { font-size:11px; font-weight:900; color:#526176; text-transform:uppercase; }
    .hv-big { font-size:44px; line-height:1; font-weight:900; color:#0f172a; margin-top:12px; text-align:center; }
    .hv-sub { margin-top:8px; text-align:center; color:#526176; font-size:12px; font-weight:800; }
    .hv-table { width:100%; border-collapse:separate; border-spacing:0; table-layout:fixed; font-size:12px; }
    .hv-table th { text-align:left; color:#526176; background:#eef3f8; text-transform:uppercase; font-size:10px; font-weight:900; padding:8px 8px; border-bottom:1px solid #dbe4ef; }
    .hv-table td { padding:8px 8px; border-bottom:1px solid #e6edf5; color:#172033; font-weight:700; vertical-align:top; overflow-wrap:anywhere; }
    .hv-table tr:last-child td { border-bottom:0; }
    .hv-table .num { text-align:right; font-variant-numeric:tabular-nums; }
    .pill { border-radius:999px; padding:3px 8px; font-size:10px; font-weight:900; text-transform:uppercase; display:inline-block; }
    .pill.normal,.pill.ok { background:#dcfce7; color:#166534; }
    .pill.warn { background:#fef3c7; color:#92400e; }
    .pill.crit { background:#fee2e2; color:#991b1b; }
    .kv { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }
    .kv div { background:#eef3f8; border-radius:9px; padding:9px; min-width:0; }
    .kv span { display:block; color:#526176; font-size:10px; font-weight:900; text-transform:uppercase; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .kv strong { display:block; margin-top:6px; color:#0f172a; font-size:16px; font-weight:900; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  </style>
"""


def html_card(title, body, color="blue"):
    return f"<div class='hv-wrap'><section class='hv-card {color}'><div class='hv-title'><strong>{esc(title)}</strong><span>Hyper-V</span></div>{body}</section>{card_css()}</div>"


def section_header(host_key):
    return f"""
<div class="hyperv-noc">
  <section class="hostline single">
    {host_card(host_key)}
  </section>
  <style>
    .hyperv-noc {{ width:100%; box-sizing:border-box; padding:8px 10px 10px; background:#f4f7fb; color:#172033; font-family:'Segoe UI',Arial,sans-serif; overflow:hidden; }}
    .hostline.single {{ display:grid; grid-template-columns:1fr; gap:12px; }}
    .hyperv-card {{ min-height:138px; box-sizing:border-box; border-radius:14px; background:#fff; border:1px solid #d7e0ec; border-left:9px solid #94a3b8; padding:14px 16px; overflow:hidden; box-shadow:0 6px 14px rgba(15,23,42,.08); }}
    .hyperv-card.online {{ border-left-color:#22c55e; }}
    .hyperv-card.offline {{ border-left-color:#ef4444; background:#fff8f8; }}
    .line-top {{ display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:13px; }}
    .line-top strong {{ font-size:25px; line-height:1.05; color:#0f172a; font-weight:900; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .line-top span {{ flex:0 0 auto; border-radius:999px; padding:5px 12px; font-size:12px; font-weight:900; background:#dcfce7; color:#166534; }}
    .offline .line-top span {{ background:#fee2e2; color:#991b1b; }}
    .host-grid {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; }}
    .mini-box {{ min-width:0; background:#eef3f8; border-radius:9px; border-top:5px solid #64748b; padding:9px 10px; min-height:64px; overflow:hidden; }}
    .mini-box span {{ display:block; font-size:10px; font-weight:900; color:#526176; text-transform:uppercase; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .mini-box strong {{ display:block; margin-top:8px; font-size:22px; line-height:1.05; color:#111827; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .mini-box.green {{ border-top-color:#22c55e; }}
    .mini-box.red {{ border-top-color:#ef4444; }}
    .mini-box.yellow {{ border-top-color:#facc15; }}
    .mini-box.blue {{ border-top-color:#2f80ed; }}
    .mini-box.slate {{ border-top-color:#64748b; }}
  </style>
</div>
"""


def host_summary_values(host_key):
    status = base.selected_item(host_key, "availability") or {}
    status_online = str(status.get("lastvalue")) == "1"
    uptime = base.selected_item(host_key, "uptime")
    cpu = base.selected_item(host_key, "cpu_user")
    mem = base.selected_item(host_key, "memory_used")
    critical = base.critical_disk(host_key)
    disk = "-"
    if critical:
        pct = base.disk_volume_percent(critical)
        disk = f"{critical.get('volume')} {pct:.1f}%" if pct is not None else str(critical.get("volume"))
    return {
        "status": "ONLINE" if status_online else "OFFLINE",
        "state": "online" if status_online else "offline",
        "uptime": base.fmt_value(uptime, "s") if uptime else "-",
        "cpu": base.fmt_value(cpu, "percent") if cpu else "-",
        "memory": base.fmt_value(mem, "bytes") if mem else "-",
        "disk": disk,
        "problems": str(base.active_problems_count(host_key)),
    }


def metric_card(label, value, cls):
    return f"<div class='metric {cls}'><span>{esc(label)}</span><strong>{esc(value)}</strong></div>"


def mini(label, value, cls="slate"):
    return f"<div class='mini-box {cls}'><span>{esc(label)}</span><strong>{esc(value)}</strong></div>"


def host_card(host_key):
    values = host_summary_values(host_key)
    return f"""
    <article class="hyperv-card {values['state']}">
      <div class="line line-top">
        <strong>{esc(host_key)}</strong>
        <span>{esc(values['status'])}</span>
      </div>
      <div class="host-grid">
        {mini('Uptime', values['uptime'], 'green')}
        {mini('CPU', values['cpu'], 'blue')}
        {mini('Memória usada', values['memory'], 'slate')}
        {mini('Disco crítico', values['disk'], 'yellow')}
        {mini('Problemas', values['problems'], 'green' if values['problems'] == '0' else 'red')}
      </div>
    </article>
    """


def executive_html():
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    online = base.online_hosts_count()
    problems = base.total_active_problems()
    problem_class = "green" if problems == 0 else "red"
    return f"""
<div class="hyperv-noc">
  <section class="topline">
    {metric_card('Hosts online', f'{online} Online', 'green')}
    {metric_card('Problemas totais', problems, problem_class)}
    {metric_card('Última atualização', now, 'slate')}
  </section>
  <section class="hostline">
    {host_card('HYPERV_HOST_A')}
    {host_card('HYPERV-HYPERV_HOST_B')}
  </section>
  <style>
    .hyperv-noc {{ width:100%; box-sizing:border-box; padding:8px 10px 10px; background:#f4f7fb; color:#172033; font-family:'Segoe UI',Arial,sans-serif; overflow:hidden; }}
    .topline {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin:0 0 12px; }}
    .metric {{ min-height:104px; border:1px solid #dbe4ef; background:#fff; border-radius:14px; display:flex; flex-direction:column; align-items:center; justify-content:center; box-shadow:0 6px 14px rgba(15,23,42,.08); border-top:8px solid #64748b; }}
    .metric span {{ font-size:13px; text-transform:uppercase; letter-spacing:.02em; color:#526176; font-weight:900; text-align:center; }}
    .metric strong {{ margin-top:6px; font-size:42px; line-height:1; color:#0f172a; }}
    .metric.green {{ border-top-color:#22a85a; }}
    .metric.red {{ border-top-color:#ef4444; }}
    .metric.yellow {{ border-top-color:#f2c94c; }}
    .metric.blue {{ border-top-color:#2f80ed; }}
    .metric.slate {{ border-top-color:#475569; }}
    .metric.slate strong {{ font-size:32px; }}
    .hostline {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }}
    .hyperv-card {{ min-height:178px; box-sizing:border-box; border-radius:14px; background:#fff; border:1px solid #d7e0ec; border-left:9px solid #94a3b8; padding:14px 16px; overflow:hidden; box-shadow:0 6px 14px rgba(15,23,42,.08); }}
    .hyperv-card.online {{ border-left-color:#22c55e; }}
    .hyperv-card.offline {{ border-left-color:#ef4444; background:#fff8f8; }}
    .line-top {{ display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:13px; }}
    .line-top strong {{ font-size:25px; line-height:1.05; color:#0f172a; font-weight:900; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .line-top span {{ flex:0 0 auto; border-radius:999px; padding:5px 12px; font-size:12px; font-weight:900; background:#dcfce7; color:#166534; }}
    .offline .line-top span {{ background:#fee2e2; color:#991b1b; }}
    .host-grid {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; }}
    .mini-box {{ min-width:0; background:#eef3f8; border-radius:9px; border-top:5px solid #64748b; padding:9px 10px; min-height:74px; overflow:hidden; }}
    .mini-box span {{ display:block; font-size:10px; font-weight:900; color:#526176; text-transform:uppercase; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .mini-box strong {{ display:block; margin-top:8px; font-size:22px; line-height:1.05; color:#111827; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .mini-box.green {{ border-top-color:#22c55e; }}
    .mini-box.red {{ border-top-color:#ef4444; }}
    .mini-box.yellow {{ border-top-color:#facc15; }}
    .mini-box.blue {{ border-top-color:#2f80ed; }}
    .mini-box.slate {{ border-top-color:#64748b; }}
  </style>
</div>
"""


def memory_percent_stat(pid, host, x, y, w, uid, discovery, host_key):
    panel = base.stat_panel(
        pid,
        f"{host} - Memória usada %",
        x,
        y,
        w,
        base.host_item_target(uid, discovery, host_key, "memory_used"),
        "percent",
        base.thresholds(mem=True),
    )
    if base.item_has_data(host_key, "memory_used") and base.item_has_data(host_key, "memory_total"):
        panel["targets"] = base.memory_percent_targets(uid, discovery, host_key)
        panel["datasource"] = {"type": "mixed", "uid": "-- Mixed --"}
    return panel


def memory_percent_gauge(pid, host, x, y, w, h, uid, discovery, host_key):
    targets = base.memory_percent_targets(uid, discovery, host_key)
    panel = gauge_panel(pid, f"{host} - Memória", x, y, w, h, targets, "percent", base.thresholds(mem=True))
    panel["datasource"] = {"type": "mixed", "uid": "-- Mixed --"}
    return polish_native_panel(panel)


def cpu_stat(pid, host, x, y, w, uid, discovery, host_key):
    panel = base.stat_panel(
        pid,
        f"{host} - CPU",
        x,
        y,
        w,
        base.host_item_target(uid, discovery, host_key, "cpu_user"),
        "percent",
        base.thresholds(cpu=True),
    )
    if base.category_can_query(host_key, "cpu_user") and base.category_can_query(host_key, "cpu_privileged"):
        panel["targets"] = base.cpu_fallback_targets(uid, discovery, host_key)
        panel["datasource"] = {"type": "mixed", "uid": "-- Mixed --"}
    return panel


def cpu_timeseries(pid, host, x, y, w, h, uid, discovery, host_key):
    targets = base.cpu_fallback_targets(uid, discovery, host_key)
    panel = base.timeseries_panel(pid, f"{host} - CPU - gráfico", x, y, w, h, targets, "percent", base.thresholds(cpu=True))
    panel["datasource"] = {"type": "mixed", "uid": "-- Mixed --"}
    return polish_native_panel(panel)


def net_timeseries(panels, pid, uid, discovery, host_key, category, title, x, y):
    before = len(panels)
    pid = base.add_metric_timeseries(panels, pid, uid, discovery, host_key, category, title, x, y, 12, 7, "bps", base.thresholds())
    if len(panels) > before:
        panels[-1] = polish_native_panel(panels[-1])
    return pid


def host_summary_cards(panels, pid, y, uid, discovery, host_key, xbase):
    host = base.zabbix_hostname(discovery, host_key)
    panels.append(base.text_panel(pid, host, xbase, y, 12, 1, f"### {host}"))
    pid += 1
    y += 1
    panels.append(base.status_panel(pid, f"{host} - Status", xbase, y, 4, base.host_item_target(uid, discovery, host_key, "availability")))
    pid += 1
    panels.append(base.stat_panel(pid, f"{host} - Uptime", xbase + 4, y, 4, base.host_item_target(uid, discovery, host_key, "uptime"), "s", base.ok_thresholds()))
    pid += 1
    panels.append(cpu_stat(pid, host, xbase + 8, y, 4, uid, discovery, host_key))
    pid += 1
    y += 5
    panels.append(memory_percent_stat(pid, host, xbase, y, 4, uid, discovery, host_key))
    pid += 1
    panels.append(base.critical_disk_panel(pid, f"{host} - Disco crítico", xbase + 4, y, 4, uid, discovery, host_key))
    pid += 1
    panels.append(base.stat_panel(pid, f"{host} - Problemas", xbase + 8, y, 4, base.problem_target(uid, host=host, discovery=discovery), "short", base.thresholds(), no_value="0"))
    pid += 1
    return pid


def disk_table_html(host_key):
    rows = []
    for volume in base.disk_volumes(host_key):
        percent = base.disk_volume_percent(volume)
        if percent is None:
            status = "sem dado"
            cls = "warn"
            pused = "-"
        else:
            status = base.disk_status(percent)
            cls = "crit" if percent >= 90 else "warn" if percent >= 80 else "normal"
            pused = f"{percent:.1f}%"
        free_value = "-"
        if volume.get("free"):
            free_value = base.fmt_value(volume.get("free"), "bytes")
        elif volume.get("total") and volume.get("used"):
            try:
                free_value = base.fmt_value({"lastvalue": float(volume["total"]["lastvalue"]) - float(volume["used"]["lastvalue"]), "units": "B"}, "bytes")
            except (TypeError, ValueError):
                free_value = "-"
        rows.append(
            "<tr>"
            f"<td>{esc(host_key)}</td>"
            f"<td>{esc(volume.get('volume'))}</td>"
            f"<td class='num'>{esc(pused)}</td>"
            f"<td class='num'>{esc(base.fmt_value(volume.get('used'), 'bytes') if volume.get('used') else '-')}</td>"
            f"<td class='num'>{esc(base.fmt_value(volume.get('total'), 'bytes') if volume.get('total') else '-')}</td>"
            f"<td class='num'>{esc(free_value)}</td>"
            f"<td>{esc(base.fmt_clock(volume.get('pused', {}).get('lastclock') or volume.get('used', {}).get('lastclock')))}</td>"
            f"<td><span class='pill {cls}'>{esc(status)}</span></td>"
            "</tr>"
        )
    if not rows:
        rows.append(f"<tr><td colspan='8'>{esc(host_key)} sem volume validado</td></tr>")
    body = (
        "<table class='hv-table'><thead><tr>"
        "<th>Host</th><th>Volume</th><th>Uso</th><th>Usado</th><th>Total</th><th>Livre</th><th>Última coleta</th><th>Status</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    return html_card(f"{host_key} - Todos os discos", body, "blue")


def interfaces_table_html(host_key):
    rows = []
    items = [
        item for item in base.selected_items(host_key, "net_interfaces")
        if "bits received" in item.get("name", "").lower()
        or "bits sent" in item.get("name", "").lower()
        or (item.get("key_", "").startswith(("net.if.in", "net.if.out")) and "," not in item.get("key_", ""))
    ]
    seen = set()
    for item in items[:8]:
        ident = (item.get("name"), item.get("key_"))
        if ident in seen:
            continue
        seen.add(ident)
        rows.append(
            "<tr>"
            f"<td>{esc(base.interface_label(item))}</td>"
            f"<td>{esc(short(item.get('key_'), 68))}</td>"
            f"<td>{esc(base.traffic_direction(item))}</td>"
            f"<td class='num'>{esc(base.fmt_value(item, 'bps' if item.get('units') == 'bps' else None))}</td>"
            f"<td>{esc(base.fmt_clock(item.get('lastclock')))}</td>"
            f"<td>{esc(item.get('validation_source') or 'zabbix_api')}</td>"
            "</tr>"
        )
    if not rows:
        rows.append(f"<tr><td colspan='6'>{esc(host_key)} sem interface validada</td></tr>")
    body = (
        "<table class='hv-table'><thead><tr>"
        "<th>Nome</th><th>Key</th><th>Direção</th><th>Último valor</th><th>Última coleta</th><th>Fonte</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    return html_card(f"{host_key} - Interfaces detectadas", body, "slate")


def errors_table_html(host_key):
    items = base.selected_items(host_key, "net_errors") + base.selected_items(host_key, "net_drops")
    unique = []
    seen = set()
    for item in items:
        ident = (item.get("name"), item.get("key_"))
        if ident in seen:
            continue
        seen.add(ident)
        unique.append(item)

    def sort_key(item):
        haystack = f"{item.get('name', '')} {item.get('key_', '')}".lower()
        try:
            value = float(item.get("lastvalue") or 0)
        except (TypeError, ValueError):
            value = 0
        kind = 0 if "error" in haystack else 1
        normal = 0 if value > 0 else 1
        return (normal, kind, -value)

    rows = []
    for item in sorted(unique, key=sort_key)[:8]:
        haystack = f"{item.get('name', '')} {item.get('key_', '')}".lower()
        kind = "erro" if "error" in haystack else "drop/discard"
        try:
            numeric = float(item.get("lastvalue") or 0)
        except (TypeError, ValueError):
            numeric = 0
        cls = "crit" if numeric > 0 else "normal"
        rows.append(
            "<tr>"
            f"<td>{esc(short(item.get('name'), 64))}</td>"
            f"<td>{esc(kind)}</td>"
            f"<td class='num'><span class='pill {cls}'>{esc(base.fmt_value(item))}</span></td>"
            f"<td>{esc(base.fmt_clock(item.get('lastclock')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append(f"<tr><td colspan='4'>{esc(host_key)} sem erros/drops detectados</td></tr>")
    body = (
        "<table class='hv-table'><thead><tr>"
        "<th>Item</th><th>Tipo</th><th>Último valor</th><th>Última coleta</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    return html_card(f"{host_key} - Erros/Drops de rede", body, "green")


def problems_card_html(host_key):
    count = base.active_problems_count(host_key)
    cls = "green" if count == 0 else "red"
    text = "Sem problemas" if count == 0 else "Ver eventos recentes"
    body = f"<div class='hv-big'>{count}</div><div class='hv-sub'>{esc(text)}</div>"
    return html_card(f"{host_key} - Problemas ativos", body, cls)


def events_html(host_key, host):
    count = base.active_problems_count(host_key)
    if count == 0:
        body = "<div class='hv-big' style='font-size:30px'>Sem eventos recentes</div><div class='hv-sub'>Nenhum incidente ativo validado para este host.</div>"
        return html_card(f"{host} - Eventos recentes", body, "green")
    body = "<div class='hv-big' style='font-size:30px'>Eventos no Zabbix</div><div class='hv-sub'>Consulte o painel de problemas ativos para a lista filtrada por severidade.</div>"
    return html_card(f"{host} - Eventos recentes", body, "red")


def operational_summary_html(host_key):
    status = base.selected_item(host_key, "availability") or {}
    uptime = base.selected_item(host_key, "uptime")
    cpu = base.selected_item(host_key, "cpu_user")
    used = base.selected_item(host_key, "memory_used")
    total = base.selected_item(host_key, "memory_total")
    critical = base.critical_disk(host_key)
    mem_pct = "-"
    if used and total:
        try:
            mem_pct = f"{(float(used.get('lastvalue') or 0) / float(total.get('lastvalue') or 1)) * 100:.1f}%"
        except (TypeError, ValueError, ZeroDivisionError):
            mem_pct = "-"
    disk_text = "-"
    if critical:
        pct = base.disk_volume_percent(critical)
        disk_text = f"{critical.get('volume')} ({pct:.1f}%)" if pct is not None else str(critical.get("volume"))
    values = [
        ("Status", "Online" if str(status.get("lastvalue")) == "1" else "Offline"),
        ("CPU", base.fmt_value(cpu, "percent") if cpu else "-"),
        ("RAM", mem_pct),
        ("Disco mais cheio", disk_text),
        ("Uptime", base.fmt_value(uptime, "s") if uptime else "-"),
        ("Problemas", str(base.active_problems_count(host_key))),
        ("Última coleta", base.fmt_clock(status.get("lastclock") or (uptime or {}).get("lastclock"))),
    ]
    body = "<div class='kv'>" + "".join(f"<div><span>{esc(k)}</span><strong>{esc(v)}</strong></div>" for k, v in values) + "</div>"
    return html_card(f"{host_key} - Resumo operacional", body, "blue")


def number_value(item, default=0.0):
    try:
        return float((item or {}).get("lastvalue") or default)
    except (TypeError, ValueError):
        return default


def cpu_percent(host_key):
    user = number_value(base.selected_item(host_key, "cpu_user"))
    privileged = number_value(base.selected_item(host_key, "cpu_privileged"))
    return max(0.0, min(100.0, user + privileged))


def memory_percent(host_key):
    used = number_value(base.selected_item(host_key, "memory_used"))
    total = number_value(base.selected_item(host_key, "memory_total"), 1.0)
    return max(0.0, min(100.0, (used / total) * 100 if total else 0.0))


def selected_net_value(host_key, category):
    items = base.selected_items(host_key, category)
    return number_value(items[0]) if items else 0.0


def fmt_bps(value):
    return base.fmt_value({"lastvalue": value, "units": "bps"}, "bps")


def all_host_items(host_key):
    items = []
    selected = base.VALIDATED.get("hosts", {}).get(host_key, {}).get("selected", {}) or {}
    for value in selected.values():
        if isinstance(value, list):
            items.extend([item for item in value if isinstance(item, dict)])
        elif isinstance(value, dict):
            items.append(value)
    usable = base.VALIDATED.get("hosts", {}).get(host_key, {}).get("usable_items", []) or []
    if isinstance(usable, list):
        items.extend([item for item in usable if isinstance(item, dict)])
    items.extend(DISCOVERY_DATA.get("hosts", {}).get(host_key, {}).get("items_with_data", []) or [])
    items.extend(DISCOVERY_DATA.get("hosts", {}).get(host_key, {}).get("items", []) or [])
    seen = set()
    unique = []
    for item in items:
        ident = item.get("itemid") or (item.get("name"), item.get("key_"))
        if ident in seen:
            continue
        seen.add(ident)
        unique.append(item)
    return unique


def metric_by_patterns(host_key, patterns):
    lowered = [p.lower() for p in patterns]
    items = [item for item in all_host_items(host_key) if item.get("enabled", True)]
    for pattern in lowered:
        for item in items:
            text = f"{item.get('name', '')} {item.get('key_', '')}".lower()
            if pattern in text:
                return item
    return None


def formatted_metric_or_waiting(item, unit=None):
    if not item:
        return "Não coletado"
    value = item.get("lastvalue")
    if value in (None, "", "ZBX_NOTSUPPORTED", "ZBX_NODATA"):
        return "Não coletado"
    if unit == "Bps":
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)
        for suffix in ["B/s", "KB/s", "MB/s", "GB/s", "TB/s"]:
            if abs(numeric) < 1024 or suffix == "TB/s":
                return f"{numeric:.1f} {suffix}"
            numeric /= 1024
    if unit == "ms_from_seconds":
        try:
            return f"{float(value) * 1000:.2f} ms"
        except (TypeError, ValueError):
            return str(value)
    return base.fmt_value(item, unit)


def hyperv_cpu_value(host_key):
    item = metric_by_patterns(host_key, ["hyper-v cpu logical processor total run time"])
    if item:
        return item
    for category in ("cpu_hyperv_logical_total", "cpu_hyperv_root_total", "cpu_hyperv_virtual_total", "cpu_processor_total"):
        item = base.selected_item(host_key, category)
        if item:
            return item
    return metric_by_patterns(host_key, [
        "hyper-v hypervisor logical processor",
        "hyper-v hypervisor root virtual processor",
        "hyper-v hypervisor virtual processor",
        "total run time",
        "processor(_total)\\% processor time",
    ])


def disk_io_values(host_key):
    return {
        "iops": metric_by_patterns(host_key, ["hyper-v disk iops total", "disk transfers/sec", "transfers/sec", "iops", "disk reads/sec", "disk writes/sec"]),
        "throughput": metric_by_patterns(host_key, ["hyper-v disk throughput total", "disk bytes/sec", "read bytes/sec", "write bytes/sec", "bytes/sec", "throughput"]),
        "queue": metric_by_patterns(host_key, ["hyper-v disk queue average", "avg. disk queue length", "current disk queue length", "disk queue", "queue length"]),
        "latency": metric_by_patterns(host_key, ["hyper-v disk latency total", "avg. disk sec/transfer", "avg. disk sec/read", "avg. disk sec/write", "disk sec/read", "disk sec/write", "latency"]),
    }


def severity_class_percent(value, warn, crit):
    if value >= crit:
        return "crit"
    if value >= warn:
        return "warn"
    return "ok"


def spark_points(value, max_value=100.0, width=380, height=92):
    value = max(0.0, min(max_value, float(value or 0)))
    base_pct = value / max_value if max_value else 0
    multipliers = [0.72, 0.82, 0.68, 0.91, 0.78, 1.0, 0.88, 1.08, 0.96, 1.0]
    points = []
    for idx, mult in enumerate(multipliers):
        pct = max(0.04, min(0.98, base_pct * mult))
        x = (width / (len(multipliers) - 1)) * idx
        y = height - (pct * (height - 14)) - 7
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def sparkline(title, value, unit_label, color="#2f80ed", max_value=100.0):
    return f"""
      <div class="chart-card">
        <div class="chart-head"><span>{esc(title)}</span><strong>{esc(unit_label)}</strong></div>
        <svg viewBox="0 0 380 110" preserveAspectRatio="none" class="spark">
          <defs>
            <linearGradient id="fill-{abs(hash(title))}" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="{color}" stop-opacity=".28"/>
              <stop offset="100%" stop-color="{color}" stop-opacity=".02"/>
            </linearGradient>
          </defs>
          <polyline points="0,105 {spark_points(value, max_value, 380, 92)} 380,105" fill="url(#fill-{abs(hash(title))})" stroke="none"/>
          <polyline points="{spark_points(value, max_value, 380, 92)}" fill="none" stroke="{color}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
          <line x1="0" y1="92" x2="380" y2="92" stroke="#dbe4ef" stroke-width="1"/>
        </svg>
      </div>
    """


def radial_gauge(title, percent, center_text):
    pct = max(0.0, min(100.0, float(percent or 0)))
    cls = severity_class_percent(pct, 75, 90)
    color = {"ok": "#22c55e", "warn": "#facc15", "crit": "#ef4444"}[cls]
    dash = pct * 2.64
    return f"""
      <div class="chart-card gauge-card">
        <div class="chart-head"><span>{esc(title)}</span><strong>{pct:.1f}%</strong></div>
        <svg viewBox="0 0 160 120" class="gauge-svg">
          <path d="M30 92 A50 50 0 0 1 130 92" fill="none" stroke="#e6edf5" stroke-width="16" stroke-linecap="round"/>
          <path d="M30 92 A50 50 0 0 1 130 92" fill="none" stroke="{color}" stroke-width="16" stroke-linecap="round" stroke-dasharray="{dash:.1f} 264"/>
          <text x="80" y="75" text-anchor="middle" class="gauge-value">{esc(center_text)}</text>
          <text x="80" y="97" text-anchor="middle" class="gauge-label">{pct:.1f}%</text>
        </svg>
      </div>
    """


def metric_tile(label, value, cls="slate"):
    return f"<div class='host-metric {cls}'><span>{esc(label)}</span><strong>{esc(value)}</strong></div>"


def load_active_problems():
    if ACTIVE_PROBLEMS.exists():
        return json.loads(ACTIVE_PROBLEMS.read_text(encoding="utf-8"))
    return {"hosts": {}}


def severity_info(value):
    names = {
        0: ("INFO", "info"),
        1: ("INFO", "info"),
        2: ("WARNING", "warning"),
        3: ("AVERAGE", "average"),
        4: ("HIGH", "high"),
        5: ("CRITICAL", "critical"),
    }
    try:
        severity = int(value)
    except (TypeError, ValueError):
        severity = 0
    return (*names.get(severity, ("INFO", "info")), severity)


def active_for_duration(clock):
    try:
        started = int(clock or 0)
    except (TypeError, ValueError):
        started = 0
    if started <= 0:
        return "Ativo"
    seconds = max(0, int(datetime.now().timestamp()) - started)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"Ativo há {days}d {hours}h"
    if hours:
        return f"Ativo há {hours}h {minutes}m"
    return f"Ativo há {minutes}m"


def problem_rows(host_key):
    host_data = ACTIVE_PROBLEMS_DATA.get("hosts", {}).get(host_key, {})
    problems = host_data.get("problems_active") or []
    if not problems:
        triggers = host_data.get("triggers_active") or []
        problems = [
            {
                "name": trigger.get("description") or trigger.get("lastEvent", {}).get("name"),
                "severity": trigger.get("priority") or trigger.get("lastEvent", {}).get("severity"),
                "clock": trigger.get("lastchange") or trigger.get("lastEvent", {}).get("clock"),
            }
            for trigger in triggers
            if str(trigger.get("value")) == "1"
        ]

    def sort_key(problem):
        _, _, severity = severity_info(problem.get("severity"))
        try:
            clock = int(problem.get("clock") or 0)
        except (TypeError, ValueError):
            clock = 0
        return (-severity, -clock)

    return sorted(problems, key=sort_key)[:3]


def active_problems_html(host_key):
    problems = problem_rows(host_key)
    if not problems:
        return """
      <div class="problem-ok">
        <strong>OK</strong>
        <span>Sem problemas ativos</span>
      </div>
    """
    rows = []
    for problem in problems:
        label, cls, _ = severity_info(problem.get("severity"))
        name = problem.get("name") or "Problema ativo no Zabbix"
        rows.append(
            "<div class='problem-row'>"
            f"<span class='severity {cls}'>{esc(label)}</span>"
            "<div>"
            f"<strong>{esc(short(name, 92))}</strong>"
            f"<em>{esc(host_key)} · {esc(active_for_duration(problem.get('clock')))}</em>"
            "</div>"
            "</div>"
        )
    return "<div class='problems-list'>" + "".join(rows) + "</div>"


def global_clock_html():
    return """
<div class="global-clock-wrap">
  <section class="global-clock-card">
    <span>Data / Hora</span>
    <strong id="hvClockDate">--/--/----</strong>
    <b id="hvClockTime">--:--:--</b>
    <em>UTC-3</em>
  </section>
  <script>
    (function () {
      function pad(value) { return String(value).padStart(2, '0'); }
      function tick() {
        var localNow = new Date();
        var utcMs = localNow.getTime() + (localNow.getTimezoneOffset() * 60000);
        var now = new Date(utcMs - (3 * 60 * 60 * 1000));
        var date = pad(now.getDate()) + '/' + pad(now.getMonth() + 1) + '/' + now.getFullYear();
        var time = pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
        var dateEl = document.getElementById('hvClockDate');
        var timeEl = document.getElementById('hvClockTime');
        if (dateEl) { dateEl.textContent = date; }
        if (timeEl) { timeEl.textContent = time; }
      }
      tick();
      window.setInterval(tick, 1000);
    }());
  </script>
  <style>
    .global-clock-wrap { width:100%; height:100%; box-sizing:border-box; display:flex; align-items:center; justify-content:center; padding:6px 12px; background:#f4f7fb; color:#172033; font-family:'Segoe UI',Arial,sans-serif; overflow:hidden; }
    .global-clock-card { width:min(430px,100%); min-height:64px; display:grid; grid-template-columns:1fr auto; grid-template-areas:"label tz" "date time"; align-items:center; gap:4px 16px; background:#fff; border:1px solid #d7e0ec; border-left:8px solid #2f80ed; border-radius:14px; padding:10px 18px; box-shadow:0 6px 14px rgba(15,23,42,.08); }
    .global-clock-card span { grid-area:label; color:#526176; font-size:11px; font-weight:900; text-transform:uppercase; }
    .global-clock-card strong { grid-area:date; color:#0f172a; font-size:21px; line-height:1; font-weight:900; }
    .global-clock-card b { grid-area:time; color:#0f172a; font-size:24px; line-height:1; font-weight:900; font-variant-numeric:tabular-nums; }
    .global-clock-card em { grid-area:tz; justify-self:end; border-radius:999px; padding:4px 10px; background:#eef3f8; color:#526176; font-style:normal; font-size:11px; font-weight:900; }
  </style>
</div>
"""


def host_disks_table(host_key):
    rows = []
    for volume in base.disk_volumes(host_key):
        pct = base.disk_volume_percent(volume)
        pct_text = f"{pct:.1f}%" if pct is not None else "-"
        cls = "crit" if pct and pct >= 90 else "warn" if pct and pct >= 80 else "ok"
        free_value = "-"
        if volume.get("free"):
            free_value = base.fmt_value(volume.get("free"), "bytes")
        elif volume.get("total") and volume.get("used"):
            try:
                free_value = base.fmt_value({"lastvalue": float(volume["total"]["lastvalue"]) - float(volume["used"]["lastvalue"]), "units": "B"}, "bytes")
            except (TypeError, ValueError):
                free_value = "-"
        rows.append(
            "<tr>"
            f"<td>{esc(volume.get('volume'))}</td>"
            f"<td class='num'><span class='pill {cls}'>{esc(pct_text)}</span></td>"
            f"<td class='num'>{esc(base.fmt_value(volume.get('used'), 'bytes') if volume.get('used') else '-')}</td>"
            f"<td class='num'>{esc(base.fmt_value(volume.get('total'), 'bytes') if volume.get('total') else '-')}</td>"
            f"<td class='num'>{esc(free_value)}</td>"
            f"<td>{esc(base.fmt_clock(volume.get('pused', {}).get('lastclock') or volume.get('used', {}).get('lastclock')))}</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='6'>Nenhum volume validado</td></tr>"


def host_interfaces_table(host_key):
    items = [
        item for item in base.selected_items(host_key, "net_interfaces")
        if "bits received" in item.get("name", "").lower()
        or "bits sent" in item.get("name", "").lower()
        or (item.get("key_", "").startswith(("net.if.in", "net.if.out")) and "," not in item.get("key_", ""))
    ]
    rows = []
    seen = set()
    for item in items[:6]:
        ident = (item.get("name"), item.get("key_"))
        if ident in seen:
            continue
        seen.add(ident)
        rows.append(
            "<tr>"
            f"<td>{esc(base.interface_label(item))}</td>"
            f"<td>{esc(short(item.get('key_'), 54))}</td>"
            f"<td>{esc(base.traffic_direction(item))}</td>"
            f"<td class='num'>{esc(base.fmt_value(item, 'bps' if item.get('units') == 'bps' else None))}</td>"
            f"<td>{esc(base.fmt_clock(item.get('lastclock')))}</td>"
            f"<td>{esc(item.get('validation_source') or 'zabbix_api')}</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='6'>Nenhuma interface validada</td></tr>"


def host_errors_table(host_key):
    items = base.selected_items(host_key, "net_errors") + base.selected_items(host_key, "net_drops")
    rows = []
    seen = set()
    for item in items[:6]:
        ident = (item.get("name"), item.get("key_"))
        if ident in seen:
            continue
        seen.add(ident)
        name = item.get("name", "")
        kind = "erro" if "error" in name.lower() else "drop/discard"
        value = number_value(item)
        cls = "crit" if value > 0 else "ok"
        rows.append(
            "<tr>"
            f"<td>{esc(short(name, 66))}</td>"
            f"<td>{esc(kind)}</td>"
            f"<td class='num'><span class='pill {cls}'>{esc(base.fmt_value(item))}</span></td>"
            f"<td>{esc(base.fmt_clock(item.get('lastclock')))}</td>"
            "</tr>"
        )
    return "".join(rows) or "<tr><td colspan='4'>Nenhum erro/drop detectado</td></tr>"


def host_operational_summary(host_key):
    vals = host_summary_values(host_key)
    status = base.selected_item(host_key, "availability") or {}
    used_pct = memory_percent(host_key)
    return f"""
      <div class="summary-grid">
        <div><span>Status</span><strong>{esc(vals['status'].title())}</strong></div>
        <div><span>CPU</span><strong>{cpu_percent(host_key):.1f}%</strong></div>
        <div><span>RAM</span><strong>{used_pct:.1f}%</strong></div>
        <div><span>Disco crítico</span><strong>{esc(vals['disk'])}</strong></div>
        <div><span>Uptime</span><strong>{esc(vals['uptime'])}</strong></div>
        <div><span>Problemas</span><strong>{esc(vals['problems'])}</strong></div>
        <div><span>Última coleta</span><strong>{esc(base.fmt_clock(status.get('lastclock')))}</strong></div>
      </div>
    """


def full_host_block(host_key):
    vals = host_summary_values(host_key)
    cpu = cpu_percent(host_key)
    hyperv_cpu = hyperv_cpu_value(host_key)
    hyperv_cpu_text = formatted_metric_or_waiting(hyperv_cpu, "percent")
    mem_pct = memory_percent(host_key)
    net_in = selected_net_value(host_key, "net_in")
    net_out = selected_net_value(host_key, "net_out")
    critical = base.critical_disk(host_key)
    disk_pct = base.disk_volume_percent(critical) if critical else 0.0
    disk_io = disk_io_values(host_key)
    problem_count = base.active_problems_count(host_key)
    events = "Sem eventos recentes" if problem_count == 0 else f"{problem_count} evento(s) ativo(s) no Zabbix"
    return f"""
<div class="host-panel {vals['state']}">
  <header class="host-title">
    <div>
      <h2>{esc(host_key)}</h2>
      <p>Monitoramento executivo e técnico do host físico Hyper-V</p>
    </div>
    <span class="host-status-pill">{esc(vals['status'])}</span>
  </header>

  <section class="metrics-row">
    {metric_tile('Status', vals['status'].title(), 'green' if vals['state'] == 'online' else 'red')}
    {metric_tile('Uptime', vals['uptime'], 'green')}
    {metric_tile('CPU host fallback', f'{cpu:.1f}%', severity_class_percent(cpu, 70, 85))}
    {metric_tile('CPU Hyper-V real', hyperv_cpu_text, 'blue' if hyperv_cpu else 'slate')}
    {metric_tile('Memória usada', vals['memory'], 'slate')}
    {metric_tile('Disco crítico', vals['disk'], severity_class_percent(disk_pct or 0, 80, 90))}
    {metric_tile('Problemas ativos', vals['problems'], 'green' if vals['problems'] == '0' else 'red')}
  </section>

  <section class="metrics-row disk-io-row">
    {metric_tile('IOPS disco', formatted_metric_or_waiting(disk_io['iops']), 'blue' if disk_io['iops'] else 'slate')}
    {metric_tile('Throughput disco', formatted_metric_or_waiting(disk_io['throughput'], 'Bps'), 'blue' if disk_io['throughput'] else 'slate')}
    {metric_tile('Fila disco', formatted_metric_or_waiting(disk_io['queue']), 'yellow' if disk_io['queue'] else 'slate')}
    {metric_tile('Latência disco', formatted_metric_or_waiting(disk_io['latency'], 'ms_from_seconds'), 'yellow' if disk_io['latency'] else 'slate')}
  </section>

  <section class="charts-row">
    {sparkline('CPU host fallback', cpu, f'{cpu:.1f}%', '#2f80ed', 100)}
    {radial_gauge('Memória usada %', mem_pct, 'RAM')}
    {sparkline('Rede entrada', net_in, fmt_bps(net_in), '#22a85a', max(net_in * 1.4, 1000))}
    {sparkline('Rede saída', net_out, fmt_bps(net_out), '#475569', max(net_out * 1.4, 1000))}
  </section>

  <section class="tables-row two">
    <article class="data-card">
      <h3>Todos os discos</h3>
      <table><thead><tr><th>Volume</th><th>Uso</th><th>Usado</th><th>Total</th><th>Livre</th><th>Última coleta</th></tr></thead><tbody>{host_disks_table(host_key)}</tbody></table>
    </article>
    <article class="data-card event-card">
      <h3>Problemas ativos</h3>
      {active_problems_html(host_key)}
    </article>
  </section>
</div>
{host_block_css()}
"""


def host_block_css():
    return """
<style>
  .host-panel { width:100%; height:100%; box-sizing:border-box; padding:clamp(12px,.75vw,20px); background:#f4f7fb; color:#172033; font-family:'Segoe UI',Arial,sans-serif; overflow:hidden; }
  .host-panel * { box-sizing:border-box; }
  .host-title { display:flex; align-items:flex-start; justify-content:space-between; gap:14px; margin-bottom:10px; background:#fff; border:1px solid #d7e0ec; border-left:10px solid #22c55e; border-radius:14px; padding:14px 18px; box-shadow:0 6px 14px rgba(15,23,42,.08); }
  .host-panel.offline .host-title { border-left-color:#ef4444; }
  .host-title h2 { margin:0; font-size:clamp(28px,1.65vw,42px); line-height:1; color:#0f172a; font-weight:900; }
  .host-title p { margin:7px 0 0; color:#526176; font-size:clamp(12px,.72vw,18px); font-weight:800; }
  .host-status-pill { flex:0 0 auto; border-radius:999px; padding:8px 18px; font-size:clamp(12px,.72vw,18px); font-weight:900; background:#dcfce7; color:#166534; }
  .host-panel.offline .host-status-pill { background:#fee2e2; color:#991b1b; }
  .metrics-row { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:10px; margin-bottom:10px; }
  .disk-io-row { grid-template-columns:repeat(4,minmax(0,1fr)); }
  .host-metric { min-height:86px; background:#fff; border:1px solid #d7e0ec; border-top:7px solid #64748b; border-radius:13px; padding:12px 14px; box-shadow:0 5px 12px rgba(15,23,42,.07); overflow:hidden; }
  .host-metric span { display:block; color:#526176; font-size:clamp(11px,.65vw,16px); font-weight:900; text-transform:uppercase; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .host-metric strong { display:block; color:#0f172a; font-size:clamp(21px,1.25vw,34px); line-height:1.05; margin-top:12px; font-weight:900; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .host-metric.green,.host-metric.ok { border-top-color:#22c55e; }
  .host-metric.red,.host-metric.crit { border-top-color:#ef4444; }
  .host-metric.warn,.host-metric.yellow { border-top-color:#facc15; }
  .host-metric.blue { border-top-color:#2f80ed; }
  .host-metric.slate { border-top-color:#64748b; }
  .charts-row { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin-bottom:10px; }
  .chart-card,.data-card { background:#fff; border:1px solid #d7e0ec; border-radius:13px; padding:12px 14px; box-shadow:0 5px 12px rgba(15,23,42,.07); overflow:hidden; }
  .chart-head { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:7px; }
  .chart-head span,.data-card h3 { margin:0; color:#526176; font-size:clamp(12px,.7vw,18px); font-weight:900; text-transform:uppercase; }
  .chart-head strong { color:#0f172a; font-size:clamp(19px,1.05vw,28px); font-weight:900; white-space:nowrap; }
  .spark { width:100%; height:118px; display:block; }
  .gauge-card { min-height:164px; }
  .gauge-svg { width:100%; height:118px; display:block; }
  .gauge-value { font-size:20px; fill:#0f172a; font-weight:900; }
  .gauge-label { font-size:15px; fill:#526176; font-weight:900; }
  .tables-row { display:grid; gap:10px; margin-bottom:10px; }
  .tables-row.two { grid-template-columns:1.35fr .65fr; margin-bottom:0; }
  .data-card h3 { margin-bottom:9px; color:#0f172a; }
  table { width:100%; border-collapse:separate; border-spacing:0; table-layout:fixed; font-size:clamp(11px,.62vw,16px); }
  th { text-align:left; color:#526176; background:#eef3f8; text-transform:uppercase; font-size:clamp(10px,.54vw,14px); font-weight:900; padding:7px 8px; border-bottom:1px solid #dbe4ef; }
  td { padding:7px 8px; border-bottom:1px solid #e6edf5; color:#172033; font-weight:750; vertical-align:top; overflow-wrap:anywhere; line-height:1.2; }
  tr:last-child td { border-bottom:0; }
  .num { text-align:right; font-variant-numeric:tabular-nums; }
  .pill { border-radius:999px; padding:4px 9px; font-size:clamp(10px,.52vw,13px); font-weight:900; display:inline-block; }
  .pill.ok,.pill.normal { background:#dcfce7; color:#166534; }
  .pill.warn { background:#fef3c7; color:#92400e; }
  .pill.crit { background:#fee2e2; color:#991b1b; }
  .event-card { display:flex; flex-direction:column; }
  .event-text { flex:1; min-height:118px; display:flex; align-items:center; justify-content:center; text-align:center; color:#0f172a; font-size:clamp(22px,1.25vw,34px); font-weight:900; background:#eef3f8; border-radius:10px; padding:12px; }
  .problems-list { flex:1; min-height:118px; display:grid; gap:8px; align-content:center; }
  .problem-row { min-width:0; display:grid; grid-template-columns:auto minmax(0,1fr); gap:10px; align-items:center; background:#eef3f8; border-radius:10px; padding:9px 10px; }
  .problem-row strong { display:block; color:#0f172a; font-size:clamp(14px,.82vw,22px); line-height:1.12; font-weight:900; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .problem-row em { display:block; margin-top:5px; color:#526176; font-size:clamp(11px,.62vw,16px); line-height:1; font-style:normal; font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .severity { border-radius:999px; padding:6px 10px; color:#fff; font-size:clamp(10px,.58vw,15px); font-weight:900; letter-spacing:.03em; }
  .severity.critical { background:#dc2626; }
  .severity.high { background:#f97316; }
  .severity.warning { background:#facc15; color:#713f12; }
  .severity.average { background:#f59e0b; color:#78350f; }
  .severity.info { background:#2f80ed; }
  .problem-ok { flex:1; min-height:118px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; text-align:center; background:#dcfce7; color:#166534; border-radius:10px; padding:12px; }
  .problem-ok strong { font-size:clamp(24px,1.45vw,38px); line-height:1; font-weight:900; }
  .problem-ok span { font-size:clamp(15px,.9vw,24px); font-weight:900; }
  .summary-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }
  .summary-grid div { min-width:0; background:#eef3f8; border-radius:9px; padding:8px 10px; }
  .summary-grid span { display:block; color:#526176; font-size:clamp(10px,.54vw,14px); font-weight:900; text-transform:uppercase; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .summary-grid strong { display:block; margin-top:6px; color:#0f172a; font-size:clamp(15px,.82vw,22px); font-weight:900; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
</style>
"""
def details_section(panels, pid, y, uid, discovery, host_key):
    host = base.zabbix_hostname(discovery, host_key)
    panels.append(html_panel(pid, f"{host} - Detalhes completos", 0, y, 24, 5, section_header(host_key)))
    pid += 1
    y += 5

    panels.append(cpu_timeseries(pid, host, 0, y, 12, 7, uid, discovery, host_key))
    pid += 1
    panels.append(memory_percent_gauge(pid, host, 12, y, 12, 7, uid, discovery, host_key))
    pid += 1
    y += 7

    pid = net_timeseries(panels, pid, uid, discovery, host_key, "net_in", f"{host} - Rede entrada", 0, y)
    pid = net_timeseries(panels, pid, uid, discovery, host_key, "net_out", f"{host} - Rede saída", 12, y)
    y += 7

    panels.append(html_panel(pid, f"{host} - Todos os discos", 0, y, 24, 8, disk_table_html(host_key)))
    pid += 1
    y += 8

    panels.append(polish_native_panel(base.critical_disk_panel(pid, f"{host} - Disco mais crítico", 0, y, 8, uid, discovery, host_key)))
    pid += 1
    panels.append(html_panel(pid, f"{host} - Interfaces detectadas", 8, y, 16, 6, interfaces_table_html(host_key)))
    pid += 1
    y += 6

    panels.append(html_panel(pid, f"{host} - Erros/Drops de rede", 0, y, 12, 6, errors_table_html(host_key)))
    pid += 1
    panels.append(html_panel(pid, f"{host} - Problemas ativos", 12, y, 12, 6, problems_card_html(host_key)))
    pid += 1
    y += 6

    panels.append(html_panel(pid, f"{host} - Eventos recentes", 0, y, 12, 6, events_html(host_key, host)))
    pid += 1
    panels.append(html_panel(pid, f"{host} - Resumo operacional", 12, y, 12, 6, operational_summary_html(host_key)))
    pid += 1
    y += 6
    return pid, y


def build_dashboard(discovery):
    panels = []
    pid = 1
    y = 0
    panels.append(html_panel(pid, "", 0, y, 24, 4, global_clock_html()))
    pid += 1
    y += 4
    host_positions = {
        "HYPERV_HOST_A": {"x": 0, "y": y, "w": 24, "h": 22},
        "HYPERV-HYPERV_HOST_B": {"x": 0, "y": y + 22, "w": 24, "h": 22},
    }
    for host_key in HOSTS:
        pos = host_positions[host_key]
        panels.append(html_panel(pid, "", pos["x"], pos["y"], pos["w"], pos["h"], full_host_block(host_key)))
        pid += 1

    return {
        "id": None,
        "uid": "hyperv-hosts-executivo-v2",
        "title": "Hyper-V Hosts - Monitoramento Executivo V2",
        "tags": ["hyper-v", "zabbix", "windows", "noc", "executivo", "v2"],
        "timezone": "browser",
        "schemaVersion": 38,
        "version": 1,
        "style": "light",
        "editable": True,
        "graphTooltip": 1,
        "refresh": "30s",
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
                    "current": {"selected": True, "text": "30s", "value": "30s"},
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


def validate_dashboard(dashboard):
    forbidden = [
        "CPU User Time",
        "CPU Privileged Time",
        "Item nao validado",
        "Item não validado",
        "$host",
        "HYPERV_HOST_A",
        "SEU_IP_PRIVADO.",
    ]
    raw = json.dumps(dashboard, ensure_ascii=False)
    expected_details = [
        "",
    ]
    expected_text = [
        "Status",
        "Uptime",
        "CPU",
        "Memória",
        "Rede entrada",
        "Rede saída",
        "Todos os discos",
        "Disco crítico",
        "Problemas ativos",
    ]
    sections = {}
    for host in HOSTS:
        host_panels = [
            panel for panel in dashboard["panels"]
            if host in panel.get("title", "") or host in panel.get("options", {}).get("content", "")
        ]
        titles = [panel.get("title") for panel in host_panels]
        host_content = "\n".join(panel.get("options", {}).get("content", "") for panel in host_panels)
        sections[host] = {
            "panel_count": len(host_panels),
            "details_found": all(text in host_content for text in expected_text),
            "titles": titles,
        }
    return {
        "dashboard": str(OUTPUT),
        "uid": dashboard["uid"],
        "title": dashboard["title"],
        "datasource_uid": UID,
        "panel_count": len(dashboard["panels"]),
        "forbidden_terms_found": [item for item in forbidden if item in raw],
        "sections": sections,
    }


def main():
    global DISCOVERY_DATA, ACTIVE_PROBLEMS_DATA
    discovery = base.load_discovery()
    DISCOVERY_DATA = discovery
    ACTIVE_PROBLEMS_DATA = load_active_problems()
    base.VALIDATED = base.load_validation()
    base.RENDERED = base.load_render_validation()
    dashboard = build_dashboard(discovery)
    OUTPUT.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = validate_dashboard(dashboard)
    SUMMARY.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
