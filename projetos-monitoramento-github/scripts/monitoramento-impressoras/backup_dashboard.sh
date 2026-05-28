#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "${ROOT_DIR}/backup"
cp "${ROOT_DIR}/dashboards/printer-dashboard.json" "${ROOT_DIR}/backup/printer-dashboard-${STAMP}.json"
cp "${ROOT_DIR}/dashboards/printers-inventory.json" "${ROOT_DIR}/backup/printers-inventory-${STAMP}.json" 2>/dev/null || true
tar -czf "${ROOT_DIR}/backup/grafana-printers-${STAMP}.tar.gz" -C "${ROOT_DIR}" dashboards provisioning scripts docs README.md .env logs 2>/dev/null || true
echo "Backup criado em ${ROOT_DIR}/backup"
