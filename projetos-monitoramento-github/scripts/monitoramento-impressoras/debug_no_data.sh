#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/debug_no_data.log"

{
  echo "== Grafana datasource =="
  "${ROOT_DIR}/scripts/test_grafana_datasource.sh"
  echo
  echo "== Zabbix items =="
  python3 "${ROOT_DIR}/scripts/test_zabbix_items.py"
  echo
  echo "== Inventory summary =="
  python3 - <<'PY'
import json
from pathlib import Path
p = Path('/CAMINHO/DO/PROJETO/dashboards/printers-inventory.json')
if p.exists():
    d = json.loads(p.read_text())
    print('printers=', d.get('count'))
    print('snmp_items_found=', d.get('snmp_items_found'))
else:
    print('Inventario nao existe')
PY
} | tee "${LOG_FILE}"

echo "Relatorio de debug: ${LOG_FILE}"
