# Seguranca

Este pacote foi sanitizado para publicacao. Mesmo assim, revise antes de commitar.

## Nunca commitar

- `.env`
- senhas reais
- tokens
- cookies
- sessoes
- URLs internas
- IPs privados reais
- backups e logs de producao

## Como configurar segredos

Use `.env.example`, `config.example.yml` e `datasource.example.yml` como modelo. Preencha valores reais apenas no ambiente local/deploy.

## Checklist antes do commit

Execute buscas por IPs privados, tokens e senhas. Se encontrar valores reais, substitua por placeholders como `SEU_GRAFANA`, `SEU_ZABBIX`, `SEU_USUARIO`, `SUA_SENHA` e `SEU_TOKEN`.
