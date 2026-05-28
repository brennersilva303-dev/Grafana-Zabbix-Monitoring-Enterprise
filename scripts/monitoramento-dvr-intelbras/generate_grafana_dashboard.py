#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboards" / "camera-dvr-dashboard.json"


def load_env(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env(ROOT / ".env")
DS_UID = os.getenv("GRAFANA_DATASOURCE_UID", "E2lQF-HGk")
DS_TYPE = os.getenv("GRAFANA_DATASOURCE_TYPE", "alexanderzobnin-zabbix-datasource")
ZABBIX_URL = os.getenv("ZABBIX_URL", "http://SEU_SERVIDOR_INTERNO").rstrip("/")
ZABBIX_USER = SEU_USUARIO
ZABBIX_PASSWORD = SUA_SENHA

EQUIPMENT = [
    {"kind": "dvr", "group": "TAGUATINGA", "display": "TAGUATINGA", "host": "TAGUATINGA", "ip": "SEU_IP_PRIVADO", "channels": 16},
    {"kind": "dvr", "group": "TAGUATINGA", "display": "TAGUATINGA 2", "host": "TAGUATINGA 2", "ip": "SEU_IP_PRIVADO", "channels": 16},
    {"kind": "dvr", "group": "SIA", "display": "SIA 01", "host": "SIA 01", "ip": "SEU_IP_PRIVADO", "channels": 24},
    {"kind": "dvr", "group": "SIA", "display": "SIA 02", "host": "SIA 02", "ip": "SEU_IP_PRIVADO", "channels": 24},
    {"kind": "dvr", "group": "SIA", "display": "SIA", "host": "SIA", "ip": "SEU_IP_PRIVADO", "channels": 16},
    {"kind": "ip_group", "group": "SIA-IP", "display": "SIA-IP", "host": "SIA-IP", "cameras": [
        {"label": "IP-01", "host": "SIA-IP-01", "ip": "SEU_IP_PRIVADO"},
        {"label": "IP-02", "host": "SIA-IP-02", "ip": "SEU_IP_PRIVADO"},
        {"label": "IP-03", "host": "SIA-IP-03", "ip": "SEU_IP_PRIVADO"},
        {"label": "IP-04", "host": "SIA-IP-04", "ip": "SEU_IP_PRIVADO"},
        {"label": "IP-05", "host": "SIA-IP-05", "ip": "SEU_IP_PRIVADO"},
    ]},
    {"kind": "dvr", "group": "GAMA", "display": "GAMA 01", "host": "GAMA", "ip": "SEU_IP_PRIVADO", "channels": 16},
    {"kind": "dvr", "group": "GAMA", "display": "GAMA 02", "host": "GAMA 02", "ip": "SEU_IP_PRIVADO", "channels": 16},
    {"kind": "dvr", "group": "VALPARAISO", "display": "VALPARAISO 01", "host": "VALPARAISO 01", "ip": "SEU_IP_PRIVADO", "channels": 16},
    {"kind": "dvr", "group": "VALPARAISO", "display": "VALPARAISO 02", "host": "VALPARAISO 02", "ip": "SEU_IP_PRIVADO", "channels": 16},
    {"kind": "dvr", "group": "RECANTO", "display": "RECANTO", "host": "RECANTO", "ip": "SEU_IP_PRIVADO", "channels": 32},
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
        try:
            self.auth = self.call("user.login", {"username": ZABBIX_USER, "password": ZABBIX_PASSWORD}, auth=False)
        except RuntimeError:
            self.auth = self.call("user.login", {"user": ZABBIX_USER, "password": ZABBIX_PASSWORD}, auth=False)


def data_hosts():
    hosts = []
    for item in EQUIPMENT:
        if item["kind"] == "ip_group":
            hosts.extend(camera["host"] for camera in item["cameras"])
        else:
            hosts.append(item["host"])
    return hosts


def fetch_initial_values():
    keys = ["dvr.online", "dvr.hdd.status", "icmpping"] + [f"dvr.channel.status[{channel}]" for channel in range(1, 33)]
    api = Zabbix()
    api.login()
    hosts = api.call(
        "host.get",
        {
            "output": ["hostid", "host", "name"],
            "selectInterfaces": ["ip", "dns"],
            "selectItems": ["key_", "lastvalue", "lastclock"],
        },
    )
    by_ip = {}
    by_name = {}
    for host in hosts:
        values = {
            item["key_"]: {"value": str(item.get("lastvalue", "")), "clock": int(item.get("lastclock") or 0) * 1000}
            for item in host.get("items", [])
            if item.get("key_") in keys
        }
        by_name[host.get("name") or host.get("host")] = values
        by_name[host.get("host")] = values
        for interface in host.get("interfaces", []):
            ip = interface.get("ip") or interface.get("dns")
            if ip:
                by_ip[ip] = values

    result = {}
    for item in EQUIPMENT:
        if item["kind"] == "ip_group":
            for camera in item["cameras"]:
                values = by_ip.get(camera["ip"]) or by_name.get(camera["host"]) or {}
                result[camera["host"]] = {key: values.get(key, "0") for key in keys}
        else:
            values = by_ip.get(item["ip"]) or by_name.get(item["host"]) or {}
            result[item["host"]] = {key: values.get(key, "0") for key in keys}
    return result


def equipment_rows():
    rows = []
    previous_group = None
    for item in EQUIPMENT:
        group_class = " group-start" if item["group"] != previous_group else ""
        previous_group = item["group"]
        if item["kind"] == "ip_group":
            cameras = "".join(
                f"<div class='cam cell ip-cam' data-host='{camera['host']}' data-key='icmpping'><span>{camera['label']}</span><b></b></div>"
                for camera in item["cameras"]
            )
            dvr = "<div class='dvr-dot empty-dot'><span></span></div>"
            hd = "<div class='hd cell empty'><span>HD</span><b></b></div>"
        else:
            cameras = "".join(
                f"<div class='cam cell' data-host='{item['host']}' data-key='dvr.channel.status[{channel}]'><span>C{channel}</span><b></b></div>"
                for channel in range(1, item["channels"] + 1)
            )
            dvr = f"<div class='dvr-dot' data-host='{item['host']}' data-key='dvr.online'><span></span></div>"
            hd = f"<div class='hd cell' data-host='{item['host']}' data-key='dvr.hdd.status'><span>HD</span><b></b></div>"
        rows.append(
            f"""
            <div class="equip-row{group_class}" data-display="{item['display']}" data-group="{item['group']}">
              <div class="equip-name"><span class="segment">{item['group']}</span><strong>{item['display']}</strong></div>
              {dvr}
              <div class="camera-grid">{cameras}</div>
              {hd}
            </div>
            """
        )
    return "\n".join(rows)


def build_html(values):
    values_json = json.dumps(values, ensure_ascii=False)
    hosts_json = json.dumps(data_hosts(), ensure_ascii=False)
    equipment_json = json.dumps(EQUIPMENT, ensure_ascii=False)
    return f"""
<div class="cftv-noc" id="cameraDvrNoc">
  <section class="summary">
    <div class="summary-card blue"><span class="icon">▣</span><div><b>TOTAL EQUIPAMENTOS</b><strong data-total>0</strong></div></div>
    <div class="summary-card green"><span class="icon">✓</span><div><b>ONLINE</b><strong data-online>0</strong></div></div>
    <div class="summary-card red"><span class="icon">×</span><div><b>OFFLINE</b><strong data-offline>0</strong></div></div>
    <div class="summary-card cyan"><span class="icon">▦</span><div><b>CÂMERAS OK</b><strong data-cams>0</strong></div></div>
    <div class="summary-card slate"><span class="icon">◷</span><div><b>ATUALIZAÇÃO</b><strong data-updated>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</strong></div></div>
  </section>

  <section class="table">
    <div class="table-head">
      <div>UNIDADE</div><div>DVR</div><div>CÂMERAS</div><div>HD</div>
    </div>
    <div class="channel-head">
      <div></div><div></div>
      <div class="channel-labels">{''.join(f'<span>C{channel}</span>' for channel in range(1, 17))}</div>
      <div></div>
    </div>
    {equipment_rows()}
  </section>

  <section class="legend">
    <span><i class="ok"></i> ONLINE</span>
    <span><i class="bad"></i> OFFLINE</span>
    <span><i class="hdok"></i> HD OK</span>
    <em>Atualização automática: 1 min</em>
  </section>

  <script>
    (function(){{
      var root = document.getElementById('cameraDvrNoc');
      if (!root) return;
      var dsUid = {json.dumps(DS_UID)};
      var dsType = {json.dumps(DS_TYPE)};
      var values = {values_json};
      var hosts = {hosts_json};
      var equipment = {equipment_json};
      var itemRegex = '/^(icmpping|dvr\\\\.(online|hdd\\\\.status|channel\\\\.status\\\\[[0-9]+\\\\]))$/';

      function cssEscape(value) {{
        if (window.CSS && window.CSS.escape) return window.CSS.escape(value);
        return String(value).replace(/"/g, '\\\\"');
      }}

      function lastValue(frame) {{
        var values = frame && frame.data && frame.data.values && frame.data.values[1] || [];
        for (var i = values.length - 1; i >= 0; i--) {{
          if (values[i] !== null && values[i] !== undefined) return String(values[i]);
        }}
        return '0';
      }}

      function lastPoint(frame) {{
        var times = frame && frame.data && frame.data.values && frame.data.values[0] || [];
        var vals = frame && frame.data && frame.data.values && frame.data.values[1] || [];
        for (var i = vals.length - 1; i >= 0; i--) {{
          if (vals[i] !== null && vals[i] !== undefined) {{
            return {{ value: String(vals[i]), clock: Number(times[i]) || 0 }};
          }}
        }}
        return {{ value: '0', clock: 0 }};
      }}

      function freshValue(host, key) {{
        var item = (values[host] || {{}})[key];
        if (!item || !item.clock) return '0';
        return Date.now() - item.clock <= 5 * 60 * 1000 ? item.value : '0';
      }}

      function setClass(el, value, hd) {{
        var ok = String(value) === '1';
        el.classList.toggle('ok', ok);
        el.classList.toggle('bad', !ok);
        el.classList.toggle('hd-ok', Boolean(hd && ok));
      }}

      function render() {{
        var total = 0, online = 0, cameras = 0;
        equipment.forEach(function(item) {{
          if (item.kind === 'ip_group') {{
            item.cameras.forEach(function(camera) {{
              total++;
              var ping = freshValue(camera.host, 'icmpping');
              if (ping === '1') {{ online++; cameras++; }}
              root.querySelectorAll('[data-host="' + cssEscape(camera.host) + '"][data-key="icmpping"]').forEach(function(el) {{ setClass(el, ping, false); }});
            }});
            return;
          }}
          total++;
          var hostValues = values[item.host] || {{}};
          var dvr = freshValue(item.host, 'dvr.online');
          if (dvr === '1') online++;
          root.querySelectorAll('[data-host="' + cssEscape(item.host) + '"][data-key="dvr.online"]').forEach(function(el) {{ setClass(el, dvr, false); }});
          root.querySelectorAll('[data-host="' + cssEscape(item.host) + '"][data-key="dvr.hdd.status"]').forEach(function(el) {{ setClass(el, freshValue(item.host, 'dvr.hdd.status'), true); }});
          for (var channel = 1; channel <= item.channels; channel++) {{
            var key = 'dvr.channel.status[' + channel + ']';
            var value = freshValue(item.host, key);
            if (value === '1') cameras++;
            root.querySelectorAll('[data-host="' + cssEscape(item.host) + '"][data-key="' + cssEscape(key) + '"]').forEach(function(el) {{ setClass(el, value, false); }});
          }}
        }});
        root.querySelector('[data-total]').textContent = String(total);
        root.querySelector('[data-online]').textContent = String(online);
        root.querySelector('[data-offline]').textContent = String(total - online);
        root.querySelector('[data-cams]').textContent = String(cameras);
        var d = new Date();
        root.querySelector('[data-updated]').textContent =
          String(d.getDate()).padStart(2, '0') + '/' + String(d.getMonth() + 1).padStart(2, '0') + '/' + d.getFullYear() + ' ' +
          String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0') + ':' + String(d.getSeconds()).padStart(2, '0');
      }}

      function refresh() {{
        fetch('/api/datasources/uid/' + encodeURIComponent(dsUid), {{ credentials: 'same-origin' }})
          .then(function(response) {{ return response.json(); }})
          .then(function(ds) {{
            var now = Date.now();
            return fetch('/api/ds/query', {{
              method: 'POST',
              credentials: 'same-origin',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify({{
                queries: [{{
                  refId: 'A',
                  datasource: {{ type: dsType, uid: dsUid }},
                  datasourceId: ds.id,
                  application: {{ filter: '' }},
                  group: {{ filter: 'DVRs Intelbras' }},
                  host: {{ filter: '/.*/' }},
                  item: {{ filter: itemRegex }},
                  trigger: {{ filter: '' }},
                  functions: [],
                  options: {{ disableDataAlignment: false, showDisabledItems: false, skipEmptyValues: false, useTrends: 'default', useZabbixValueMapping: false }},
                  queryType: 0,
                  resultFormat: 'time_series',
                  table: {{ skipEmptyValues: false }},
                  intervalMs: 60000,
                  maxDataPoints: 500
                }}],
                from: String(now - 6 * 60 * 60 * 1000),
                to: String(now)
              }})
            }});
          }})
          .then(function(response) {{ return response.json(); }})
          .then(function(result) {{
            var frames = (((result || {{}}).results || {{}}).A || {{}}).frames || [];
            frames.forEach(function(frame) {{
              var field = frame.schema && frame.schema.fields && frame.schema.fields[1];
              var labels = field && field.labels || {{}};
              var host = labels.host;
              var key = labels.item_key || labels.item;
              if (!host || !key) return;
              values[host] = values[host] || {{}};
              values[host][key] = lastPoint(frame);
            }});
            render();
          }})
          .catch(render);
      }}

      render();
      refresh();
      setInterval(refresh, 60000);
    }})();
  </script>

  <style>
    * {{ scrollbar-width:none!important; }}
    *::-webkit-scrollbar {{ width:0!important; height:0!important; display:none!important; }}
    html, body, #reactRoot, .grafana-app, .main-view, #pageContent, [class*="page-"], [class*="canvas-content"] {{ width:100vw!important; height:100vh!important; min-height:100vh!important; max-height:100vh!important; overflow:hidden!important; contain:none!important; }}
    .scrollbar-view {{ width:100vw!important; height:100vh!important; min-height:100vh!important; max-height:100vh!important; overflow:hidden!important; contain:none!important; }}
    .react-grid-layout, .react-grid-item, .react-grid-layout--enable-move-animations {{ height:100vh!important; min-height:100vh!important; max-height:100vh!important; overflow:visible!important; contain:none!important; }}
    .react-grid-item {{ transform:none!important; top:0!important; left:0!important; width:100%!important; }}
    [class*="panel-content"], [class*="panel-container"], [class*="markdown-html"] {{ height:100vh!important; min-height:100vh!important; max-height:100vh!important; overflow:visible!important; contain:none!important; }}
    .cftv-noc {{ width:100%; height:calc(100vh - 30px); max-height:calc(100vh - 30px); min-height:0; box-sizing:border-box; padding:18px 22px; background:#f8fafc; color:#0f172a; font-family:'Segoe UI',Arial,sans-serif; overflow:hidden; }}
    .summary {{ display:grid; grid-template-columns:1.15fr 1.05fr 1.02fr 1fr .93fr; gap:18px; margin-bottom:14px; }}
    .summary-card {{ min-height:92px; border-radius:14px; display:grid; grid-template-columns:68px 1fr; align-items:center; gap:12px; padding:0 18px; border:1px solid #bfdbfe; background:linear-gradient(135deg,#ffffff,#eff6ff); box-shadow:0 18px 28px rgba(15,23,42,.12), inset 0 1px 0 rgba(255,255,255,.9); }}
    .summary-card.green {{ border-color:#16a34a; background:linear-gradient(135deg,#f0fdf4,#dcfce7); }}
    .summary-card.red {{ border-color:#dc2626; background:linear-gradient(135deg,#fff1f2,#fee2e2); }}
    .summary-card.cyan {{ border-color:#0891b2; background:linear-gradient(135deg,#ecfeff,#cffafe); }}
    .summary-card.slate {{ border-color:#cbd5e1; }}
    .summary-card .icon {{ width:54px; height:54px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:34px; font-weight:900; background:#e0f2fe; color:#1d4ed8; box-shadow:0 0 18px rgba(96,165,250,.22), inset 0 0 16px rgba(255,255,255,.8); }}
    .summary-card.green .icon {{ color:#dcfce7; background:#16a34a; box-shadow:0 0 18px rgba(34,197,94,.4); }}
    .summary-card.red .icon {{ color:#fff; background:#dc2626; box-shadow:0 0 18px rgba(239,68,68,.38); }}
    .summary-card.cyan .icon {{ color:#ccfbf1; background:#0f766e; box-shadow:0 0 18px rgba(45,212,191,.3); }}
    .summary-card b {{ display:block; font-size:19px; line-height:1; color:#0f172a; text-shadow:none; }}
    .summary-card strong {{ display:block; margin-top:6px; font-size:50px; line-height:.9; color:#0f172a; text-shadow:none; }}
    .summary-card.green strong {{ color:#16a34a; }} .summary-card.red strong {{ color:#dc2626; }} .summary-card.cyan strong {{ color:#16a34a; }} .summary-card.slate strong {{ font-size:24px; }}

    .table {{ border-radius:14px; overflow:hidden; border:1px solid #cbd5e1; box-shadow:0 20px 42px rgba(15,23,42,.14); }}
    .table-head,.channel-head,.equip-row {{ display:grid; grid-template-columns:270px 100px minmax(0,1fr) 86px; }}
    .table-head {{ height:48px; align-items:center; background:linear-gradient(180deg,#e2e8f0,#cbd5e1); color:#0f172a; font-size:20px; font-weight:900; text-align:center; }}
    .table-head div:first-child {{ text-align:left; padding-left:54px; }}
    .channel-head {{ height:30px; align-items:end; background:#f1f5f9; border-top:1px solid rgba(15,23,42,.08); }}
    .channel-labels {{ display:grid; grid-template-columns:repeat(16,1fr); gap:8px; padding:0 22px 5px; color:#0f172a; font-size:20px; font-weight:900; text-align:center; text-shadow:none; }}
    .equip-row {{ min-height:50px; align-items:center; background:linear-gradient(180deg,#ffffff,#f8fafc); border-top:1px solid #e2e8f0; }}
    .equip-row.group-start {{ box-shadow:inset 0 2px 0 rgba(59,130,246,.25); }}
    .equip-name {{ height:100%; display:flex; flex-direction:column; justify-content:center; padding-left:28px; border-right:1px solid #e2e8f0; }}
    .equip-name .segment {{ color:#0284c7; font-size:10px; font-weight:900; letter-spacing:.12em; text-transform:uppercase; opacity:.82; }}
    .equip-name strong {{ margin-top:2px; font-size:25px; line-height:1; font-weight:900; color:#0f172a; text-shadow:none; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .dvr-dot {{ height:100%; display:flex; align-items:center; justify-content:center; border-right:1px solid #e2e8f0; background:#f8fafc; }}
    .dvr-dot span {{ width:32px; height:32px; border-radius:50%; background:#ef4444; box-shadow:0 0 22px rgba(239,68,68,.9), inset 0 0 10px rgba(255,255,255,.35); }}
    .dvr-dot.ok span {{ background:#86efac; box-shadow:0 0 22px rgba(34,197,94,.95), inset 0 0 10px rgba(255,255,255,.45); }}
    .dvr-dot.empty-dot span {{ display:none; }}
    .camera-grid {{ display:grid; grid-template-columns:repeat(16,1fr); gap:6px 8px; padding:6px 22px; }}
    .cell {{ height:38px; border-radius:8px; display:flex; align-items:center; justify-content:center; position:relative; overflow:hidden; background:linear-gradient(180deg,#dc2626,#b91c1c); box-shadow:0 0 12px rgba(239,68,68,.42), inset 0 1px 0 rgba(255,255,255,.22), inset 0 -4px 0 rgba(0,0,0,.17); }}
    .cell.ok {{ background:linear-gradient(180deg,#5bdd49,#16a31f); box-shadow:0 0 12px rgba(34,197,94,.38), inset 0 1px 0 rgba(255,255,255,.25), inset 0 -4px 0 rgba(0,0,0,.18); }}
    .cell.hd-ok {{ background:linear-gradient(180deg,#38bdf8,#2563eb); box-shadow:0 0 14px rgba(59,130,246,.58), inset 0 1px 0 rgba(255,255,255,.28), inset 0 -4px 0 rgba(0,0,0,.18); }}
    .cell.empty {{ background:transparent; box-shadow:none; }}
    .cell b::before {{ content:'×'; color:#fff; font-size:31px; line-height:1; font-weight:900; text-shadow:0 2px 4px rgba(0,0,0,.55); }}
    .cell.ok b::before,.cell.hd-ok b::before {{ content:'✓'; }}
    .cell.empty b::before {{ content:''; }}
    .cell span {{ position:absolute; top:-999px; left:-999px; }}
    .cell.ip-cam {{ flex-direction:column; gap:1px; }}
    .cell.ip-cam span {{ position:static; color:#fff; font-size:10px; font-weight:900; line-height:1; text-shadow:0 1px 2px rgba(0,0,0,.55); }}
    .cell.ip-cam b::before {{ font-size:20px; }}
    .hd {{ margin:6px 14px 6px 0; height:38px; }}
    .hd b::before {{ font-size:25px; }}
    .legend {{ height:66px; display:flex; align-items:center; justify-content:center; gap:34px; color:#0f172a; font-size:19px; font-weight:900; }}
    .legend i {{ display:inline-block; width:24px; height:24px; border-radius:7px; margin-right:9px; vertical-align:middle; box-shadow:0 0 12px rgba(15,23,42,.16); }}
    .legend .ok {{ background:#22c55e; }} .legend .bad {{ background:#dc2626; }} .legend .hdok {{ background:#2563eb; }}
    .legend em {{ color:#475569; font-style:normal; font-weight:700; border-left:1px solid #94a3b8; padding-left:28px; }}
    @media (max-height:980px) {{
      .cftv-noc {{ transform:scale(.92); transform-origin:top left; width:108.6957%; height:calc((100vh - 30px) / .92); max-height:calc((100vh - 30px) / .92); }}
    }}
  </style>
</div>
"""


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


def main():
    content = build_html(fetch_initial_values())
    dashboard = {
        "annotations": {"list": [{"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": True, "hide": True, "name": "Annotations & Alerts", "type": "dashboard"}]},
        "editable": True,
        "graphTooltip": 0,
        "id": None,
        "panels": [text_panel(9100, content, 0, 0, 24, 36)],
        "refresh": "1m",
        "schemaVersion": 39,
        "style": "light",
        "tags": ["zabbix", "snmp", "camera", "dvr", "intelbras", "proxy", "noc"],
        "templating": {"list": []},
        "time": {"from": "now-6h", "to": "now"},
        "timezone": "browser",
        "title": "Monitoramento DVR Intelbras",
        "uid": "camera-dvr-monitoring",
        "version": 1,
        "description": "Painel NOC CFTV claro: DVR -> Zabbix Proxy -> Zabbix Server -> Grafana.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Dashboard gerado: {OUT}")


if __name__ == "__main__":
    main()
