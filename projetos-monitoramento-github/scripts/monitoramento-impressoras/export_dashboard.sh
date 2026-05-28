#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "${ROOT_DIR}/.env"
set +a
: "${GRAFANA_URL:?Defina GRAFANA_URL no .env}"
UID="${DASHBOARD_UID:-printer-monitoring}"
OUT="${1:-${ROOT_DIR}/dashboards/printer-dashboard.json}"
AUTH_ARGS=()
if [[ -n "${GRAFANA_TOKEN:-}" ]]; then
  AUTH_ARGS=(-H "Authorization: Bearer ${GRAFANA_TOKEN}")
else
  AUTH_ARGS=(-u "${GRAFANA_USER:-admin}:${GRAFANA_PASSWORD:-admin}")
fi
curl -fsS "${AUTH_ARGS[@]}" -H "Content-Type: application/json" "${GRAFANA_URL%/}/api/dashboards/uid/${UID}" | jq '.dashboard' > "${OUT}"
echo "Dashboard exportado: ${OUT}"
