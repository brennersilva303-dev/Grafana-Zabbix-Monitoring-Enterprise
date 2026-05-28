#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "${ROOT_DIR}/.env"
set +a

DASHBOARD_FILE="${1:-${ROOT_DIR}/dashboards/camera-dvr-dashboard.json}"
AUTH_ARGS=()
if [[ -n "${GRAFANA_TOKEN:-}" ]]; then
  AUTH_ARGS=(-H "Authorization: Bearer ${GRAFANA_TOKEN}")
else
  AUTH_ARGS=(-u "${GRAFANA_USER:-admin}:${GRAFANA_PASSWORD:-admin}")
fi

jq -n --argjson dashboard "$(jq '.id = null' "${DASHBOARD_FILE}")" '{dashboard: $dashboard, overwrite: true}' \
  | curl -fsS "${AUTH_ARGS[@]}" -H "Content-Type: application/json" -X POST -d @- "${GRAFANA_URL%/}/api/dashboards/db"
echo
echo "Dashboard importado: ${DASHBOARD_FILE}"
