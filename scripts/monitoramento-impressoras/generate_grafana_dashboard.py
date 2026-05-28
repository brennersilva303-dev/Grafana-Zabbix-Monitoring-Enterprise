#!/usr/bin/env python3
import html
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
INV = ROOT / "dashboards" / "printers-inventory.json"
DS_FILE = ROOT / "dashboards" / "zabbix-datasource.json"
OUT = ROOT / "dashboards" / "printer-dashboard.json"
SETUP_REPORT = ROOT / "dashboards" / "zabbix-printers-setup-report.json"
MOCKUP_DIR = ROOT / "docs" / "mockups"

ds_info = json.loads(DS_FILE.read_text()) if DS_FILE.exists() else {}
DS_UID = ds_info.get("uid") or os.getenv("GRAFANA_DATASOURCE_UID") or "zabbix"
DS_NAME = ds_info.get("name") or os.getenv("GRAFANA_DATASOURCE_NAME") or "Zabbix"
DS_TYPE = ds_info.get("type") or os.getenv("GRAFANA_DATASOURCE_TYPE") or "alexanderzobnin-zabbix-datasource"


def setup_status():
    if not SETUP_REPORT.exists():
        return {}
    report = json.loads(SETUP_REPORT.read_text())
    result = {}
    for item in report.get("printers", []):
        result[item.get("host")] = item
        result[item.get("name")] = item
        result[item.get("ip")] = item
    return result


SETUP_STATUS = setup_status()


def choose(printer, keys):
    by_key = printer.get("items_by_key") or {}
    for key in keys:
        item = by_key.get(key)
        if item:
            return item
    return {}


def official_online(printer):
    return (printer.get("official_status") or "").strip().lower() == "online"


def ping_ok(printer):
    status = SETUP_STATUS.get(printer.get("name")) or SETUP_STATUS.get(printer.get("ip"))
    if status and "ping_ok" in status:
        return bool(status["ping_ok"])
    item = choose(printer, ["printer.ping", "icmpping"])
    return str(item.get("lastvalue")) in ("1", "1.0")


def snmp_ok(printer):
    status = SETUP_STATUS.get(printer.get("name")) or SETUP_STATUS.get(printer.get("ip"))
    if status and "snmp_ok" in status:
        return bool(status["snmp_ok"])
    item = choose(printer, ["printer.snmp.available"])
    return bool(item.get("lastclock")) and str(item.get("lastclock")) != "0"


def last_collection(printer):
    clocks = []
    for item in (printer.get("items_by_key") or {}).values():
        try:
            clock = int(item.get("lastclock") or 0)
            if clock:
                clocks.append(clock)
        except Exception:
            pass
    if not clocks:
        return "Sem coleta"
    return datetime.fromtimestamp(max(clocks)).strftime("%d/%m/%Y %H:%M")


def esc(value):
    return html.escape(str(value or ""))


def state_class(printer):
    if not official_online(printer):
        return "offline"
    if not snmp_ok(printer):
        return "nosnmp"
    if not last_collection(printer) or last_collection(printer) == "Sem coleta":
        return "nodata"
    return "online"


def state_label(printer):
    return "ONLINE" if official_online(printer) else "OFFLINE"


def yes_no(value, warning=False):
    if warning and not value:
        return "<span class='mini warn'>SEM SNMP</span>"
    return "<span class='mini ok'>OK</span>" if value else "<span class='mini bad'>FALHA</span>"


def text_panel(panel_id, content, x, y, w, h):
    return {
        "id": panel_id,
        "type": "text",
        "title": "",
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "transparent": True,
        "pluginVersion": "SEU_IP_PRIVADO",
        "options": {"mode": "html", "content": content},
    }


def metric_card(label, value, cls):
    return f"<div class='metric {cls}'><span>{esc(label)}</span><strong>{esc(value)}</strong></div>"


def printer_card(printer):
    cls = state_class(printer)
    sector = printer.get("sector") or "-"
    return f"""
    <article class="printer-card {cls}">
      <div class="line line-top">
        <strong title="{esc(printer.get('name'))}">{esc(printer.get('name'))}</strong>
        <span>{state_label(printer)}</span>
      </div>
      <div class="line split"><em>{esc(sector)}</em><b>{esc(printer.get('ip'))}</b></div>
      <div class="line model">{esc(printer.get('model'))}</div>
      <div class="line serial">{esc(printer.get('serial'))}</div>
      <div class="line signals">
        <div>Ping {yes_no(ping_ok(printer))}</div>
        <div>SNMP {yes_no(snmp_ok(printer), True)}</div>
        <div>{esc(last_collection(printer))}</div>
      </div>
    </article>
    """


def compact_table(printers):
    rows = []
    important = [p for p in printers if not official_online(p) or not snmp_ok(p)]
    for printer in important[:8]:
        rows.append(
            "<tr>"
            f"<td>{esc(printer.get('name'))}</td>"
            f"<td>{esc(printer.get('ip'))}</td>"
            f"<td><span class='status-dot {state_class(printer)}'>{state_label(printer)}</span></td>"
            f"<td>{esc(last_collection(printer))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append("<tr><td colspan='4'>Nenhum incidente ativo</td></tr>")
    return "".join(rows)


def css_clamp(min_value, preferred, max_value):
    return max(min_value, min(preferred, max_value))


def validate_tv_layout(total_cards):
    columns = 6
    rows = (total_cards + columns - 1) // columns
    results = []
    for viewport_w, viewport_h in ((1920, 1080), (3840, 2160)):
        available_h = viewport_h - 30
        margin = css_clamp(6, available_h * 0.006, 14)
        gap = css_clamp(6, available_h * 0.0045, 14)
        top_h = css_clamp(72, available_h * 0.08, 170)
        grid_h = available_h - (margin * 2) - top_h - gap
        grid_w = viewport_w - (margin * 2)
        card_h = (grid_h - (rows - 1) * gap) / rows
        card_w = (grid_w - (columns - 1) * gap) / columns
        grid_ratio = grid_h / available_h
        report = {
            "viewport": f"{viewport_w}x{viewport_h}",
            "colunas": columns,
            "linhas": rows,
            "altura_util": round(available_h, 2),
            "altura_topo": round(top_h, 2),
            "altura_grid": round(grid_h, 2),
            "grid_percentual_altura": round(grid_ratio * 100, 2),
            "largura_card_estimada": round(card_w, 2),
            "altura_card_estimada": round(card_h, 2),
            "total_cards": total_cards,
            "status": "APROVADO",
        }
        if rows > 7 or grid_ratio < 0.80 or card_h < 110 or card_w < 300 or top_h > available_h * 0.15:
            report["status"] = "REPROVADO"
            raise RuntimeError(f"Layout TV invalido: {report}")
        results.append(report)
    return results


def build_dashboard_html(printers):
    total = len(printers)
    online_count = sum(1 for p in printers if official_online(p))
    offline_count = total - online_count
    snmp_down = sum(1 for p in printers if not snmp_ok(p))
    offline_names = ", ".join(p.get("name") for p in printers if not official_online(p)) or "Nenhum"
    snmp_names = ", ".join(p.get("name") for p in printers if not snmp_ok(p)) or "Nenhum"
    cards = "".join(printer_card(p) for p in printers)
    online_pct = int(round((online_count / total) * 100)) if total else 0
    offline_pct = int(round((offline_count / total) * 100)) if total else 0
    snmp_pct = int(round((snmp_down / total) * 100)) if total else 0

    return f"""
<div class="noc-printers">
  <section class="topline">
    {metric_card("Total Impressoras", total, "blue")}
    {metric_card("Online", online_count, "green")}
    {metric_card("Offline", offline_count, "red")}
    {metric_card("Sem SNMP", snmp_down, "yellow")}
    <div class="metric slate"><span>Última atualização</span><strong id="printerLastUpdate">--/--/---- --:--</strong></div>
    <div class="metric clock slate"><span>Relógio</span><strong id="printerClock">{datetime.now().strftime("%H:%M:%S")}</strong></div>
  </section>

  <section class="grid-printers">
    {cards}
  </section>

  <script>
    (function(){{
      function pad(n){{return String(n).padStart(2,'0');}}
      function tick(){{
        var d=new Date(), el=document.getElementById('printerClock');
        if(el) el.textContent=pad(d.getHours())+':'+pad(d.getMinutes())+':'+pad(d.getSeconds());
      }}
      function updateLastRefresh(){{
        var d=new Date(), el=document.getElementById('printerLastUpdate');
        if(el) el.textContent=pad(d.getDate())+'/'+pad(d.getMonth()+1)+'/'+d.getFullYear()+' '+pad(d.getHours())+':'+pad(d.getMinutes());
      }}
      tick(); updateLastRefresh(); setInterval(tick,1000); setInterval(updateLastRefresh,60000);
    }})();
  </script>

  <style>
    .noc-printers {{ width:100%; height:calc(100vh - 30px); max-height:calc(100vh - 30px); box-sizing:border-box; padding:clamp(6px,.6vh,14px); background:#f4f7fb; color:#172033; font-family:'Segoe UI',Arial,sans-serif; overflow:hidden; display:grid; grid-template-rows:clamp(72px,8vh,170px) minmax(0,1fr); gap:clamp(6px,.45vh,14px); align-content:start; }}
    .topline {{ display:grid; grid-template-columns:repeat(6,1fr); gap:clamp(7px,.45vw,16px); margin:0; min-height:0; }}
    .metric {{ min-height:0; border:1px solid #dbe4ef; background:#fff; border-radius:clamp(10px,.55vw,18px); display:flex; flex-direction:column; align-items:center; justify-content:center; box-shadow:0 6px 14px rgba(15,23,42,.08); border-top:clamp(6px,.35vw,12px) solid #64748b; }}
    .metric span {{ font-size:clamp(12px,.72vw,26px); text-transform:uppercase; letter-spacing:.02em; color:#526176; font-weight:900; text-align:center; }}
    .metric strong {{ margin-top:clamp(2px,.25vh,8px); font-size:clamp(36px,2.35vw,92px); line-height:1; color:#0f172a; }}
    .metric.clock strong {{ font-size:clamp(42px,2.7vw,108px); }}
    .metric.blue {{ border-top-color:#2f80ed; }}
    .metric.green {{ border-top-color:#22a85a; }}
    .metric.red {{ border-top-color:#ef4444; }}
    .metric.yellow {{ border-top-color:#f2c94c; }}
    .metric.slate {{ border-top-color:#475569; }}
    .metric.slate strong {{ font-size:clamp(26px,1.55vw,60px); }}
    .metric.clock strong {{ font-size:clamp(42px,2.7vw,108px); }}

    .grid-printers {{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); grid-template-rows:repeat(7,minmax(0,1fr)); gap:clamp(7px,.45vw,16px); min-height:0; overflow:hidden; }}
    .printer-card {{ min-height:0; height:100%; box-sizing:border-box; border-radius:clamp(9px,.5vw,18px); background:#fff; border:1px solid #d7e0ec; border-left:clamp(7px,.42vw,15px) solid #94a3b8; padding:clamp(6px,.5vh,14px) clamp(8px,.55vw,20px); overflow:hidden; box-shadow:0 5px 12px rgba(15,23,42,.08); display:grid; grid-template-rows:auto auto auto auto clamp(20px,1.45vh,36px); gap:clamp(2px,.18vh,6px); }}
    .printer-card.online {{ border-left-color:#22c55e; }}
    .printer-card.offline {{ border-left-color:#ef4444; background:#fff8f8; }}
    .printer-card.nosnmp {{ border-left-color:#facc15; background:#fffdf2; }}
    .printer-card.nodata {{ border-left-color:#94a3b8; background:#f8fafc; }}
    .line {{ min-width:0; overflow:hidden; }}
    .line-top {{ display:flex; align-items:flex-start; justify-content:space-between; gap:clamp(5px,.35vw,12px); }}
    .line-top strong {{ font-size:clamp(13px,.72vw,28px); line-height:1.05; color:#0f172a; font-weight:900; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }}
    .line-top span {{ flex:0 0 auto; border-radius:999px; padding:clamp(2px,.18vh,6px) clamp(7px,.42vw,15px); font-size:clamp(10px,.56vw,22px); font-weight:900; background:#dcfce7; color:#166534; }}
    .offline .line-top span {{ background:#fee2e2; color:#991b1b; }}
    .split {{ display:flex; align-items:center; justify-content:space-between; gap:clamp(8px,.45vw,16px); font-size:clamp(11px,.62vw,24px); line-height:1.05; color:#334155; }}
    .split em {{ font-style:normal; font-weight:800; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .split b {{ flex:0 0 auto; font-size:clamp(12px,.66vw,26px); color:#0f172a; }}
    .model,.serial {{ font-size:clamp(10px,.57vw,22px); line-height:1.05; color:#0f172a; white-space:nowrap; text-overflow:ellipsis; }}
    .serial {{ color:#475569; font-weight:700; }}
    .signals {{ display:grid; grid-template-columns:1fr 1fr 1.45fr; gap:clamp(4px,.25vw,9px); align-items:center; font-size:clamp(9px,.5vw,19px); font-weight:800; }}
    .signals div {{ min-width:0; display:flex; align-items:center; justify-content:space-between; gap:clamp(2px,.18vw,7px); background:#eef3f8; border-radius:clamp(5px,.35vw,10px); padding:clamp(2px,.18vh,6px) clamp(4px,.28vw,10px); color:#334155; white-space:nowrap; overflow:hidden; }}
    .mini {{ border-radius:999px; padding:clamp(1px,.12vh,4px) clamp(4px,.25vw,9px); font-size:clamp(7px,.38vw,15px); font-weight:900; }}
    .mini.ok {{ background:#bbf7d0; color:#166534; }}
    .mini.bad {{ background:#fecaca; color:#991b1b; }}
    .mini.warn {{ background:#fde68a; color:#7c4a03; }}
    .collected {{ display:none; }}

    .bottomline {{ display:none; }}
    .panel {{ min-height:118px; background:#fff; border:1px solid #dbe3ee; border-radius:9px; padding:10px; box-sizing:border-box; overflow:hidden; }}
    .panel h3 {{ margin:0 0 7px; font-size:13px; text-transform:uppercase; letter-spacing:.04em; color:#e5e7eb; }}
    .bar {{ position:relative; height:22px; margin:7px 0; background:#0d1524; border-radius:5px; overflow:hidden; }}
    .bar span {{ position:absolute; left:8px; top:5px; z-index:2; font-size:10px; font-weight:800; }}
    .bar em {{ position:absolute; right:8px; top:5px; z-index:2; font-size:10px; font-style:normal; font-weight:900; }}
    .bar b {{ display:block; height:100%; background:#22c55e; }}
    .bar.danger b {{ background:#ef4444; }}
    .bar.warn b {{ background:#facc15; }}
    .pie {{ width:72px; height:72px; border-radius:50%; margin:0 auto 8px; background:conic-gradient(#22c55e 0 calc(var(--online)*1%), #ef4444 calc(var(--online)*1%) calc((var(--online) + var(--offline))*1%), #facc15 0); box-shadow:inset 0 0 0 14px #111827; }}
    .legend {{ display:flex; justify-content:center; gap:8px; font-size:10px; }}
    .legend span:before {{ content:''; display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:4px; }}
    .legend .g:before {{ background:#22c55e; }} .legend .r:before {{ background:#ef4444; }} .legend .y:before {{ background:#facc15; }}
    .incident-panel p {{ margin:5px 0; font-size:11px; line-height:1.3; color:#cbd5e1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .table-panel table {{ width:100%; border-collapse:collapse; table-layout:fixed; font-size:10px; }}
    .table-panel th,.table-panel td {{ border-bottom:1px solid #243244; padding:3px 4px; text-align:left; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .table-panel th {{ color:#94a3b8; text-transform:uppercase; }}
    .status-dot {{ border-radius:999px; padding:1px 6px; font-size:8px; font-weight:900; }}
    .status-dot.online {{ background:#bbf7d0; color:#166534; }} .status-dot.offline {{ background:#fecaca; color:#991b1b; }} .status-dot.nosnmp {{ background:#fde68a; color:#7c4a03; }}
  </style>
</div>
"""


def write_mockups(html_content):
    MOCKUP_DIR.mkdir(parents=True, exist_ok=True)
    (MOCKUP_DIR / "printer-dashboard-grid-mockup.html").write_text(html_content, encoding="utf-8")
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
<rect width="1920" height="1080" fill="#0b1220"/>
<text x="40" y="62" fill="#e5e7eb" font-size="34" font-family="Segoe UI, Arial" font-weight="700">Monitoramento de Impressoras - Grid NOC</text>
<rect x="40" y="95" width="290" height="86" rx="8" fill="#2563eb"/><text x="70" y="130" fill="#cbd5e1" font-size="18" font-family="Arial" font-weight="700">TOTAL IMPRESSORAS</text><text x="158" y="168" fill="#fff" font-size="44" font-family="Arial" font-weight="700">41</text>
<rect x="350" y="95" width="290" height="86" rx="8" fill="#22a85a"/><text x="390" y="130" fill="#dcfce7" font-size="18" font-family="Arial" font-weight="700">ONLINE</text><text x="470" y="168" fill="#fff" font-size="44" font-family="Arial" font-weight="700">35</text>
<rect x="660" y="95" width="290" height="86" rx="8" fill="#ef4444"/><text x="700" y="130" fill="#fee2e2" font-size="18" font-family="Arial" font-weight="700">OFFLINE</text><text x="790" y="168" fill="#fff" font-size="44" font-family="Arial" font-weight="700">6</text>
<rect x="970" y="95" width="290" height="86" rx="8" fill="#facc15"/><text x="1010" y="130" fill="#3b2f00" font-size="18" font-family="Arial" font-weight="700">SEM SNMP</text><text x="1100" y="168" fill="#3b2f00" font-size="44" font-family="Arial" font-weight="700">7</text>
<g fill="#111827" stroke="#334155" stroke-width="1">
""" + "\n".join(
        f'<rect x="{40 + (i % 7) * 265}" y="{220 + (i // 7) * 128}" width="245" height="108" rx="8" stroke="#22c55e"/>' for i in range(41)
    ) + """
</g>
</svg>
"""
    (MOCKUP_DIR / "printer-dashboard-grid-mockup.svg").write_text(svg, encoding="utf-8")


def main():
    inventory = json.loads(INV.read_text())
    printers = sorted(inventory.get("printers", []), key=lambda p: p.get("name", "").lower())
    if len(printers) != 41:
        raise RuntimeError(f"Inventario deve conter exatamente 41 impressoras; atual={len(printers)}")
    print(f"Datasource Zabbix reutilizado: {DS_NAME} ({DS_UID})")
    layout_report = validate_tv_layout(len(printers))

    content = build_dashboard_html(printers)
    write_mockups(content)
    dashboard = {
        "annotations": {"list": [{"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": True, "hide": True, "name": "Annotations & Alerts", "type": "dashboard"}]},
        "editable": True,
        "graphTooltip": 0,
        "id": None,
        "panels": [text_panel(9100, content, 0, 0, 24, 36)],
        "links": [{"targetBlank": True, "title": "Modo TV", "url": "http://SEU_SERVIDOR_INTERNO"}],
        "refresh": "1m",
        "schemaVersion": 39,
        "style": "light",
        "tags": ["zabbix", "snmp", "printers", "noc", "grid"],
        "templating": {"list": []},
        "time": {"from": "now-7d", "to": "now"},
        "timezone": "browser",
        "title": "Monitoramento de Impressoras",
        "uid": "printer-monitoring",
        "version": 1,
    }
    OUT.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Dashboard gerado: {OUT}")
    print(f"Cards de impressoras: {len(printers)}")
    print("Validacao matematica TV:")
    for report in layout_report:
        print(f"  {report}")
    print(f"Mockups: {MOCKUP_DIR}")


if __name__ == "__main__":
    main()
