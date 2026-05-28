# Grafana Printers

Provisionamento completo de impressoras SNMP no Zabbix 5.0.2 e dashboard NOC no Grafana usando o datasource Zabbix existente.

## Enderecos

- Zabbix API: `http://SEU_SERVIDOR_INTERNO
- Grafana: `http://SEU_SERVIDOR_INTERNO
- Dashboard: `http://SEU_SERVIDOR_INTERNO
- Modo TV/Kiosk: `http://SEU_SERVIDOR_INTERNO

## Execucao

```bash
cd /CAMINHO/DO/PROJETO
./run_all.sh
```

O fluxo valida `.env`, API Zabbix, `user.login`, grupo `Impressoras`, hosts, SNMP, itens, triggers, datasource Grafana, inventario, dashboard JSON e importacao sem duplicar.

## Arquivos Principais

- `scripts/printers_list.txt`: IPs das impressoras.
- `scripts/setup_zabbix_printers.py`: cria/atualiza grupo, hosts, interfaces SNMP, itens e triggers.
- `scripts/discover_zabbix_printers.py`: gera `dashboards/printers-inventory.json`.
- `scripts/generate_grafana_dashboard.py`: gera dashboard sem variaveis de template, usando `itemid` real do Zabbix.
- `scripts/import_dashboard.sh`: importa/atualiza o dashboard no Grafana.
- `scripts/test_zabbix_items.py`: mostra itens, ultimos valores e motivos de `No data`.
- `scripts/test_grafana_datasource.sh`: lista e valida datasource Zabbix no Grafana.
- `scripts/debug_no_data.sh`: gera `logs/debug_no_data.log`.

## Fonte Oficial

`scripts/printers_list.txt` e a fonte oficial de nomes, IPs, modelos e status. O arquivo fica em CSV:

```text
Nome,IP,Modelo,Status
```

Hosts antigos fora dessa base saem do grupo `Impressoras` e vao para `Impressoras - Ignoradas`, para nao aparecerem no dashboard.

## Itens Criados

- `printer.ping`
- `printer.snmp.available`
- `printer.status`
- `printer.toner.black`
- `printer.toner.cyan`
- `printer.toner.magenta`
- `printer.toner.yellow`
- `printer.error`

Tambem e mantido `icmpping` como base de coleta ICMP. O dashboard usa consultas por `itemid`, evitando regex/variaveis que causavam `q.replace is not a function`.

## Dashboard

O dashboard `Monitoramento de Impressoras` usa layout estatico de TV/NOC em tela unica.

- fundo claro;
- topo executivo compacto;
- grid unico com 41 cards;
- 6 colunas por linha;
- 7 linhas no total;
- sem paginas, carrossel, playlist ou scroll automatico;
- cada card mostra nome, status, setor, IP, modelo, serial, ping, SNMP e ultima coleta;
- online em verde, offline em vermelho, sem SNMP em amarelo.

O gerador executa validacao matematica para 1920x1080 antes de salvar o JSON:

- largura: 1920 px;
- altura: 1080 px;
- topo maximo: 120 px;
- margem externa maxima: 12 px;
- gap maximo entre cards: 8 px;
- grid ate 940 px;
- card com altura aproximada maxima de 125 px.

Relatorio visual:

```bash
python3 scripts/validate_dashboard_visual.py
```

Saida salva em:

- `docs/mockups/visual-validation.json`

## TV / Kiosk

Para a TV, use `&kiosk` puro. Nesta versao do Grafana, `&kiosk=tv` ainda deixa camadas da interface visiveis e reduz a area util.

Launcher recomendado no servidor da TV:

```bash
cd /CAMINHO/DO/PROJETO
./scripts/launch_grafana_tv_kiosk.sh
```

Checklist da TV/navegador:

- Chrome/Chromium em zoom 100%: `Ctrl+0`.
- Tela cheia real: `F11` ou launcher com `--kiosk`.
- Escala do sistema operacional em 100%.
- Resolucao de saida em 3840x2160 a 60Hz quando usando a TV 4K.
- Na TV, usar modo de imagem sem overscan, geralmente chamado `Just Scan`, `Original`, `Screen Fit` ou equivalente.

Diagnostico de escala/renderizacao:

```bash
python3 scripts/diagnose_grafana_tv_scale.py
```

O diagnostico testa modo normal, `kiosk=tv`, `kiosk`, zoom/DPI simulados e salva:

- `docs/mockups/grafana-tv-scale-report.json`
- `docs/mockups/printer-dashboard-scale-*.png`

Resultado esperado: `cards=41`, `hasVerticalOverflow=false`, `devicePixelRatio=1`, URL com `&kiosk` e preenchimento do grid acima de 80%.

## Raspberry Pi

Este projeto tambem inclui ajustes focados na Raspberry ligada na TV 4K, quando a saida esta limitada a 1920x1080.

Primeiro rode o diagnostico na propria Raspberry:

```bash
cd /CAMINHO/DO/PROJETO
./scripts/diagnose_raspberry_display.sh
```

Depois aplique o kiosk 1080p com backup automatico:

```bash
cd /CAMINHO/DO/PROJETO
./scripts/setup_raspberry_tv_kiosk.sh
sudo reboot
```

O script cria backup dos arquivos encontrados em `/boot`, configs de Chromium/autostart e gera:

- `~/.config/grafana-printers-kiosk/launch.sh`
- `~/.config/autostart/grafana-printers-kiosk.desktop`
- `docs/raspberry-tv-kiosk.md`

A URL correta para a Raspberry e:

```text
http://SEU_SERVIDOR_INTERNO
```

Na TV 4K, mantenha a saida da Raspberry em 1920x1080 60Hz, zoom do Chromium em 100%, escala do sistema em 100% e overscan/deslocamento da TV desativado.

## Diagnostico

```bash
scripts/debug_no_data.sh
```

Se ainda houver `No data`, veja:

- `logs/debug_no_data.log`
- `logs/test_zabbix_items.json`

O diagnostico indica itens faltantes, itens sem `lastclock` e hosts ainda sem coleta.
