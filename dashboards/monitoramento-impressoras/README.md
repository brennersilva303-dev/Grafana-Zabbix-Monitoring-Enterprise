# Monitoramento de Impressoras

Dashboard Grafana sanitizado para uso com datasource Zabbix variavel.

## Arquivos

- `dashboard.json`: dashboard pronto para importacao.
- Screenshots relacionados ficam em `../../images/` quando disponiveis.

## EDITE AQUI

Ao importar no Grafana, selecione o datasource Zabbix do seu ambiente na variavel `DS_ZABBIX`.
Configure URLs, usuarios e senhas somente em `.env` local, nunca neste arquivo JSON.
