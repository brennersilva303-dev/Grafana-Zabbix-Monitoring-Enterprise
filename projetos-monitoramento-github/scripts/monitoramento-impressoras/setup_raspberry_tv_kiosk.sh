#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "${ROOT_DIR}/.env"
set +a

: "${GRAFANA_URL:?Defina GRAFANA_URL no .env}"

BACKUP_DIR="${ROOT_DIR}/backup/raspberry-tv-$(date +%F-%H%M)"
mkdir -p "$BACKUP_DIR"

backup_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    mkdir -p "$BACKUP_DIR$(dirname "$file")"
    cp -a "$file" "$BACKUP_DIR$file"
  fi
}

CONFIG_FILE=""
if [[ -f /boot/firmware/config.txt ]]; then
  CONFIG_FILE="/boot/firmware/config.txt"
elif [[ -f /boot/config.txt ]]; then
  CONFIG_FILE="/boot/config.txt"
fi

CMDLINE_FILE=""
if [[ -f /boot/firmware/cmdline.txt ]]; then
  CMDLINE_FILE="/boot/firmware/cmdline.txt"
elif [[ -f /boot/cmdline.txt ]]; then
  CMDLINE_FILE="/boot/cmdline.txt"
fi

backup_file "${CONFIG_FILE:-/dev/null}"
backup_file "${CMDLINE_FILE:-/dev/null}"
backup_file "${HOME}/.config/autostart/grafana-printers-kiosk.desktop"
backup_file "${HOME}/.config/lxsession/LXDE-pi/autostart"
backup_file "${HOME}/.config/openbox/autostart"
backup_file "${HOME}/.config/chromium/Default/Preferences"

if [[ -n "$CONFIG_FILE" ]]; then
  python3 - "$CONFIG_FILE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(errors="ignore")
lines = text.splitlines()
managed = {
    "disable_overscan": "1",
    "hdmi_force_hotplug": "1",
    "hdmi_group": "1",
    "hdmi_mode": "16",
    "framebuffer_width": "1920",
    "framebuffer_height": "1080",
    "max_framebuffers": "2",
    "gpu_mem": "128",
}
seen = set()
out = []
for line in lines:
    raw = line.strip()
    key = raw.split("=", 1)[0] if "=" in raw else ""
    if key in managed:
        out.append(f"{key}={managed[key]}")
        seen.add(key)
    else:
        out.append(line)
if not seen:
    out.append("")
    out.append("# Grafana printers TV/NOC 1080p")
for key, value in managed.items():
    if key not in seen:
        out.append(f"{key}={value}")
path.write_text("\n".join(out).rstrip() + "\n")
PY
fi

mkdir -p "${HOME}/.config/autostart" "${HOME}/.config/grafana-printers-kiosk"

cat > "${HOME}/.config/grafana-printers-kiosk/launch.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail

export DISPLAY="\${DISPLAY:-:0}"
xset s off -dpms s noblank 2>/dev/null || true
xrandr --output HDMI-1 --mode 1920x1080 --rate 60 2>/dev/null || true
xrandr --output HDMI-0 --mode 1920x1080 --rate 60 2>/dev/null || true
xrandr --output HDMI-2 --mode 1920x1080 --rate 60 2>/dev/null || true

pkill -f 'chromium.*printer-monitoring' 2>/dev/null || true
sleep 1

exec "${CHROMIUM_BIN:-/usr/bin/chromium-browser}" \\
  --kiosk \\
  --start-fullscreen \\
  --no-first-run \\
  --disable-infobars \\
  --disable-session-crashed-bubble \\
  --disable-pinch \\
  --overscroll-history-navigation=0 \\
  --force-device-scale-factor=1 \\
  --high-dpi-support=1 \\
  --window-position=0,0 \\
  --window-size=1920,1080 \\
  --user-data-dir="\${HOME}/.config/grafana-printers-kiosk/profile" \\
  "${GRAFANA_URL%/}/d/printer-monitoring/monitoramento-de-impressoras?orgId=1&refresh=1m&kiosk"
EOF
chmod +x "${HOME}/.config/grafana-printers-kiosk/launch.sh"

cat > "${HOME}/.config/autostart/grafana-printers-kiosk.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Grafana Printers Kiosk
Comment=Painel TV/NOC de impressoras
Exec=${HOME}/.config/grafana-printers-kiosk/launch.sh
X-GNOME-Autostart-enabled=true
EOF

cat > "${ROOT_DIR}/docs/raspberry-tv-kiosk.md" <<EOF
# Raspberry TV Kiosk

Backups criados em:

\`${BACKUP_DIR}\`

URL usada:

\`${GRAFANA_URL%/}/d/printer-monitoring/monitoramento-de-impressoras?orgId=1&refresh=1m&kiosk\`

Configuracao aplicada quando \`/boot/config.txt\` ou \`/boot/firmware/config.txt\` existe:

- \`disable_overscan=1\`
- \`hdmi_force_hotplug=1\`
- \`hdmi_group=1\`
- \`hdmi_mode=16\`  # 1920x1080 60Hz TV/CEA
- \`framebuffer_width=1920\`
- \`framebuffer_height=1080\`
- \`gpu_mem=128\`

Launcher:

\`${HOME}/.config/grafana-printers-kiosk/launch.sh\`

Autostart:

\`${HOME}/.config/autostart/grafana-printers-kiosk.desktop\`

Apos aplicar na Raspberry, reinicie:

\`sudo reboot\`

Na TV, desative overscan na propria TV usando modo "Just Scan", "Screen Fit", "Original", "1:1" ou equivalente.
EOF

echo "Backups: $BACKUP_DIR"
echo "Launcher: ${HOME}/.config/grafana-printers-kiosk/launch.sh"
echo "Autostart: ${HOME}/.config/autostart/grafana-printers-kiosk.desktop"
echo "Documentacao: ${ROOT_DIR}/docs/raspberry-tv-kiosk.md"
if [[ -n "$CONFIG_FILE" ]]; then
  echo "Config Raspberry ajustado: $CONFIG_FILE"
  echo "Reinicie a Raspberry para aplicar HDMI/overscan."
else
  echo "Aviso: config.txt da Raspberry nao encontrado neste host."
fi
