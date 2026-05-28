#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "${ROOT_DIR}/.env"
set +a

IP="${1:-SEU_IP_PRIVADO}"
COMMUNITY="${2:-${DVR_SNMP_COMMUNITY:-Publico}}"
OUT_DIR="${ROOT_DIR}/logs/snmp/${IP}"
mkdir -p "${OUT_DIR}"

FULL="${OUT_DIR}/snmpwalk-full.txt"
PRIVATE="${OUT_DIR}/snmpwalk-private.txt"
SYSTEM="${OUT_DIR}/snmpwalk-system.txt"
SUMMARY="${OUT_DIR}/summary.txt"

{
  echo "Data: $(date -Is)"
  echo "DVR: ${IP}"
  echo "SNMP: v2c community=${COMMUNITY}"
  echo
} > "${SUMMARY}"

if ! command -v snmpwalk >/dev/null 2>&1; then
  echo "ERRO: snmpwalk nao encontrado. Instale net-snmp-utils." | tee -a "${SUMMARY}" >&2
  exit 2
fi

set +e
snmpwalk -v2c -c "${COMMUNITY}" -t 2 -r 1 "${IP}" 1.3.6.1.2.1 > "${SYSTEM}" 2>> "${SUMMARY}"
SYSTEM_RC=$?
snmpwalk -v2c -c "${COMMUNITY}" -t 2 -r 1 "${IP}" 1.3.6.1.4.1 > "${PRIVATE}" 2>> "${SUMMARY}"
PRIVATE_RC=$?
snmpwalk -v2c -c "${COMMUNITY}" -t 2 -r 1 "${IP}" > "${FULL}" 2>> "${SUMMARY}"
FULL_RC=$?
set -e

{
  echo
  echo "Retornos:"
  echo "  system=${SYSTEM_RC}"
  echo "  private=${PRIVATE_RC}"
  echo "  full=${FULL_RC}"
  echo
  echo "Candidatos encontrados por palavra-chave:"
  grep -Eia "video|loss|camera|channel|canal|hdd|disk|storage|sata|health|error|alarm|record" "${FULL}" "${PRIVATE}" "${SYSTEM}" 2>/dev/null | head -200 || true
} >> "${SUMMARY}"

cat "${SUMMARY}"
exit "${FULL_RC}"
