#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="$ROOT/logs"
LOCK_DIR="$LOGS/update-operational.lock"
STATUS="$LOGS/realtime-update-status.json"
RUN_LOG="$LOGS/realtime-update.log"

mkdir -p "$LOGS"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "{\"status\":\"skipped\",\"reason\":\"previous run still active\",\"timestamp\":\"$(date -Is)\"}" > "$STATUS"
  exit 0
fi
trap 'rm -rf "$LOCK_DIR"' EXIT

cd "$ROOT"

START_TS="$(date -Is)"
{
  echo "[$START_TS] inicio atualizacao operacional"

  python3 scripts/discover_hyperv_items.py
  python3 scripts/test_dashboard_data.py
  python3 scripts/generate_hyperv_dashboard_v2.py
  python3 scripts/import_dashboard_json.py dashboard-hyperv-hosts-v2.json "Atualizacao operacional Hosts V2"

  python3 scripts/collect_hyperv_vm_metrics.py
  python3 scripts/generate_hyperv_vms_dashboard.py
  python3 scripts/import_dashboard_json.py dashboard-hyperv-vms.json "Atualizacao operacional Hyper-V VMs"

  END_TS="$(date -Is)"
  cat > "$STATUS" <<JSON
{
  "status": "OK",
  "started_at": "$START_TS",
  "finished_at": "$END_TS",
  "cycle": "1m",
  "dashboards": [
    {
      "uid": "hyperv-hosts-executivo-v2",
      "json": "dashboard-hyperv-hosts-v2.json",
      "updated": true
    },
    {
      "uid": "hyperv-vms-executivo",
      "json": "dashboard-hyperv-vms.json",
      "updated": true
    }
  ],
  "visual_changed": false,
  "kiosk_changed": false,
  "playlist_changed": false
}
JSON
  echo "[$END_TS] fim atualizacao operacional"
} >> "$RUN_LOG" 2>&1
