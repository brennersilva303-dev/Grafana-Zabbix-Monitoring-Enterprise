#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DISCOVERY="$ROOT/logs/hyperv-items-discovery.json"
VALIDATION="$ROOT/logs/dashboard-data-validation.json"
DEBUG="$ROOT/logs/debug_no_data.log"

mkdir -p "$ROOT/logs"

{
  echo "Debug de paineis sem dados - Hyper-V Hosts"
  echo "Gerado em: $(date -Is)"
  echo

  if [ ! -f "$DISCOVERY" ]; then
    echo "Arquivo de descoberta nao encontrado: logs/hyperv-items-discovery.json"
    echo "Execute: ./run_all.sh"
    exit 0
  fi

  echo "Itens ausentes por host:"
  jq -r '.missing | to_entries[] | "\(.key): \(.value | join(", "))"' "$DISCOVERY"
  echo

  if [ -f "$VALIDATION" ]; then
    echo "Paineis sem item validado por API Zabbix ou zabbix_get:"
    jq -r '.panels_without_data[]? | "- \(.host) / \(.panel): \(.reason)"' "$VALIDATION"
    echo

    echo "Resumo de dados por host:"
    jq -r '.hosts | to_entries[] | "- \(.key): enabled_items=\(.value.enabled_items), items_with_data=\(.value.items_with_data), zabbix_host=\(.value.zabbix_host), visible_name=\(.value.zabbix_name)"' "$VALIDATION"
    echo

    echo "Itens escolhidos para paineis:"
    jq -r '.hosts | to_entries[] | "- \(.key): status=\(.value.selected.status.name // "sem dado"), uptime=\(.value.selected.uptime.name // "sem dado"), memoria=\(.value.selected.memory_used.name // "sem dado"), cpu=\(.value.selected.cpu_any.name // "sem dado"), disco=\(.value.selected.disk_percent.name // "sem dado"), rede_in=\(.value.selected.net_in.name // "sem dado"), rede_out=\(.value.selected.net_out.name // "sem dado")"' "$VALIDATION"
    echo
  fi

  echo "Problemas de descoberta:"
  jq -r '.problems[]?' "$DISCOVERY"
  echo

  echo "Sugestoes:"
  echo "- Confirme se os Host names HYPERV_HOST_A e HYPERV-HYPERV_HOST_B estao exatamente iguais no Zabbix/Grafana Zabbix."
  echo "- Se zabbix_get valida mas o Grafana nao retorna serie, o dashboard mostra valor de validacao e registra o caso em logs/dashboard-render-validation.json."
  echo "- Para HYPERV_HOST_A, confira a interface SEU_IP_PRIVADO:10050 e se os itens tecnicos sairam de lastclock=0."
  echo "- Revise templates Windows: CPU, memoria, filesystems, interfaces e servicos."
  echo "- Para servicos Hyper-V, crie itens/triggers para vmms, vmcompute e vmictimesync se nao houver descoberta automatica."
  echo "- Se o item existir com outro nome, ajuste os padroes em scripts/discover_hyperv_items.py."
} | tee "$DEBUG"
