#!/usr/bin/env python3
import html
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
METRICS = LOGS / "hyperv-vms-metrics-validation.json"
OUTPUT = ROOT / "dashboard-hyperv-vms.json"
SUMMARY = LOGS / "hyperv-vms-dashboard-render-validation.json"
UID = "hyperv-vms-executivo"
TITLE = "Hyper-V VMs - Monitoramento Executivo"
HOSTS = ["HYPERV_HOST_A", "HYPERV-HYPERV_HOST_B"]


def esc(value):
    return html.escape(str(value if value is not None else ""))


def short(value, limit=42):
    text = str(value or "-")
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def state_class(state):
    state_l = str(state or "").lower()
    if state_l == "running":
        return "ok"
    if state_l == "off":
        return "off"
    if state_l in {"paused", "suspended", "saved", "saving"}:
        return "warn"
    return "crit"


def fmt_mem(mb):
    try:
        value = float(mb)
    except (TypeError, ValueError):
        return "-"
    if value >= 1024:
        return f"{value / 1024:.1f} GB"
    return f"{value:.0f} MB"


def fmt_mbps(value):
    try:
        return f"{float(value):.2f} Mbps"
    except (TypeError, ValueError):
        return "-"


def css():
    return """
<style>
  .vm-noc { width:100%; height:100%; box-sizing:border-box; background:#f4f7fb; color:#172033; font-family:'Segoe UI',Arial,sans-serif; overflow:hidden; padding:10px 14px; }
  .vm-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:12px; height:100%; }
  .vm-card { background:#fff; border:1px solid #d7e0ec; border-radius:18px; box-shadow:0 9px 22px rgba(15,23,42,.09); overflow:hidden; box-sizing:border-box; }
  .vm-kpi { min-height:108px; height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; border-top:9px solid #64748b; }
  .vm-kpi.ok { border-top-color:#22c55e; } .vm-kpi.warn { border-top-color:#facc15; } .vm-kpi.crit { border-top-color:#ef4444; } .vm-kpi.blue { border-top-color:#2f80ed; }
  .vm-kpi span { color:#526176; font-size:15px; font-weight:900; text-transform:uppercase; text-align:center; }
  .vm-kpi strong { margin-top:7px; color:#0f172a; font-size:46px; line-height:1; font-weight:900; text-align:center; }
  .vm-host { display:flex; flex-direction:column; gap:11px; height:100%; }
  .vm-head { min-height:132px; padding:15px 18px; border-left:11px solid #2f80ed; }
  .vm-headline { display:flex; align-items:flex-start; justify-content:space-between; gap:15px; margin-bottom:12px; }
  .vm-headline h2 { margin:0; font-size:36px; line-height:1; color:#0f172a; font-weight:950; }
  .vm-headline small { display:block; margin-top:7px; color:#526176; font-size:15px; font-weight:850; }
  .vm-pill { border-radius:999px; padding:6px 12px; font-size:12px; font-weight:950; text-transform:uppercase; white-space:nowrap; }
  .vm-pill.ok { background:#dcfce7; color:#166534; } .vm-pill.off { background:#e5e7eb; color:#374151; } .vm-pill.warn { background:#fef3c7; color:#92400e; } .vm-pill.crit { background:#fee2e2; color:#991b1b; }
  .vm-mini { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; }
  .vm-mini div { background:#eef3f8; border-radius:12px; border-top:6px solid #64748b; min-height:66px; padding:9px 11px; box-sizing:border-box; overflow:hidden; }
  .vm-mini span { display:block; color:#526176; font-size:12px; font-weight:950; text-transform:uppercase; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .vm-mini strong { display:block; margin-top:6px; color:#111827; font-size:25px; font-weight:950; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .vm-mini .ok { border-top-color:#22c55e; } .vm-mini .off { border-top-color:#94a3b8; } .vm-mini .warn { border-top-color:#facc15; } .vm-mini .crit { border-top-color:#ef4444; } .vm-mini .blue { border-top-color:#2f80ed; }
  .vm-columns { display:grid; grid-template-columns:1.25fr .75fr; gap:12px; align-items:start; }
  .vm-section { padding:14px 16px; }
  .vm-title { display:flex; align-items:center; justify-content:space-between; gap:10px; margin:0 0 10px; }
  .vm-title strong { color:#0f172a; font-size:17px; font-weight:950; }
  .vm-title span { color:#526176; font-size:12px; font-weight:850; text-transform:uppercase; }
  .vm-table { width:100%; border-collapse:separate; border-spacing:0; table-layout:fixed; font-size:13px; }
  .vm-table th { text-align:left; background:#eef3f8; color:#526176; font-size:11px; font-weight:950; text-transform:uppercase; padding:9px 8px; border-bottom:1px solid #dbe4ef; }
  .vm-table td { padding:9px 8px; border-bottom:1px solid #e6edf5; color:#172033; font-weight:760; vertical-align:middle; overflow-wrap:anywhere; }
  .vm-table tr:last-child td { border-bottom:0; }
  .vm-table .num { text-align:right; font-variant-numeric:tabular-nums; }
  .bar { height:12px; border-radius:999px; background:#e2e8f0; overflow:hidden; }
  .bar i { display:block; height:100%; border-radius:999px; background:linear-gradient(90deg,#22c55e,#2f80ed); }
  .vm-list { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:11px; flex:1; align-content:start; }
  .vm-tile { border-radius:16px; background:#f8fafc; border:1px solid #dbe4ef; padding:13px 15px; min-height:170px; box-sizing:border-box; border-left:8px solid #94a3b8; }
  .vm-tile.ok { border-left-color:#22c55e; } .vm-tile.off { border-left-color:#94a3b8; } .vm-tile.warn { border-left-color:#facc15; } .vm-tile.crit { border-left-color:#ef4444; }
  .vm-tile-top { display:flex; justify-content:space-between; align-items:flex-start; gap:9px; margin-bottom:12px; }
  .vm-tile-name { font-size:20px; font-weight:950; color:#0f172a; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .vm-kv { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px 12px; }
  .vm-kv span { color:#526176; font-size:11px; font-weight:950; text-transform:uppercase; display:block; }
  .vm-kv strong { color:#172033; font-size:15px; font-weight:900; display:block; margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .muted { color:#526176; font-weight:800; }
</style>
"""


def metric(label, value, cls="blue"):
    return f"<div class='vm-card vm-kpi {cls}'><span>{esc(label)}</span><strong>{esc(value)}</strong></div>"


def top_html(data):
    totals = {"vms": 0, "running": 0, "off": 0, "checkpoints": 0}
    for host in HOSTS:
        summary = data.get("summary", {}).get(host, {})
        totals["vms"] += int(summary.get("total", 0))
        totals["running"] += int(summary.get("running", 0))
        totals["off"] += int(summary.get("off", 0))
        totals["checkpoints"] += int(summary.get("checkpoints", 0))
    generated = data.get("generated_at", datetime.now().isoformat(timespec="seconds")).replace("T", " ")
    return f"""
<div class="vm-noc">
  <section class="vm-grid">
    {metric('Total de VMs', totals['vms'], 'blue')}
    {metric('VMs ligadas', totals['running'], 'ok')}
    {metric('VMs desligadas', totals['off'], 'off')}
    {metric('Checkpoints', totals['checkpoints'], 'warn' if totals['checkpoints'] else 'ok')}
    {metric('Última coleta', generated[11:16], 'blue')}
  </section>
  {css()}
</div>
"""


def mini(label, value, cls="blue"):
    return f"<div class='{cls}'><span>{esc(label)}</span><strong>{esc(value)}</strong></div>"


def vm_tile(vm):
    cls = state_class(vm.get("state"))
    cpu = float(vm.get("cpu_usage_percent") or 0)
    return f"""
<article class="vm-tile {cls}">
  <div class="vm-tile-top">
    <div class="vm-tile-name" title="{esc(vm.get('name'))}">{esc(short(vm.get('name'), 32))}</div>
    <span class="vm-pill {cls}">{esc(vm.get('state'))}</span>
  </div>
  <div class="vm-kv" style="grid-template-columns:repeat(4,minmax(0,1fr));">
    <div><span>CPU</span><strong>{cpu:.1f}%</strong></div>
    <div><span>Memória</span><strong>{esc(fmt_mem(vm.get('assigned_memory_mb')))}</strong></div>
    <div><span>Uptime</span><strong>{esc(vm.get('uptime'))}</strong></div>
    <div><span>Checkpoints</span><strong>{esc(vm.get('checkpoint_count'))}</strong></div>
    <div><span>VHDX</span><strong>{esc(vm.get('vhd_count'))}</strong></div>
    <div><span>Entrada</span><strong>{esc(fmt_mbps(vm.get('traffic_in_mbps')))}</strong></div>
    <div><span>Saída</span><strong>{esc(fmt_mbps(vm.get('traffic_out_mbps')))}</strong></div>
    <div><span>Status</span><strong>{esc(vm.get('status'))}</strong></div>
  </div>
</article>
"""


def table_rows(vms, limit=10):
    rows = []
    for vm in vms[:limit]:
        cls = state_class(vm.get("state"))
        cpu = float(vm.get("cpu_usage_percent") or 0)
        rows.append(
            "<tr>"
            f"<td title='{esc(vm.get('name'))}'>{esc(short(vm.get('name'), 34))}</td>"
            f"<td><span class='vm-pill {cls}'>{esc(vm.get('state'))}</span></td>"
            f"<td class='num'>{cpu:.1f}%</td>"
            f"<td><div class='bar'><i style='width:{max(2, min(100, cpu)):.0f}%'></i></div></td>"
            f"<td class='num'>{esc(fmt_mem(vm.get('assigned_memory_mb')))}</td>"
            f"<td class='num'>{esc(vm.get('checkpoint_count'))}</td>"
            f"<td class='num'>{esc(vm.get('vhd_count'))}</td>"
            f"<td class='num'>{esc(fmt_mbps(vm.get('traffic_in_mbps')))}</td>"
            f"<td class='num'>{esc(fmt_mbps(vm.get('traffic_out_mbps')))}</td>"
            f"<td class='num'>{esc(vm.get('uptime'))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append("<tr><td colspan='10' class='muted'>Nenhuma VM retornada pela coleta WMI.</td></tr>")
    return "\n".join(rows)


def disk_rows(vms, limit=12):
    rows = []
    for vm in vms:
        paths = vm.get("vhd_paths") or []
        shown = paths[:3] or ["-"]
        rows.append(
            "<tr>"
            f"<td title='{esc(vm.get('name'))}'>{esc(short(vm.get('name'), 36))}</td>"
            f"<td class='num'>{esc(vm.get('vhd_count'))}</td>"
            f"<td>{esc(short(' | '.join(shown), 92))}</td>"
            "</tr>"
        )
        if len(rows) >= limit:
            break
    return "\n".join(rows) if rows else "<tr><td colspan='3' class='muted'>Sem VHDX detectado.</td></tr>"


def host_html(host, host_data):
    vms = host_data.get("vms", [])
    total = len(vms)
    running = sum(1 for vm in vms if vm.get("state") == "Running")
    off = sum(1 for vm in vms if vm.get("state") == "Off")
    checkpoints = sum(int(vm.get("checkpoint_count") or 0) for vm in vms)
    top_cpu = max(vms, key=lambda vm: float(vm.get("cpu_usage_percent") or 0), default={})
    tiles = "\n".join(vm_tile(vm) for vm in vms) or "<div class='muted'>Nenhuma VM detectada.</div>"
    return f"""
<div class="vm-noc">
  <section class="vm-host">
    <article class="vm-card vm-head">
      <div class="vm-headline">
        <div><h2>{esc(host)}</h2><small>VMs Hyper-V coletadas pelo host, sem agent dentro das VMs</small></div>
        <span class="vm-pill ok">somente leitura</span>
      </div>
      <div class="vm-mini">
        {mini('Total de VMs', total, 'blue')}
        {mini('Ligadas', running, 'ok')}
        {mini('Desligadas', off, 'off')}
        {mini('Checkpoints', checkpoints, 'warn' if checkpoints else 'ok')}
        {mini('Maior CPU', f"{short(top_cpu.get('name'), 18)} {top_cpu.get('cpu_usage_percent', 0)}%", 'crit' if float(top_cpu.get('cpu_usage_percent') or 0) > 80 else 'blue')}
      </div>
    </article>
    <section class="vm-list">{tiles}</section>
  </section>
  {css()}
</div>
"""


def panel(pid, title, x, y, w, h, content):
    return {
        "id": pid,
        "type": "text",
        "title": title,
        "transparent": True,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "options": {"mode": "html", "content": content},
    }


def main():
    if not METRICS.exists():
        raise SystemExit("Execute scripts/collect_hyperv_vm_metrics.py antes de gerar a dashboard.")
    data = json.loads(METRICS.read_text())
    panels = [panel(1, "Resumo das VMs Hyper-V", 0, 0, 24, 4, top_html(data))]
    y = 4
    pid = 2
    for host in HOSTS:
        panels.append(panel(pid, host, 0, y, 24, 24, host_html(host, data.get("hosts", {}).get(host, {}))))
        pid += 1
        y += 24
    dashboard = {
        "id": None,
        "uid": UID,
        "title": TITLE,
        "tags": ["hyper-v", "vms", "executivo", "zabbix"],
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 1,
        "refresh": "30s",
        "style": "light",
        "time": {"from": "now-1h", "to": "now"},
        "panels": panels,
        "templating": {"list": []},
        "annotations": {"list": []},
    }
    OUTPUT.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n")
    validation = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dashboard": str(OUTPUT),
        "uid": UID,
        "title": TITLE,
        "hosts": {
            host: {
                "vm_count": len(data.get("hosts", {}).get(host, {}).get("vms", [])),
                "running": sum(1 for vm in data.get("hosts", {}).get(host, {}).get("vms", []) if vm.get("state") == "Running"),
                "off": sum(1 for vm in data.get("hosts", {}).get(host, {}).get("vms", []) if vm.get("state") == "Off"),
                "has_real_data": bool(data.get("hosts", {}).get(host, {}).get("vms")),
            }
            for host in HOSTS
        },
        "vm_operational_changes": False,
        "forbidden_commands_executed": [],
        "visual_base": "V2 hosts: HTML/CSS cards, TV/fullscreen, sem paineis nativos crus",
        "fullscreen_fit": {
            "target": "1920x1080 kiosk",
            "grid_rows_total": y,
            "panels": "topo 4 rows + 2 hosts de 24 rows",
            "vm_card_grid": "4 colunas por host com escala ampliada para 3840x2160",
        },
    }
    SUMMARY.write_text(json.dumps(validation, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(validation, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
