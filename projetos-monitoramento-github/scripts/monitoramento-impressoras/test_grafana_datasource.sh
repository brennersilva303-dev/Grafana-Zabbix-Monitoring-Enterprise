#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "${ROOT_DIR}/.env"
set +a

GRAFANA_URL="${GRAFANA_URL:-http://SEU_SERVIDOR_INTERNO"
AUTH_ARGS=()
if [[ -n "${GRAFANA_TOKEN:-}" ]]; then
  AUTH_ARGS=(-H "Authorization: Bearer ${GRAFANA_TOKEN}")
else
  AUTH_ARGS=(-u "${GRAFANA_USER}:${GRAFANA_PASSWORD}")
fi

echo "Grafana: ${GRAFANA_URL}"
curl -fsS "${AUTH_ARGS[@]}" "${GRAFANA_URL%/}/api/datasources" \
  | jq -r '.[] | select((.type|test("zabbix";"i")) or (.name|test("zabbix";"i")) or (.url|test("zabbix";"i"))) | "name=\(.name) uid=\(.uid) type=\(.type) url=\(.url)"'

uid="$(curl -fsS "${AUTH_ARGS[@]}" "${GRAFANA_URL%/}/api/datasources" | jq -r '.[] | select((.type|test("zabbix";"i")) or (.name|test("zabbix";"i")) or (.url|test("zabbix";"i"))) | .uid' | head -1)"
if [[ -z "${uid}" ]]; then
  echo "Nenhum datasource Zabbix encontrado no Grafana" >&2
  exit 1
fi
echo "Datasource Zabbix detectado: ${uid}"
