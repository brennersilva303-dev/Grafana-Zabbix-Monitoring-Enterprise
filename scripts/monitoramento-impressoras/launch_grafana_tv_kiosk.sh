#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "${ROOT_DIR}/.env"
set +a

: "${GRAFANA_URL:?Defina GRAFANA_URL no .env}"

CHROMIUM_BIN="${CHROMIUM_BIN:-/usr/bin/chromium-browser}"
TV_SCALE="${TV_SCALE:-1}"
TV_URL="${GRAFANA_URL%/}/d/printer-monitoring/monitoramento-de-impressoras?orgId=1&refresh=1m&kiosk"

export DISPLAY="${DISPLAY:-:0}"
xset s off -dpms s noblank 2>/dev/null || true
xrandr --output HDMI-1 --mode 1920x1080 --rate 60 2>/dev/null || true
xrandr --output HDMI-0 --mode 1920x1080 --rate 60 2>/dev/null || true
xrandr --output HDMI-2 --mode 1920x1080 --rate 60 2>/dev/null || true

exec "${CHROMIUM_BIN}" \
  --kiosk \
  --start-fullscreen \
  --no-first-run \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  --force-device-scale-factor="${TV_SCALE}" \
  --high-dpi-support=1 \
  --window-position=0,0 \
  --window-size=1920,1080 \
  --user-data-dir="${HOME}/.config/grafana-printers-kiosk/profile" \
  "${TV_URL}"
