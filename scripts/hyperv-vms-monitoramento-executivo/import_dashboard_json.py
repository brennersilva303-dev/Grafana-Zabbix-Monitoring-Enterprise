#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

import requests


def main():
    if len(sys.argv) < 2:
        raise SystemExit("uso: import_dashboard_json.py <dashboard.json> [mensagem]")
    json_file = Path(sys.argv[1])
    message = sys.argv[2] if len(sys.argv) > 2 else "Atualizacao operacional automatica"
    grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000").rstrip("/")
    grafana_user = os.getenv("GRAFANA_USER", "SEU_USUARIO")
    grafana_password = os.getenv("GRAFANA_PASSWORD", "SUA_SENHA")

    dashboard = json.loads(json_file.read_text(encoding="utf-8"))
    payload = {"dashboard": dashboard, "folderId": 0, "overwrite": True, "message": message}
    response = requests.post(
        f"{grafana_url}/api/dashboards/db",
        auth=(grafana_user, grafana_password),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    print(json.dumps({"url": grafana_url + result["url"], "result": result}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
