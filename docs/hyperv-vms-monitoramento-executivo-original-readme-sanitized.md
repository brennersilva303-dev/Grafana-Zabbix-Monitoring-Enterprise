# Hyper-V Hosts - Monitoramento Executivo

Projeto Grafana/Zabbix para monitoramento executivo dos hosts físicos Hyper-V `HYPERV_HOST_A` e `HYPERV-HYPERV_HOST_B`.

O dashboard não cria datasource novo, não usa IP nas queries e não inclui VMs. Os painéis técnicos são separados por host e usam somente itens confirmados em `logs/dashboard-data-validation.json`.

## Execução

```bash
cp .env.example .env
./run_all.sh
```

O fluxo executa, nesta ordem:

1. valida Grafana;
2. valida Zabbix;
3. detecta o datasource Zabbix existente;
4. descobre hosts, interfaces, grupos, itens e triggers;
5. valida quais itens têm dado real via API Zabbix, histórico Grafana ou `zabbix_get`;
6. gera e importa o dashboard mínimo;
7. testa os painéis mínimos pela API do Grafana;
8. gera e importa o dashboard completo;
9. valida renderização/dados em `logs/dashboard-render-validation.json`;
SEU_IP_PRIVADO. grava resumo e diagnóstico em `logs/`.

Dashboard:

```text
http://localhost:3000/d/hyperv-hosts-monitoramento-executivo/hyper-v-hosts-monitoramento-executivo
```

## Datasource

O datasource Zabbix detectado neste ambiente é:

```text
E2lQF-HGk
```

O projeto procura um datasource Grafana dos tipos/nome:

- `alexanderzobnin-zabbix-datasource`
- `alexanderzobnin-zabbix-app`
- nome contendo `zabbix`

Se nada for detectado, usa o valor de `ZABBIX_DATASOURCE_UID` no `.env`.

## Logs Principais

- `logs/zabbix-validation.json`: login Zabbix, hosts, interfaces e grupos.
- `logs/hyperv-items-discovery.json`: todos os itens enabled com `name`, `key_`, `itemid`, `lastvalue`, `lastclock`, `units` e `status`.
- `logs/dashboard-data-validation.json`: itens realmente utilizáveis para cada painel.
- `logs/HYPERV_HOST_A-vs-HYPERV_HOST_B-comparison.json`: comparação por key, nome, lastclock e métricas utilizáveis entre HYPERV_HOST_A e HYPERV-HYPERV_HOST_B.
- `logs/grafana-panel-data-test.json`: teste dos painéis mínimos pela API do Grafana.
- `logs/dashboard-render-validation.json`: painéis que renderizaram dados, item usado e host consultado.
- `logs/debug_no_data.log`: resumo humano para painéis sem dados.

## Como Interpretar a Validação

Em `logs/dashboard-data-validation.json`:

- `items_with_data`: quantidade de itens enabled com dado válido por API Zabbix ou `zabbix_get`.
- `selected`: item escolhido para cada painel.
- `missing`: painéis que não têm item validado.
- `items_without_data`: itens enabled que existem, mas ainda não têm histórico utilizável.

Se um item responde via `zabbix_get`, mas o Zabbix Server ainda não gravou histórico (`lastclock=0`), os painéis críticos continuam sendo `stat` com target Zabbix real e exibem o valor validado por `zabbix_get` como fallback visual. Isso mantém status, uptime e memória com leitura operacional enquanto o Zabbix Server ainda não entrega série histórica ao Grafana.

Se um painel não tiver item validado nem por API nem por `zabbix_get`, o dashboard mostra um painel de texto explicando o host, o painel afetado e o log para consultar.

## Estado Detectado

`HYPERV_HOST_A`:

- Host encontrado no Zabbix.
- Visible name: `HYPERV_HOST_A`.
- Host interno retornado pela API: `HYPERV_HOST_A`.
- Zabbix Agent clássico confirmado via `zabbix_get`: `7.4.10`.
- `agent.ping` confirmado via `zabbix_get`: `1`.
- Interface confirmada: `SEU_IP_PRIVADO:10050`.
- Itens enabled/validados no fluxo atual: 114.
- Itens com dados válidos por API ou `zabbix_get`: 116.
- Volumes detectados no painel `HYPERV_HOST_A - Todos os discos`: `C:`, `D:`, `F:`, `G:`.
- Itens validados: `Zabbix agent ping`, `Uptime`, `Used memory`, `Total memory`, `Available memory`, CPU, volumes detectados, rede de entrada/saída, interfaces detectadas e problemas/triggers.

`HYPERV-HYPERV_HOST_B`:

- Host encontrado no Zabbix.
- Interface confirmada: `SEU_IP_PRIVADO:10050`.
- Itens enabled/validados no fluxo: 98.
- Itens com dados válidos: 98.
- Volumes detectados no painel `HYPERV-HYPERV_HOST_B - Todos os discos`: `C:`, `D:`.
- Itens usados: `Uptime`, `Used memory`, `Total memory`, CPU, volumes detectados, `Bits received`, `Bits sent` e interfaces detectadas.

## CPU

O dashboard exibe apenas um painel funcional por host:

- `HYPERV_HOST_A - CPU`
- `HYPERV-HYPERV_HOST_B - CPU`

Hoje esses painéis usam os itens disponíveis do template Windows, com cálculo baseado em `CPU user time` + `CPU privileged time` quando ambos existem. O dashboard não exibe painel informativo quebrado para CPU Hyper-V ausente.

No estado atual, o Zabbix não retornou itens históricos para:

- `Hyper-V Hypervisor Logical Processor(_Total)\% Total Run Time`
- `Hyper-V Hypervisor Root Virtual Processor(_Total)\% Total Run Time`
- `Hyper-V Hypervisor Virtual Processor(_Total)\% Total Run Time`
- `Processor Information(_Total)\% Processor Time`
- `Processor(_Total)\% Processor Time`

Se quiser substituir o fallback por uma CPU mais representativa de Hyper-V, crie estes itens no Zabbix Agent e execute `./run_all.sh` depois que houver histórico:

```text
UserParameter=hyperv.cpu.logical.total,powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Counter '\Hyper-V Hypervisor Logical Processor(_Total)\% Total Run Time').CounterSamples.CookedValue"
UserParameter=hyperv.cpu.virtual.total,powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Counter '\Hyper-V Hypervisor Virtual Processor(_Total)\% Total Run Time').CounterSamples | Measure-Object CookedValue -Average | Select-Object -ExpandProperty Average"
UserParameter=windows.cpu.processor.total,powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Counter '\Processor Information(_Total)\% Processor Time').CounterSamples.CookedValue"
```

Crie itens numéricos `%` no Zabbix com essas keys, aguarde histórico e execute `./run_all.sh`.

## Rede Hyper-V

`HYPERV_HOST_A` possui itens de rede e último valor válido (`net.if.in`/`net.if.out`). O dashboard mantém os painéis de rede como time series com unidade `bps`, no mesmo padrão do `HYPERV-HYPERV_HOST_B`, e adiciona o painel `Interfaces detectadas` com os itens principais de entrada/saída.

Itens recomendados para rede:

```text
net.if.in["<nome da interface>"]
net.if.out["<nome da interface>"]
net.if.in["<nome da interface>",errors]
net.if.out["<nome da interface>",errors]
net.if.in["<nome da interface>",dropped]
net.if.out["<nome da interface>",dropped]
```

Alternativa via PowerShell/UserParameter:

```text
UserParameter=net.bytes.received[*],powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Counter '\Network Interface($1)\Bytes Received/sec').CounterSamples.CookedValue"
UserParameter=net.bytes.sent[*],powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Counter '\Network Interface($1)\Bytes Sent/sec').CounterSamples.CookedValue"
```

## Corrigir Host Sem `lastclock > 0`

Quando um item existe mas `lastclock` fica `0`, o Grafana Zabbix não terá série histórica para exibir. O projeto ainda valida o item via `zabbix_get` e mostra o valor real como painel informativo. Para transformar isso em gráfico histórico:

1. confirme se o host está enabled no Zabbix;
2. confirme se a interface está correta, por exemplo `SEU_IP_PRIVADO:10050` para `HYPERV_HOST_A`;
3. confira se os itens técnicos estão enabled;
4. force/aguarde a coleta dos itens no Zabbix;
5. confira erros em `Monitoring > Latest data` e na coluna de erro do item;
6. execute novamente `./run_all.sh`.

## Debug de Sem Dados

```bash
scripts/debug_no_data.sh
```

Também valide diretamente:

```bash
python3 scripts/discover_hyperv_items.py
python3 scripts/test_dashboard_data.py
python3 scripts/test_grafana_panel_data.py
```

O ponto mais importante é: painel técnico só é gerado com query histórica quando existe item real em `logs/dashboard-data-validation.json`. Itens validados apenas por `zabbix_get` ou somente por último valor da API aparecem como fallback visual até o Zabbix Server/Grafana entregar série histórica.

## Templates/Itens Esperados

Os hosts Windows Server/Hyper-V devem coletar:

- `agent.ping` ou disponibilidade do agente;
- `system.uptime`;
- `vm.memory.size[used]`;
- `vm.memory.size[total]`;
- `vm.memory.size[available]` ou `vm.memory.size[free]`;
- itens reais de CPU, preferencialmente Hyper-V/Processor Time se forem criados no Zabbix;
- `vfs.fs.size[*]` ou itens com `Space utilization`, `Used space`, `Total space` e `Free space`;
- interfaces com `Bits received` e `Bits sent`;
- triggers/problemas do Zabbix.

O dashboard não exibe painéis separados de CPU detalhada; quando necessário, esses itens são usados apenas como base interna para o painel simples `CPU`.
