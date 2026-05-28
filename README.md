# Projetos de Monitoramento para Grafana e Zabbix

Pacote sanitizado para GitHub com dashboards, scripts de automacao e documentacao para quatro projetos oficiais:

- Monitoramento de Impressoras
- Hyper-V Hosts - Monitoramento Executivo V2
- Monitoramento DVR Intelbras
- Hyper-V VMs - Monitoramento Executivo

## Estrutura

```text
dashboards/   Dashboards Grafana exportados sem IDs internos fixos
scripts/      Scripts de descoberta, coleta, importacao e validacao
images/       Screenshots disponiveis dos dashboards
docs/         Relatorio de sanitizacao e notas tecnicas
```

## Tecnologias

- Grafana
- Zabbix e plugin Zabbix datasource para Grafana
- Python 3
- Shell script
- Raspberry Pi em modo kiosk com Chromium
- SNMP, quando aplicavel aos dispositivos monitorados

## Screenshots

![Monitoramento de Impressoras](images/monitoramento-impressoras.png)
![Hyper-V Hosts V2](images/hyperv-hosts-monitoramento-executivo-v2.png)
![Hyper-V VMs](images/hyperv-vms-monitoramento-executivo.png)

O projeto DVR Intelbras nao tinha screenshot seguro disponivel no momento da exportacao; importe o dashboard em seu Grafana e gere uma imagem propria se desejar.

## Como usar

Leia `INSTALL.md`, copie `.env.example` para `.env` localmente e preencha os valores do seu ambiente. Nunca commite `.env`.
