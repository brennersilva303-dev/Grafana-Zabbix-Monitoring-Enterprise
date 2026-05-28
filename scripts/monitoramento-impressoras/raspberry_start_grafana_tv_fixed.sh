#!/usr/bin/env bash
set -euo pipefail
export DISPLAY=${DISPLAY:-:0}
URL='http://SEU_SERVIDOR_INTERNO'
ROOT="$HOME/grafana-printers-validation"
mkdir -p "$ROOT/logs" "$ROOT/screenshots"
pkill -f chromium-browser || true
sleep 2
chromium-browser \
  --remote-debugging-port=9222 \
  --kiosk \
  --start-fullscreen \
  --window-position=0,0 \
  --window-size=3840,2160 \
  --force-device-scale-factor=1 \
  --high-dpi-support=1 \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  "$URL" >/tmp/chromium-printers-tv.log 2>&1 &
sleep 10
python3 "$ROOT/inject_grafana_tv_css.py"
