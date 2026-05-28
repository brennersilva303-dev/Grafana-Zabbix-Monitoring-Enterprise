# Instalacao

## Pre-requisitos

- Grafana instalado e acessivel
- Zabbix instalado e com API habilitada
- Plugin Grafana Zabbix datasource instalado
- Python 3 e `pip`, quando os scripts Python forem usados
- Acesso SNMP aos dispositivos, quando aplicavel
- Raspberry Pi com Chromium, caso use modo kiosk

## Configuracao

1. Copie `.env.example` para `.env` fora do controle de versao.
2. Edite as variaveis:
   - `GRAFANA_URL`
   - `ZABBIX_URL`
   - `ZABBIX_USER`
   - `ZABBIX_PASSWORD`
3. Ajuste `datasource.example.yml` para provisionar o datasource Zabbix no Grafana.

## Importar dashboards

No Grafana, use Import dashboard e escolha um dos arquivos:

- `dashboards/monitoramento-impressoras/dashboard.json`
- `dashboards/hyperv-hosts-monitoramento-executivo-v2/dashboard.json`
- `dashboards/monitoramento-dvr-intelbras/dashboard.json`
- `dashboards/hyperv-vms-monitoramento-executivo/dashboard.json`

Durante a importacao, selecione o datasource Zabbix do seu ambiente na variavel `DS_ZABBIX`.

## Scripts

Os scripts ficam em `scripts/<projeto>/`. Antes de executar, revise os comentarios `EDITE AQUI` e configure `.env`.

## Raspberry kiosk

Use os scripts de kiosk apenas em ambiente controlado. Edite a URL do Grafana/playlist com valores do seu ambiente e mantenha segredos fora do repositorio.
