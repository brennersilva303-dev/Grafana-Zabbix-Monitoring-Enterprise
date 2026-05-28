#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JSON_FILE="$ROOT/dashboard-hyperv-vms.json"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_USER=SEU_USUARIO
GRAFANA_PASSWORD=SUA_SENHA

if [[ ! -f "$JSON_FILE" ]]; then
  echo "Arquivo nao encontrado: $JSON_FILE" >&2
  exit 1
fi

python3 - "$JSON_FILE" "$GRAFANA_URL" "$GRAFANA_USER" "$GRAFANA_PASSWORD" <<'PY'
import json
import sys
from pathlib import Path

import requests

json_file = Path(sys.argv[1])
grafana_url, user, password = sys.argv[2:6]
dashboard = json.loads(json_file.read_text())
payload = {
    "dashboard": dashboard,
    "folderId": 0,
    "overwrite": True,
    "message": "Importa dashboard Hyper-V VMs - Monitoramento Executivo",
}
response = requests.post(
    f"{grafana_url.rstrip('/')}/api/dashboards/db",
    auth=(user, password),
    json=payload,
    timeout=30,
)
response.raise_for_status()
result = response.json()
print(json.dumps({"url": grafana_url.rstrip("/") + result["url"], "result": result}, indent=2, ensure_ascii=False))
PY
