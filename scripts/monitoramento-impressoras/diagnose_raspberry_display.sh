#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
OUT="${LOG_DIR}/raspberry-display-diagnose-$(date +%F-%H%M).log"
mkdir -p "${LOG_DIR}"

{
  echo "== Sistema =="
  date
  uname -a || true
  cat /etc/os-release 2>/dev/null || true

  echo
  echo "== Ambiente grafico =="
  echo "DISPLAY=${DISPLAY:-}"
  echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-}"
  echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}"
  echo "DESKTOP_SESSION=${DESKTOP_SESSION:-}"

  echo
  echo "== Resolucao / escala =="
  command -v xrandr >/dev/null 2>&1 && xrandr --current || echo "xrandr indisponivel ou sem DISPLAY"
  command -v xdpyinfo >/dev/null 2>&1 && xdpyinfo | sed -n '1,80p' || true
  command -v wlr-randr >/dev/null 2>&1 && wlr-randr || true

  echo
  echo "== Config Raspberry =="
  for f in /boot/config.txt /boot/firmware/config.txt /boot/cmdline.txt /boot/firmware/cmdline.txt; do
    if [[ -f "$f" ]]; then
      echo "--- $f"
      sed -n '1,220p' "$f"
    fi
  done

  echo
  echo "== Chromium =="
  command -v chromium-browser || true
  command -v chromium || true
  pgrep -a chromium || true
  pgrep -a chromium-browser || true

  echo
  echo "== Autostart =="
  find /etc/xdg/autostart "${HOME}/.config/autostart" -maxdepth 1 -type f 2>/dev/null | sort | while read -r f; do
    case "$f" in
      *grafana*|*chromium*|*kiosk*)
        echo "--- $f"
        sed -n '1,160p' "$f"
        ;;
    esac
  done
} | tee "$OUT"

echo
echo "Relatorio salvo em: $OUT"
