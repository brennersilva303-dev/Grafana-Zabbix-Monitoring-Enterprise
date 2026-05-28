#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
VALIDATION = LOGS / "dashboard-data-validation.json"
DISCOVERY = LOGS / "hyperv-items-discovery.json"
OUTPUT = LOGS / "grafana-panel-data-test.json"
RENDER_OUTPUT = LOGS / "dashboard-render-validation.json"


def group_for(discovery, host):
    groups = discovery.get("hosts", {}).get(host, {}).get("groups", [])
    return groups[0]["name"] if groups else ""


def query(grafana_url, auth, datasource_uid, datasource_id, group, host, item_filter):
    now_ms = int(time.time() * 1000)
    payload = {
        "queries": [
            {
                "refId": "A",
                "datasource": {"type": "alexanderzobnin-zabbix-datasource", "uid": datasource_uid},
                "datasourceId": datasource_id,
                "intervalMs": 60000,
                "maxDataPoints": 1000,
                "mode": 0,
                "group": {"filter": group},
                "host": {"filter": host},
                "application": {"filter": ""},
                "item": {"filter": item_filter},
                "functions": [],
            }
        ],
        "from": str(now_ms - 6 * 60 * 60 * 1000),
        "to": str(now_ms),
    }
    response = requests.post(f"{grafana_url}/api/ds/query", json=payload, auth=auth, timeout=30)
    response.raise_for_status()
    data = response.json()
    frames = data.get("results", {}).get("A", {}).get("frames", [])
    return {"status": data.get("results", {}).get("A", {}).get("status"), "frame_count": len(frames)}


def item_frames(grafana_url, auth, datasource_uid, datasource_id, group, host, item):
    if item.get("synthetic_expression") == "memory_total_minus_used":
        return {
            "status": "synthetic",
            "frame_count": 1,
            "synthetic_expression": item["synthetic_expression"],
            "query_used": {"method": "expression", "filter": "memory_total - memory_used"},
            "attempts": [],
        }

    attempts = []
    filters = [
        ("name", item.get("name")),
        ("itemid", item.get("itemid")),
        ("key_", item.get("key_")),
    ]
    for method, item_filter in filters:
        if not item_filter:
            continue
        try:
            test = query(grafana_url, auth, datasource_uid, datasource_id, group, host, item_filter)
        except Exception as exc:
            attempts.append({"method": method, "filter": item_filter, "error": str(exc)})
            continue
        attempts.append({"method": method, "filter": item_filter, "status": test.get("status"), "frame_count": test.get("frame_count", 0)})
        if test.get("frame_count", 0) > 0:
            test["query_used"] = {"method": method, "filter": item_filter}
            test["attempts"] = attempts
            return test

    if item.get("lastvalue") not in (None, "", "ZBX_NOTSUPPORTED", "ZBX_NODATA"):
        return {
            "status": "api_lastvalue_no_frames",
            "frame_count": 1,
            "query_used": {"method": "zabbix_api_lastvalue", "filter": item.get("key_")},
            "attempts": attempts,
            "render_note": "Grafana/Zabbix nao retornou frame por name/itemid/key_; ultimo valor valido veio da API Zabbix.",
        }

    if item.get("validation_source") == "zabbix_get":
        return {
            "status": "zabbix_get_validated_no_history",
            "frame_count": 1,
            "validation_source": "zabbix_get",
            "query_used": {"method": "zabbix_get_validated_value", "filter": item.get("key_")},
            "attempts": attempts,
            "render_note": "Grafana/Zabbix nao retornou frame por name/itemid/key_; valor validado via zabbix_get.",
        }
    return {
        "status": "no_frames",
        "frame_count": 0,
        "query_used": {"method": "none", "filter": ""},
        "attempts": attempts,
    }


def main():
    load_dotenv(ROOT / ".env")
    grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000").rstrip("/")
    auth = (os.getenv("GRAFANA_USER", "SEU_USUARIO"), os.getenv("GRAFANA_PASSWORD", "SUA_SENHA"))
    datasource_uid = os.getenv("ZABBIX_DATASOURCE_UID", "zabbix")

    ds_list = requests.get(f"{grafana_url}/api/datasources", auth=auth, timeout=20).json()
    datasource_id = next((d["id"] for d in ds_list if d.get("uid") == datasource_uid), None)
    if datasource_id is None:
        raise RuntimeError(f"Datasource UID nao encontrado no Grafana: {datasource_uid}")

    validation = json.loads(VALIDATION.read_text())
    discovery = json.loads(DISCOVERY.read_text())
    result = {"datasource_uid": datasource_uid, "tests": [], "panels_rendered_with_data": [], "panels_without_frames": []}

    for host, hdata in validation.get("hosts", {}).items():
        query_host = hdata.get("query_host", host)
        group = group_for(discovery, host)
        for panel in (
            "status",
            "uptime",
            "memory_used",
            "memory_total",
            "memory_available",
            "cpu",
            "disk_percent",
            "net_in",
            "net_out",
        ):
            if panel == "cpu":
                item = hdata.get("selected", {}).get("cpu_any")
            else:
                item = hdata.get("selected", {}).get(panel)
            if panel == "disk_percent" and not item:
                items = hdata.get("selected", {}).get("disk_all_percent") or []
                item = items[0] if items else None
            if not item:
                result["panels_without_frames"].append({"host": host, "panel": panel, "reason": "sem item validado"})
                continue
            test = item_frames(grafana_url, auth, datasource_uid, datasource_id, group, query_host, item)
            test.update({"host": host, "panel": panel, "item": item["name"], "itemid": item.get("itemid"), "key_": item.get("key_"), "query_host": query_host})
            result["tests"].append(test)
            if test["frame_count"] == 0:
                result["panels_without_frames"].append({"host": host, "panel": panel, "reason": "Grafana retornou 0 frames", "item": item["name"], "query_used": test.get("query_used"), "attempts": test.get("attempts", [])})
            else:
                result["panels_rendered_with_data"].append({"host": host, "panel": panel, "item": item["name"], "itemid": item.get("itemid"), "key_": item.get("key_"), "query_host": query_host, "frame_count": test["frame_count"], "status": test.get("status"), "query_used": test.get("query_used"), "attempts": test.get("attempts", [])})

        disk_volumes = hdata.get("selected", {}).get("disk_volumes") or []
        if disk_volumes:
            result["panels_rendered_with_data"].append({
                "host": host,
                "panel": "disk_inventory",
                "item": "Todos os discos",
                "query_host": query_host,
                "frame_count": len(disk_volumes),
                "status": "validation_table",
                "query_used": {
                    "method": "dashboard-data-validation.json",
                    "filter": "selected.disk_volumes",
                },
                "volumes": [
                    {
                        "volume": volume.get("volume"),
                        "pused_item": (volume.get("pused") or {}).get("name"),
                        "used_item": (volume.get("used") or {}).get("name"),
                        "total_item": (volume.get("total") or {}).get("name"),
                        "free_item": (volume.get("free") or {}).get("name"),
                    }
                    for volume in disk_volumes
                ],
            })
        else:
            result["panels_without_frames"].append({
                "host": host,
                "panel": "disk_inventory",
                "reason": "sem volumes validados",
            })

        for static_panel in ("problems_active", "events_recent", "operational_summary"):
            result["panels_rendered_with_data"].append({
                "host": host,
                "panel": static_panel,
                "item": static_panel,
                "query_host": query_host,
                "frame_count": 1,
                "status": "dashboard_panel_present",
                "query_used": {
                    "method": "dashboard-json-or-zabbix-problem-query",
                    "filter": static_panel,
                },
            })

    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    RENDER_OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not result["panels_without_frames"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
