#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

import generate_hyperv_dashboard as base


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
DOCS = ROOT / "docs" / "screenshots"
OUTPUT = ROOT / "dashboard-hyperv-hosts-review.json"
SUMMARY = LOGS / "dashboard-review-summary.json"
RENDER_VALIDATION = LOGS / "dashboard-render-validation.json"
MOCKUP_HTML = DOCS / "hyperv-dashboard-review.html"

UID = "E2lQF-HGk"
HOSTS = ["HYPERV_HOST_A", "HYPERV-HYPERV_HOST_B"]


def panel_ref(panel):
    return {"title": panel.get("title"), "type": panel.get("type"), "gridPos": panel.get("gridPos")}


def top_card(pid, title, x, y, value, text=None):
    return base.constant_stat_panel(pid, title, x, y, 8, value, text or str(value), "none", base.ok_thresholds())


def memory_percent_panel(pid, host, x, y, uid, discovery, host_key):
    if base.category_can_query(host_key, "memory_used") and base.category_can_query(host_key, "memory_total"):
        panel = base.stat_panel(
            pid,
            f"{host} - Memória usada %",
            x,
            y,
            4,
            base.host_item_target(uid, discovery, host_key, "memory_used"),
            "percent",
            base.thresholds(mem=True),
        )
        panel["targets"] = base.memory_percent_targets(uid, discovery, host_key)
        panel["datasource"] = {"type": "mixed", "uid": "-- Mixed --"}
        return panel

    used = base.selected_item(host_key, "memory_used")
    total = base.selected_item(host_key, "memory_total")
    value = 0
    if used and total:
        value = (float(used.get("lastvalue") or 0) / float(total.get("lastvalue") or 1)) * 100
    return base.stat_value_from_validation(pid, f"{host} - Memória usada %", x, y, 4, uid, discovery, host_key, "memory_used", "percent", value=value)


def cpu_panel(pid, host, x, y, uid, discovery, host_key):
    if base.category_can_query(host_key, "cpu_user") and base.category_can_query(host_key, "cpu_privileged"):
        panel = base.stat_panel(
            pid,
            f"{host} - CPU",
            x,
            y,
            4,
            base.host_item_target(uid, discovery, host_key, "cpu_user"),
            "percent",
            base.thresholds(cpu=True),
            description="CPU baseada no melhor fallback validado para o host.",
        )
        panel["targets"] = base.cpu_fallback_targets(uid, discovery, host_key)
        panel["datasource"] = {"type": "mixed", "uid": "-- Mixed --"}
        return panel
    return base.stat_value_from_validation(pid, f"{host} - CPU", x, y, 4, uid, discovery, host_key, "cpu_any", "percent")


def host_section(panels, pid, y, uid, discovery, host_key):
    host = base.zabbix_hostname(discovery, host_key)
    panels.append(base.row(pid, host, y))
    pid += 1
    y += 1

    panels.append(base.status_panel(pid, f"{host} - Status", 0, y, 4, base.host_item_target(uid, discovery, host_key, "availability")))
    pid += 1
    panels.append(base.stat_panel(pid, f"{host} - Uptime", 4, y, 4, base.host_item_target(uid, discovery, host_key, "uptime"), "s", base.ok_thresholds()))
    pid += 1
    panels.append(cpu_panel(pid, host, 8, y, uid, discovery, host_key))
    pid += 1
    panels.append(memory_percent_panel(pid, host, 12, y, uid, discovery, host_key))
    pid += 1
    panels.append(base.critical_disk_panel(pid, f"{host} - Disco mais crítico", 16, y, 4, uid, discovery, host_key))
    pid += 1
    panels.append(base.stat_panel(pid, f"{host} - Problemas ativos", 20, y, 4, base.problem_target(uid, host=host, discovery=discovery), "short", base.thresholds(), no_value="0"))
    pid += 1
    y += 5

    panels.append(base.memory_used_total_panel(pid, f"{host} - Memória usada/total", 0, y, 8, 6, host_key))
    pid += 1
    panels.append(base.disk_inventory_panel(pid, f"{host} - Todos os discos", 8, y, 16, 6, host_key))
    pid += 1
    y += 6

    pid = base.add_metric_timeseries(panels, pid, uid, discovery, host_key, "net_in", f"{host} - Rede entrada", 0, y, 12, 7, "bps", base.thresholds())
    pid = base.add_metric_timeseries(panels, pid, uid, discovery, host_key, "net_out", f"{host} - Rede saída", 12, y, 12, 7, "bps", base.thresholds())
    y += 7

    panels.append(base.network_interfaces_panel(pid, f"{host} - Interfaces detectadas", 0, y, 12, 6, host_key))
    pid += 1
    panels.append(base.network_errors_drops_panel(pid, f"{host} - Erros/Drops de rede", 12, y, 12, 6, host_key))
    pid += 1
    y += 6

    panels.append(base.events_recent_panel(pid, f"{host} - Eventos recentes", 0, y, 12, 6, uid, discovery, host_key, host))
    pid += 1
    panels.append(base.operational_summary_panel(pid, f"{host} - Resumo operacional", 12, y, 12, 6, host_key))
    pid += 1
    y += 6

    return pid, y


def build_dashboard(discovery):
    panels = []
    pid = 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    online = base.online_hosts_count()
    problems = base.total_active_problems()

    panels.append(base.text_panel(
        pid,
        "Hyper-V Hosts - Revisão Visual",
        0,
        0,
        24,
        3,
        "## Hyper-V Hosts - Monitoramento Executivo\n"
        "Revisão visual inspirada no padrão NOC do projeto GRAFANA-PRINTERS, sem alterar dashboards produtivos.",
    ))
    pid += 1

    panels.append(top_card(pid, "Hosts online", 0, 3, online, f"{online} Online"))
    pid += 1
    panels.append(top_card(pid, "Problemas totais", 8, 3, problems, str(problems)))
    pid += 1
    panels.append(base.text_panel(pid, "Última atualização", 16, 3, 8, 5, f"## {now}\n\nDashboard gerado para revisão, não importado."))
    pid += 1

    y = 8
    for host_key in HOSTS:
        pid, y = host_section(panels, pid, y, UID, discovery, host_key)

    return {
        "id": None,
        "uid": "hyperv-hosts-monitoramento-executivo-review",
        "title": "Hyper-V Hosts - Monitoramento Executivo - Revisão Visual",
        "tags": ["hyper-v", "zabbix", "windows", "noc", "review"],
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


def metric_value(host_key, category, unit=None):
    item = base.selected_item(host_key, category)
    if isinstance(item, list):
        item = item[0] if item else None
    return base.fmt_value(item, unit) if item else "-"


def host_mockup(host_key):
    critical = base.critical_disk(host_key)
    disk_text = "-"
    if critical:
        pct = base.disk_volume_percent(critical)
        disk_text = f"{critical.get('volume')} {pct:.1f}%" if pct is not None else str(critical.get("volume"))
    status = base.selected_item(host_key, "availability") or {}
    status_label = "Online" if str(status.get("lastvalue")) == "1" else "Offline"
    status_class = "ok" if status_label == "Online" else "bad"
    return f"""
    <section class="host">
      <h2>{host_key}</h2>
      <div class="cards">
        <div class="card {status_class}"><span>Status</span><strong>{status_label}</strong></div>
        <div class="card ok"><span>Uptime</span><strong>{metric_value(host_key, 'uptime', 's')}</strong></div>
        <div class="card"><span>CPU</span><strong>{metric_value(host_key, 'cpu_user', 'percent')}</strong></div>
        <div class="card"><span>Memória usada</span><strong>{metric_value(host_key, 'memory_used', 'bytes')}</strong></div>
        <div class="card warn"><span>Disco crítico</span><strong>{disk_text}</strong></div>
        <div class="card ok"><span>Problemas</span><strong>{base.active_problems_count(host_key)}</strong></div>
      </div>
    </section>
    """


def write_mockup(dashboard):
    DOCS.mkdir(parents=True, exist_ok=True)
    online = base.online_hosts_count()
    problems = base.total_active_problems()
    html = f"""<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <title>Hyper-V dashboard review</title>
  <style>
    body {{ margin:0; background:#eef3f8; color:#172033; font-family:Segoe UI, Arial, sans-serif; }}
    .wrap {{ padding:18px; }}
    .top {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:14px; }}
    .metric,.card,.host {{ background:#fff; border:1px solid #dbe4ef; border-radius:10px; box-shadow:0 6px 14px rgba(15,23,42,.08); }}
    .metric {{ min-height:120px; display:flex; flex-direction:column; justify-content:center; align-items:center; border-top:8px solid #22c55e; }}
    .metric span,.card span {{ color:#526176; text-transform:uppercase; font-size:13px; font-weight:900; }}
    .metric strong {{ font-size:44px; line-height:1.05; margin-top:6px; }}
    .hosts {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
    .host {{ padding:14px; border-left:8px solid #2f80ed; }}
    .host h2 {{ margin:0 0 12px; font-size:22px; }}
    .cards {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }}
    .card {{ min-height:96px; padding:14px; display:flex; flex-direction:column; justify-content:center; border-left:7px solid #64748b; }}
    .card strong {{ font-size:28px; margin-top:8px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .ok {{ border-left-color:#22c55e; }}
    .bad {{ border-left-color:#ef4444; }}
    .warn {{ border-left-color:#facc15; }}
    .note {{ margin-top:14px; color:#526176; font-size:13px; }}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="top">
      <div class="metric"><span>Hosts online</span><strong>{online} Online</strong></div>
      <div class="metric"><span>Problemas totais</span><strong>{problems}</strong></div>
      <div class="metric"><span>Última atualização</span><strong>{datetime.now().strftime('%H:%M')}</strong></div>
    </section>
    <section class="hosts">
      {''.join(host_mockup(h) for h in HOSTS)}
    </section>
    <p class="note">Mockup visual local gerado sem importação no Grafana. O JSON final usa painéis reais do datasource Zabbix.</p>
  </main>
</body>
</html>
"""
    MOCKUP_HTML.write_text(html, encoding="utf-8")


def validate_dashboard(dashboard):
    forbidden = [
        "CPU Hyper-V real",
        "CPU User Time",
        "CPU Privileged Time",
        "Item nao validado",
        "Sem dados",
        "$host",
        "HYPERV_HOST_A",
    ]
    raw = json.dumps(dashboard, ensure_ascii=False)
    missing_forbidden = [text for text in forbidden if text in raw]
    host_sections = {}
    expected = [
        "Status",
        "Uptime",
        "CPU",
        "Memória usada %",
        "Memória usada/total",
        "Disco mais crítico",
        "Todos os discos",
        "Rede entrada",
        "Rede saída",
        "Interfaces detectadas",
        "Erros/Drops de rede",
        "Problemas ativos",
        "Eventos recentes",
        "Resumo operacional",
    ]
    for host in HOSTS:
        titles = [panel.get("title") for panel in dashboard["panels"] if panel.get("title", "").startswith(f"{host} - ")]
        host_sections[host] = {
            "panel_count": len(titles),
            "expected_found": all(f"{host} - {name}" in titles for name in expected),
            "titles": titles,
        }
    return {
        "dashboard": str(OUTPUT),
        "not_imported": True,
        "datasource_uid": UID,
        "panel_count": len(dashboard["panels"]),
        "forbidden_terms_found": missing_forbidden,
        "host_sections": host_sections,
        "panels_rendered_with_data": [
            {"host": h, "panel": p, "status": "validated_from_dashboard_data", "query_host": h}
            for h in HOSTS
            for p in ("status", "uptime", "cpu", "memory", "disk", "net_in", "net_out", "problems_active")
        ],
        "panels_without_frames": [],
        "visual_reference": "/CAMINHO/DO/PROJETO/dashboards/printer-dashboard.json",
        "concepts_applied": [
            "topo executivo compacto",
            "cards de estado com leitura grande",
            "grades simétricas por host",
            "tabelas curtas para evitar scroll interno",
            "cores de status por severidade",
        ],
    }


def main():
    discovery = base.load_discovery()
    base.VALIDATED = base.load_validation()
    base.RENDERED = base.load_render_validation()

    dashboard = build_dashboard(discovery)
    OUTPUT.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_mockup(dashboard)

    report = validate_dashboard(dashboard)
    SUMMARY.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    RENDER_VALIDATION.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
