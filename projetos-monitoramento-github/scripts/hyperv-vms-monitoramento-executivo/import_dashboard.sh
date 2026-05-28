#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="$ROOT/logs"
BACKUP="$ROOT/backup"
DASHBOARD="$ROOT/dashboard-hyperv-hosts.json"
ENV_FILE="$ROOT/.env"

mkdir -p "$LOGS" "$BACKUP"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_USER=SEU_USUARIO
GRAFANA_PASSWORD=SUA_SENHA
ZABBIX_DATASOURCE_UID="${ZABBIX_DATASOURCE_UID:-zabbix}"
DASHBOARD_UID="hyperv-hosts-monitoramento-executivo"

echo "Validando Grafana em $GRAFANA_URL..."
curl -fsS -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/health" | tee "$LOGS/grafana-health.json" >/dev/null

echo "Detectando datasource Zabbix existente..."
DETECTED_UID="$(curl -fsS -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/datasources" \
  | jq -r '.[] | select((.type=="alexanderzobnin-zabbix-datasource") or (.type=="alexanderzobnin-zabbix-app") or (.name|test("zabbix";"i"))) | .uid' \
  | head -n 1)"

if [ -n "${DETECTED_UID:-}" ] && [ "$DETECTED_UID" != "null" ]; then
  ZABBIX_DATASOURCE_UID="$DETECTED_UID"
else
  ZABBIX_DATASOURCE_UID="${ZABBIX_DATASOURCE_UID:-zabbix}"
fi

echo "Datasource Zabbix usado: $ZABBIX_DATASOURCE_UID" | tee "$LOGS/datasource-used.log"
export ZABBIX_DATASOURCE_UID

echo "Gerando dashboard com UID do datasource..."
DASHBOARD_MODE="${DASHBOARD_MODE:-full}" python3 "$ROOT/scripts/generate_hyperv_dashboard.py" | tee "$LOGS/import-generation.log"

echo "Consultando dashboard existente..."
if curl -fsS -u "$GRAFANA_USER:$GRAFANA_PASSWORD" "$GRAFANA_URL/api/dashboards/uid/$DASHBOARD_UID" > "$BACKUP/dashboard-existing-$DASHBOARD_UID.json"; then
  TS="$(date +%Y%m%d-%H%M%S)"
  cp "$BACKUP/dashboard-existing-$DASHBOARD_UID.json" "$BACKUP/dashboard-$DASHBOARD_UID-$TS.json"
  echo "Backup criado: backup/dashboard-$DASHBOARD_UID-$TS.json"
else
  rm -f "$BACKUP/dashboard-existing-$DASHBOARD_UID.json"
  echo "Dashboard ainda nao existia no Grafana."
fi

echo "Importando/atualizando dashboard..."
TMP_BODY="$LOGS/dashboard-import-result.json"
HTTP_CODE="$(
  jq '{dashboard: ., folderUid: null, overwrite: true, message: "Atualizado por run_all.sh"}' "$DASHBOARD" \
    | curl -sS -u "$GRAFANA_USER:$GRAFANA_PASSWORD" \
        -H "Content-Type: application/json" \
        -X POST "$GRAFANA_URL/api/dashboards/db" \
        --data-binary @- \
        -o "$TMP_BODY" \
        -w "%{http_code}"
)"

cat "$TMP_BODY"
echo

if [ "$HTTP_CODE" -lt 200 ] || [ "$HTTP_CODE" -ge 300 ]; then
  {
    echo "Dashboard nao importado."
    echo "HTTP status: $HTTP_CODE"
    echo "Provavel causa: usuario Grafana sem permissao de escrita em dashboards ou pasta."
    echo "Usuario usado: $GRAFANA_USER"
  } | tee "$LOGS/dashboard-import-error.log"
  exit 3
fi

echo
echo "Dashboard importado:"
echo "$GRAFANA_URL/d/$DASHBOARD_UID/hyper-v-hosts-monitoramento-executivo"
