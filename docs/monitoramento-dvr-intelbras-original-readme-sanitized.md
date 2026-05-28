# CameraDVR

Monitoramento de DVRs Intelbras iMHDX usando Zabbix Proxy para coleta SNMP e Grafana apenas para visualizacao.

## Arquitetura

```text
DVR Intelbras -> Zabbix Proxy -> Zabbix Server -> Grafana
```

O Grafana nao coleta SNMP e nao precisa acessar o DVR. Ele consulta somente o datasource Zabbix existente.

## Ambiente

Referencia estudada, sem alteracao: `/CAMINHO/DO/PROJETO`.

Conexoes usadas:

- Zabbix API: `http://SEU_SERVIDOR_INTERNO
- Grafana: `http://SEU_SERVIDOR_INTERNO
- Datasource Grafana/Zabbix: `Zabbix00`, UID `E2lQF-HGk`
- Zabbix Proxy: `zabbixProxy`
- Zabbix Server/Proxy: `5.0.2`

## Diagnostico do Proxy

Problema confirmado em 2026-05-26:

- SNMP, DVR, OIDs e datasource Grafana estavam corretos.
- O host `DVR-GAMA` existia no Zabbix Server e estava associado ao proxy `zabbixProxy`.
- O proxy local recebia apenas `icmpping`; os itens SNMP nao entravam no SQLite do proxy.
- Causa: os itens SNMP foram criados como `type=4`. Neste ambiente Zabbix `5.0.2`, o padrao SNMP operacional usado pelos hosts existentes e sincronizado ao proxy e `type=20` (`SNMP agent`).
- Correcao aplicada: itens SNMP do `DVR-GAMA` convertidos para `type=20` e vinculados a interface SNMP `83`.

Validacao apos correcao:

- Proxy SQLite: `45` itens para o host `10429` (`1` ICMP + `44` SNMP).
- Config sync: pacote do proxy subiu de `datalen 304345` para `datalen 312705`.
- `dvr.online`, `dvr.channel.status[1..16]`, `dvr.hdd.status`, `dvr.hdd.error`, `dvr.hdd.capacity`, `dvr.hdd.used` e `dvr.device.model` passaram a ter `lastclock` real.

## DVRs monitorados

Todos os hosts ficam no grupo Zabbix `DVRs Intelbras`, associados ao proxy `zabbixProxy`, com interface SNMP v2c porta `161` e community `Publico`.

| Exibicao | Host Zabbix | IP | Modelo/Tipo | Canais | Observacao |
| --- | --- | --- | --- | --- |
| TAGUATINGA | `DVR-TAGUATINGA` | `SEU_IP_PRIVADO` | `iMHDX 3116` | 16 | SNMP OK |
| TAGUATINGA 2 | `DVR-TAGUATINGA 2` | `SEU_IP_PRIVADO` | `iMHDX 3116` | 16 | SNMP OK |
| SIA 01 | `DVR-SIA 01` | `SEU_IP_PRIVADO` | `iMHDX 3116` | 24 | SNMP OK |
| SIA 02 | `DVR-SIA 02` | `SEU_IP_PRIVADO` | `iMHDX 3116` | 24 | SNMP OK |
| SIA | `DVR-SIA` | `SEU_IP_PRIVADO` | iMHDX esperado | 16 | Sem ping/SNMP a partir do proxy em 2026-05-27 |
| GAMA 01 | `DVR-GAMA` | `SEU_IP_PRIVADO` | `iMHDX 3116` | 16 | Referencia funcional |
| GAMA 02 | `DVR-GAMA 02` | `SEU_IP_PRIVADO` | `iMHDX 3116` | 16 | SNMP OK |
| VALPARAISO 01 | `DVR-VALPARAISO 01` | `SEU_IP_PRIVADO` | `iMHDX 3116` | 16 | SNMP OK |
| VALPARAISO 02 | `DVR-VALPARAISO 02` | `SEU_IP_PRIVADO` | `iMHDX 3116` | 16 | SNMP OK |
| RECANTO | `DVR-RECANTO` | `SEU_IP_PRIVADO` | `NVD 1232` | 32 | SNMP OK; perfil NVD para HD |

Cameras IP SIA monitoradas por ICMP, sem SNMP, sem HD e sem canais internos:

| Exibicao/Host Zabbix | IP | Item |
| --- | --- | --- |
| `SIA-IP-01` | `SEU_IP_PRIVADO` | `icmpping` |
| `SIA-IP-02` | `SEU_IP_PRIVADO` | `icmpping` |
| `SIA-IP-03` | `SEU_IP_PRIVADO` | `icmpping` |
| `SIA-IP-04` | `SEU_IP_PRIVADO` | `icmpping` |
| `SIA-IP-05` | `SEU_IP_PRIVADO` | `icmpping` |

Inventario oficial: `scripts/dvrs_list.csv`.

## SNMP validado

Comando usado:

```bash
snmpwalk -On -v2c -c Publico SEU_IP_PRIVADO .1.3.6.1.4.1.1004849
```

Walk salvo em:

- `logs/snmp/SEU_IP_PRIVADO/intelbras-enterprise-walk.txt`

Enterprise Intelbras:

- `.1.3.6.1.4.1.1004849`

Modulos/tabelas encontrados:

- `VideoLossInfoTable`: `.1.3.6.1.4.1.1004849.2.3.2`
- `PhysicalVolumeInfoTable` / `oidStorageInfo`: `.1.3.6.1.4.1.1004849.2.4`
- `allChannelStatusTable`: `.1.3.6.1.4.1.1004849.2.SEU_IP_PRIVADO`
- `VideoChannelInfo`: `.1.3.6.1.4.1.1004849.2.10`

## OIDs mapeados

Arquivo oficial de OIDs:

- `config/oids_intelbras_imhdx3116.json`

Principais OIDs:

- Modelo: `.1.3.6.1.4.1.1004849.2.1.2.6.0`
- DVR online: `.1.3.6.1.4.1.1004849.2.1.2.8.0`
- Status de canal: `.1.3.6.1.4.1.1004849.2.SEU_IP_PRIVADO.3.<indice>`
- Texto de status de canal: `.1.3.6.1.4.1.1004849.2.SEU_IP_PRIVADO.2.<indice>`
- Nome de canal: `.1.3.6.1.4.1.1004849.2.SEU_IP_PRIVADO.3.<canal>`
- HD device: `.1.3.6.1.4.1.1004849.2.4.4.1.1.8.47.100.101.118.47.115.100.97`
- HD status: `.1.3.6.1.4.1.1004849.2.4.4.1.2.8.47.100.101.118.47.115.100.97`
- HD error: `.1.3.6.1.4.1.1004849.2.4.4.1.3.8.47.100.101.118.47.115.100.97`
- HD capacidade: `.1.3.6.1.4.1.1004849.2.4.4.1.4.8.47.100.101.118.47.115.100.97`
- HD usado: `.1.3.6.1.4.1.1004849.2.4.4.1.5.8.47.100.101.118.47.115.100.97`

OIDs NVD 1232 usados para RECANTO:

- Modelo: `.1.3.6.1.4.1.1004849.2.1.2.6.0`
- NVD online: `.1.3.6.1.4.1.1004849.2.1.2.8.0`
- HD status: `.1.3.6.1.4.1.1004849.2.4.1.1.2.1`
- HD error: `.1.3.6.1.4.1.1004849.2.4.1.1.3.1`
- HD device: `.1.3.6.1.4.1.1004849.2.4.1.1.4.1`
- HD volume status: `.1.3.6.1.4.1.1004849.2.4.1.1.5.1`
- HD capacidade: `.1.3.6.1.4.1.1004849.2.4.1.1.6.1`
- HD usado: `.1.3.6.1.4.1.1004849.2.4.1.1.7.1`
- Tabela de canais/IPs: `.1.3.6.1.4.1.1004849.2.SEU_IP_PRIVADO`

Observacao sobre indice dos canais:

- `dvr.channel.status[1]` usa indice SNMP `0`;
- `dvr.channel.status[16]` usa indice SNMP `15`;
- `dvr.channel.status[24]` usa indice SNMP `23`;
- valor `1` = conectado/OK;
- valor `0` = desconectado/perda de video.

## Itens Zabbix

Obrigatorios:

- `dvr.online`
- `dvr.channel.status[1..N]`, conforme quantidade real de canais;
- `dvr.channel.video_loss[1..N]`, conforme quantidade real de canais;
- `dvr.hdd.status`
- `dvr.hdd.capacity`
- `dvr.hdd.used`

Complementares:

- `dvr.snmp.sysdescr`
- `dvr.snmp.uptime`
- `dvr.device.model`
- `dvr.channel.name[1..N]`
- `dvr.total_count`
- `dvr.online_count`
- `dvr.offline_count`
- `dvr.cameras.ok_count`
- `dvr.cameras.total`
- `dvr.hdd.device`
- `dvr.hdd.error`
- `dvr.hdd.ok`
- `dvr.hdd.free_percent`
- `dvr.hdd.volume_status`

Nos iMHDX, `dvr.channel.video_loss[N]` e calculado a partir do item SNMP real `dvr.channel.status[N]`.

Formula usada:

- `dvr.channel.video_loss[N]`: `1-last(dvr.channel.status[N])`
- `dvr.cameras.ok_count`: soma de `last(dvr.channel.status[1..N])`
- `dvr.total_count`: `last(dvr.online)+1-last(dvr.online)`
- `dvr.online_count`: `last(dvr.online)`
- `dvr.offline_count`: `1-last(dvr.online)`
- `dvr.hdd.ok`: `last(dvr.hdd.status)*(1-last(dvr.hdd.error))`

## Triggers

- `DVR offline`
- `SNMP DVR sem resposta`
- `Canal 01..16 com perda de video`
- `HD ausente`
- `HD do DVR com falha`

Para cameras IP SIA:

- `Camera IP offline`, usando `icmpping.max(3m)=0`

## Validacao 2026-05-26

Validado a partir do Zabbix Proxy:

- `SEU_IP_PRIVADO`, `SEU_IP_PRIVADO`, `SEU_IP_PRIVADO`, `SEU_IP_PRIVADO`, `SEU_IP_PRIVADO`, `SEU_IP_PRIVADO`, `SEU_IP_PRIVADO`, `SEU_IP_PRIVADO` e `SEU_IP_PRIVADO`: ping e SNMP OK com `Publico`.
- `SEU_IP_PRIVADO`: ping falha e SNMP timeout a partir do proxy; host/itens foram criados, mas depende de conectividade do proxy ate o equipamento.
- O proxy SQLite recebeu os hosts e itens apos `zabbix_proxy -R config_cache_reload`.

## Validacao 2026-05-27

Validado a partir do Zabbix Proxy:

- Cameras SIA-IP `SEU_IP_PRIVADO`, `SEU_IP_PRIVADO`, `SEU_IP_PRIVADO`, `SEU_IP_PRIVADO` e `SEU_IP_PRIVADO`: ping OK.
- `allChannelStatusTable` iMHDX:
  - TAGUATINGA: 16 indices, 6 OK e 10 offline/perda.
  - TAGUATINGA 2: 16 indices, 16 OK.
  - SIA 01: 24 indices, 24 OK.
  - SIA 02: 24 indices, 22 OK e 2 offline/perda.
  - GAMA 01: 16 indices, 11 OK e 5 offline/perda.
  - GAMA 02: 16 indices, 14 OK e 2 offline/perda.
  - VALPARAISO 01: 16 indices, 16 OK.
  - VALPARAISO 02: 16 indices, 16 OK.
- RECANTO `NVD 1232`: 32 cameras IP expostas na tabela `.1.3.6.1.4.1.1004849.2.SEU_IP_PRIVADO`; status operacional derivado de `dvr.online`.
- `SEU_IP_PRIVADO`: segue sem ping/SNMP a partir do proxy.
- Datasource Grafana retornou `199` series: DVR/HD/canais reais, SIA-IP por `icmpping` e canais ate `C32`.

## Execucao

```bash
cd /CAMINHO/DO/PROJETO
./run_all.sh
```

Ou por etapas:

```bash
cd /CAMINHO/DO/PROJETO
python3 scripts/setup_zabbix_dvrs.py
python3 scripts/discover_zabbix_dvrs.py
python3 scripts/generate_grafana_dashboard.py
./scripts/import_dashboard.sh
```

Relatorio:

- `dashboards/zabbix-dvrs-setup-report.json`

## Grafana

Dashboard:

- Titulo: `Monitoramento DVR Intelbras`
- UID: `camera-dvr-monitoring`
- URL: `http://SEU_SERVIDOR_INTERNO

Visual operacional atual:

- tema claro, fundo branco;
- uma linha por equipamento;
- coluna `DVR` com bolinha de status;
- canais `C1..C32` em blocos compactos, exibindo apenas os canais reais de cada equipamento;
- segmento separado `SIA-IP` com `SIA-IP-01..05` por ICMP;
- `HD` em azul quando OK;
- atualizacao automatica a cada `1m`.

Cores:

- verde: OK;
- vermelho: falha/perda de video;
- dado ausente no Zabbix e tratado como vermelho/offline no dashboard.

O dashboard segue o mesmo layout operacional aprovado, adaptado para tema claro. Os dados exibidos vêm de consultas dinamicas ao datasource Zabbix; nao ha coleta SNMP pelo Grafana.

Versao dinamica atual:

- UID: `camera-dvr-monitoring`
- Refresh: `1m`
- Time range: ultimas `6h`

## Ajuste realtime 2026-05-28

Objetivo operacional: refletir quedas e recuperacoes em ate `5 minutos`.

Zabbix:

- Itens criticos (`dvr.online`, `dvr.hdd.status`, `dvr.channel.status[N]`, `icmpping`) ajustados para `delay=1m`.
- Itens SNMP criticos ajustados com `timeout=2s`.
- Triggers criadas/ajustadas com `nodata(5m)` para DVR, HD, canais e cameras IP.

Zabbix Proxy `zabbixProxy`:

- `ConfigFrequency=60`
- `DataSenderFrequency=1`
- `StartPollers=20`
- `StartPollersUnreachable=5`
- `StartPingers=2`
- `Timeout=3`
- `UnreachableDelay=15`
- `UnavailableDelay=30`
- `UnreachablePeriod=45`

Backups do proxy:

- `/etc/zabbix/zabbix_proxy.conf.bak-cameradvr-realtime-2026-05-28-112012`
- `/etc/zabbix/zabbix_proxy.conf.bak-cameradvr-realtime2-2026-05-28-112049`

Grafana:

- Refresh do dashboard mantido em `1m`.
- A consulta continua usando somente datasource Zabbix.
- O painel agora considera qualquer item com `lastclock` maior que `5 minutos` como `0`/offline, evitando estado verde congelado quando o SNMP para de responder.

Validacao apos ajuste:

- Hosts com SNMP respondendo atualizaram com `max_age` entre aproximadamente `34s` e `58s`.
- `GAMA 02` (`SEU_IP_PRIVADO`) nao respondeu `snmpget` a partir do proxy no teste de 2026-05-28 e por isso fica offline por stale/nodata.
- `SIA` (`SEU_IP_PRIVADO`) segue sem coleta pelo proxy e fica offline por stale/nodata.
- Painel unico em modo HTML, usando consultas dinamicas ao datasource Zabbix
- Canais C01..C32 consultam diretamente `dvr.channel.status[N]`
- Cameras SIA-IP consultam diretamente `icmpping`
- Mapeamento obrigatorio: `1 = ONLINE/OK = verde`; `0 = OFFLINE/FALHA = vermelho`
- Nodata/null nos cards de estado e tratado como OFFLINE/FALHA
- Grafana consulta apenas o datasource Zabbix; nao ha coleta SNMP direta no Grafana

O fluxo nao altera `/CAMINHO/DO/PROJETO` e nao remove dashboards existentes. O import do Grafana atualiza apenas o dashboard com UID `camera-dvr-monitoring`.
