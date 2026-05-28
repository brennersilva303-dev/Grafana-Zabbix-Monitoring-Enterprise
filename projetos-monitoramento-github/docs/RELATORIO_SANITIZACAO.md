# Relatorio de Sanitizacao

Gerado em: 2026-05-28T14:48:45

## Atualizacao de screenshots

Atualizado em: 2026-05-28T16:10:00

- Screenshots refeitos diretamente no Grafana via Chromium desktop/headless em 1920x1080.
- Nenhum screenshot foi capturado da Raspberry Pi.
- Previews/mockups antigos foram removidos do pacote final para evitar imagens quebradas ou desatualizadas.
- Dados visuais sensiveis foram borrados ou substituidos por placeholders.
- Arquivos finais:
  - images/printer-dashboard-overview.png
  - images/hyperv-hosts-overview.png
  - images/hyperv-vms-overview.png
  - images/dvr-monitoring-overview.png

## Arquivos copiados

- /root/grafana-printers/dashboards/printer-dashboard.json -> /tmp/projetos-monitoramento-github/dashboards/monitoramento-impressoras/dashboard.json
- /root/grafana-printers/scripts/backup_dashboard.sh -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/backup_dashboard.sh
- /root/grafana-printers/scripts/debug_no_data.sh -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/debug_no_data.sh
- /root/grafana-printers/scripts/detect_grafana_zabbix_datasource.py -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/detect_grafana_zabbix_datasource.py
- /root/grafana-printers/scripts/diagnose_grafana_tv_scale.py -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/diagnose_grafana_tv_scale.py
- /root/grafana-printers/scripts/diagnose_raspberry_display.sh -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/diagnose_raspberry_display.sh
- /root/grafana-printers/scripts/discover_zabbix_printers.py -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/discover_zabbix_printers.py
- /root/grafana-printers/scripts/export_dashboard.sh -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/export_dashboard.sh
- /root/grafana-printers/scripts/generate_grafana_dashboard.py -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/generate_grafana_dashboard.py
- /root/grafana-printers/scripts/import_dashboard.sh -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/import_dashboard.sh
- /root/grafana-printers/scripts/launch_grafana_tv_kiosk.sh -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/launch_grafana_tv_kiosk.sh
- /root/grafana-printers/scripts/printers_list.txt -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/printers_list.txt
- /root/grafana-printers/scripts/raspberry_inject_grafana_tv_css.py -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/raspberry_inject_grafana_tv_css.py
- /root/grafana-printers/scripts/raspberry_start_grafana_tv_fixed.sh -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/raspberry_start_grafana_tv_fixed.sh
- /root/grafana-printers/scripts/setup_raspberry_tv_kiosk.sh -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/setup_raspberry_tv_kiosk.sh
- /root/grafana-printers/scripts/setup_zabbix_printers.py -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/setup_zabbix_printers.py
- /root/grafana-printers/scripts/test_grafana_datasource.sh -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/test_grafana_datasource.sh
- /root/grafana-printers/scripts/test_zabbix_items.py -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/test_zabbix_items.py
- /root/grafana-printers/scripts/validate_dashboard_visual.py -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/validate_dashboard_visual.py
- /root/grafana-printers/scripts/validate_tv_view.sh -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/validate_tv_view.sh
- /root/grafana-printers/provisioning/alerting/printers.yaml -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/config-examples/alerting/printers.yaml
- /root/grafana-printers/provisioning/dashboards/printers.yaml -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/config-examples/dashboards/printers.yaml
- /root/grafana-printers/provisioning/datasources/zabbix.yaml -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/config-examples/datasources/zabbix.yaml
- /root/grafana-printers/provisioning/printer-alerts.yaml -> /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/config-examples/printer-alerts.yaml
- /root/grafana-printers/README.md -> /tmp/projetos-monitoramento-github/docs/monitoramento-impressoras-original-readme-sanitized.md
- Screenshot real capturado do Grafana -> /tmp/projetos-monitoramento-github/images/printer-dashboard-overview.png
- /root/grafana-hyperv/dashboard-hyperv-hosts-v2.json -> /tmp/projetos-monitoramento-github/dashboards/hyperv-hosts-monitoramento-executivo-v2/dashboard.json
- /root/grafana-hyperv/scripts/collect_hyperv_vm_metrics.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/collect_hyperv_vm_metrics.py
- /root/grafana-hyperv/scripts/debug_no_data.sh -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/debug_no_data.sh
- /root/grafana-hyperv/scripts/discover_hyperv_items.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/discover_hyperv_items.py
- /root/grafana-hyperv/scripts/discover_hyperv_vms.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/discover_hyperv_vms.py
- /root/grafana-hyperv/scripts/generate_hyperv_dashboard.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/generate_hyperv_dashboard.py
- /root/grafana-hyperv/scripts/generate_hyperv_dashboard_review.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/generate_hyperv_dashboard_review.py
- /root/grafana-hyperv/scripts/generate_hyperv_dashboard_v2.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/generate_hyperv_dashboard_v2.py
- /root/grafana-hyperv/scripts/generate_hyperv_vms_dashboard.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/generate_hyperv_vms_dashboard.py
- /root/grafana-hyperv/scripts/import_dashboard.sh -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/import_dashboard.sh
- /root/grafana-hyperv/scripts/import_dashboard_json.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/import_dashboard_json.py
- /root/grafana-hyperv/scripts/import_hyperv_vms_dashboard.sh -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/import_hyperv_vms_dashboard.sh
- /root/grafana-hyperv/scripts/test_dashboard_data.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/test_dashboard_data.py
- /root/grafana-hyperv/scripts/test_grafana_panel_data.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/test_grafana_panel_data.py
- /root/grafana-hyperv/scripts/test_zabbix_hyperv_hosts.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/test_zabbix_hyperv_hosts.py
- /root/grafana-hyperv/scripts/update_operational_dashboards.sh -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/update_operational_dashboards.sh
- /root/grafana-hyperv/.grafana/provisioning/dashboards/local-dashboard.yml -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/config-examples/dashboards/local-dashboard.yml
- /root/grafana-hyperv/.grafana/provisioning/datasources/local-zabbix.yml -> /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/config-examples/datasources/local-zabbix.yml
- /root/grafana-hyperv/README.md -> /tmp/projetos-monitoramento-github/docs/hyperv-hosts-monitoramento-executivo-v2-original-readme-sanitized.md
- Screenshot real capturado do Grafana -> /tmp/projetos-monitoramento-github/images/hyperv-hosts-overview.png
- /opt/CameraDVR/dashboards/camera-dvr-dashboard.json -> /tmp/projetos-monitoramento-github/dashboards/monitoramento-dvr-intelbras/dashboard.json
- /opt/CameraDVR/scripts/discover_zabbix_dvrs.py -> /tmp/projetos-monitoramento-github/scripts/monitoramento-dvr-intelbras/discover_zabbix_dvrs.py
- /opt/CameraDVR/scripts/generate_grafana_dashboard.py -> /tmp/projetos-monitoramento-github/scripts/monitoramento-dvr-intelbras/generate_grafana_dashboard.py
- /opt/CameraDVR/scripts/import_dashboard.sh -> /tmp/projetos-monitoramento-github/scripts/monitoramento-dvr-intelbras/import_dashboard.sh
- /opt/CameraDVR/scripts/setup_zabbix_dvrs.py -> /tmp/projetos-monitoramento-github/scripts/monitoramento-dvr-intelbras/setup_zabbix_dvrs.py
- /opt/CameraDVR/scripts/snmp_discover_dvr.sh -> /tmp/projetos-monitoramento-github/scripts/monitoramento-dvr-intelbras/snmp_discover_dvr.sh
- /opt/CameraDVR/config/oids_intelbras_imhdx3116.json -> /tmp/projetos-monitoramento-github/scripts/monitoramento-dvr-intelbras/config-examples/oids_intelbras_imhdx3116.json
- /opt/CameraDVR/README.md -> /tmp/projetos-monitoramento-github/docs/monitoramento-dvr-intelbras-original-readme-sanitized.md
- /root/grafana-hyperv/dashboard-hyperv-vms.json -> /tmp/projetos-monitoramento-github/dashboards/hyperv-vms-monitoramento-executivo/dashboard.json
- /root/grafana-hyperv/scripts/collect_hyperv_vm_metrics.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/collect_hyperv_vm_metrics.py
- /root/grafana-hyperv/scripts/debug_no_data.sh -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/debug_no_data.sh
- /root/grafana-hyperv/scripts/discover_hyperv_items.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/discover_hyperv_items.py
- /root/grafana-hyperv/scripts/discover_hyperv_vms.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/discover_hyperv_vms.py
- /root/grafana-hyperv/scripts/generate_hyperv_dashboard.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/generate_hyperv_dashboard.py
- /root/grafana-hyperv/scripts/generate_hyperv_dashboard_review.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/generate_hyperv_dashboard_review.py
- /root/grafana-hyperv/scripts/generate_hyperv_dashboard_v2.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/generate_hyperv_dashboard_v2.py
- /root/grafana-hyperv/scripts/generate_hyperv_vms_dashboard.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/generate_hyperv_vms_dashboard.py
- /root/grafana-hyperv/scripts/import_dashboard.sh -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/import_dashboard.sh
- /root/grafana-hyperv/scripts/import_dashboard_json.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/import_dashboard_json.py
- /root/grafana-hyperv/scripts/import_hyperv_vms_dashboard.sh -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/import_hyperv_vms_dashboard.sh
- /root/grafana-hyperv/scripts/test_dashboard_data.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/test_dashboard_data.py
- /root/grafana-hyperv/scripts/test_grafana_panel_data.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/test_grafana_panel_data.py
- /root/grafana-hyperv/scripts/test_zabbix_hyperv_hosts.py -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/test_zabbix_hyperv_hosts.py
- /root/grafana-hyperv/scripts/update_operational_dashboards.sh -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/update_operational_dashboards.sh
- /root/grafana-hyperv/.grafana/provisioning/dashboards/local-dashboard.yml -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/config-examples/dashboards/local-dashboard.yml
- /root/grafana-hyperv/.grafana/provisioning/datasources/local-zabbix.yml -> /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/config-examples/datasources/local-zabbix.yml
- /root/grafana-hyperv/README.md -> /tmp/projetos-monitoramento-github/docs/hyperv-vms-monitoramento-executivo-original-readme-sanitized.md
- Screenshot real capturado do Grafana -> /tmp/projetos-monitoramento-github/images/hyperv-vms-overview.png
- Screenshot real capturado do Grafana -> /tmp/projetos-monitoramento-github/images/dvr-monitoring-overview.png

## Arquivos/itens ignorados

- .env reais das origens
- logs/
- backup/
- backups/
- cookies/
- sessions/
- tokens/
- arquivos .bak/.old/.log

## Arquivos sanitizados

- /tmp/projetos-monitoramento-github/dashboards/hyperv-hosts-monitoramento-executivo-v2/dashboard.json
- /tmp/projetos-monitoramento-github/dashboards/hyperv-vms-monitoramento-executivo/dashboard.json
- /tmp/projetos-monitoramento-github/dashboards/monitoramento-dvr-intelbras/dashboard.json
- /tmp/projetos-monitoramento-github/dashboards/monitoramento-impressoras/dashboard.json
- /tmp/projetos-monitoramento-github/docs/hyperv-hosts-monitoramento-executivo-v2-original-readme-sanitized.md
- /tmp/projetos-monitoramento-github/docs/hyperv-vms-monitoramento-executivo-original-readme-sanitized.md
- /tmp/projetos-monitoramento-github/docs/monitoramento-dvr-intelbras-original-readme-sanitized.md
- /tmp/projetos-monitoramento-github/docs/monitoramento-impressoras-original-readme-sanitized.md
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/collect_hyperv_vm_metrics.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/config-examples/dashboards/local-dashboard.yml
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/config-examples/datasources/local-zabbix.yml
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/debug_no_data.sh
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/discover_hyperv_items.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/discover_hyperv_vms.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/generate_hyperv_dashboard.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/generate_hyperv_dashboard_review.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/generate_hyperv_dashboard_v2.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/generate_hyperv_vms_dashboard.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/import_dashboard.sh
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/import_dashboard_json.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/import_hyperv_vms_dashboard.sh
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/test_dashboard_data.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/test_grafana_panel_data.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/test_zabbix_hyperv_hosts.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-hosts-monitoramento-executivo-v2/update_operational_dashboards.sh
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/collect_hyperv_vm_metrics.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/config-examples/dashboards/local-dashboard.yml
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/config-examples/datasources/local-zabbix.yml
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/debug_no_data.sh
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/discover_hyperv_items.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/discover_hyperv_vms.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/generate_hyperv_dashboard.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/generate_hyperv_dashboard_review.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/generate_hyperv_dashboard_v2.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/generate_hyperv_vms_dashboard.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/import_dashboard.sh
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/import_dashboard_json.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/import_hyperv_vms_dashboard.sh
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/test_dashboard_data.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/test_grafana_panel_data.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/test_zabbix_hyperv_hosts.py
- /tmp/projetos-monitoramento-github/scripts/hyperv-vms-monitoramento-executivo/update_operational_dashboards.sh
- /tmp/projetos-monitoramento-github/scripts/monitoramento-dvr-intelbras/config-examples/oids_intelbras_imhdx3116.json
- /tmp/projetos-monitoramento-github/scripts/monitoramento-dvr-intelbras/discover_zabbix_dvrs.py
- /tmp/projetos-monitoramento-github/scripts/monitoramento-dvr-intelbras/generate_grafana_dashboard.py
- /tmp/projetos-monitoramento-github/scripts/monitoramento-dvr-intelbras/setup_zabbix_dvrs.py
- /tmp/projetos-monitoramento-github/scripts/monitoramento-dvr-intelbras/snmp_discover_dvr.sh
- /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/config-examples/datasources/zabbix.yaml
- /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/debug_no_data.sh
- /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/detect_grafana_zabbix_datasource.py
- /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/diagnose_grafana_tv_scale.py
- /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/discover_zabbix_printers.py
- /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/generate_grafana_dashboard.py
- /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/printers_list.txt
- /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/raspberry_start_grafana_tv_fixed.sh
- /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/setup_zabbix_printers.py
- /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/test_grafana_datasource.sh
- /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/test_zabbix_items.py
- /tmp/projetos-monitoramento-github/scripts/monitoramento-impressoras/validate_tv_view.sh

## Segredos removidos ou substituidos

- IPs privados reais substituidos por `SEU_IP_PRIVADO` ou `http://SEU_SERVIDOR_INTERNO`.
- Usuarios reais substituidos por `SEU_USUARIO` ou `SEU_USUARIO_LINUX`.
- Senhas/tokens/secrets substituidos por placeholders.
- Dashboards tiveram `id`, `uid`, `version` e datasource fixo removidos/substituidos por `DS_ZABBIX`.
- `.env`, logs, backups, cookies, sessoes e tokens nao foram copiados.

## Placeholders criados

- CAMINHO/DO/PROJETO
- DS_ZABBIX
- HYPERV_HOST_A
- HYPERV_HOST_B
- SEU_GRAFANA
- SEU_IP_PRIVADO
- SEU_SERVIDOR_INTERNO
- SEU_TOKEN
- SEU_USUARIO
- SEU_ZABBIX
- SUA_SENHA

## Itens que o usuario precisa editar antes de usar

- `.env.example`: copiar para `.env` e preencher Grafana/Zabbix.
- `datasource.example.yml`: ajustar datasource Zabbix real.
- `config.example.yml`: ajustar URLs, usuarios, senha e playlist.
- Dashboards: selecionar o datasource `DS_ZABBIX` durante a importacao.
- Scripts de Raspberry kiosk: revisar comentarios `EDITE AQUI` e preencher URL propria do Grafana/playlist.

## Validacao final

PASSOU: nenhum IP privado real, usuario real ou segredo atribuido foi encontrado.

Detalhes em `docs/VALIDACAO_SENSIVE_SCAN.txt`.

## Observacoes

- Pasta anterior movida para /tmp/projetos-monitoramento-github-old-20260528-144843
- Screenshots seguros disponiveis para os quatro dashboards oficiais.

## Publicacao no compartilhamento

- O pacote compactado foi enviado com sucesso para o compartilhamento SMB definido pelo mantenedor.
- A pasta expandida `projetos-monitoramento-github/` nao pode ser criada por este host porque nao ha `smbclient`/`mount.cifs`, `gio` nao suporta SMB aqui, e o `curl` SMB disponivel faz upload de arquivos mas nao cria diretorios remotos.
- Para obter a pasta final no compartilhamento, extraia `projetos-monitoramento-github.tar.gz` no destino.
- Nenhum projeto original foi alterado.


## Atualizacao de imagens

- Screenshots antigos/previews foram removidos do pacote final e nao sao referenciados pelo README.
- Foram gerados screenshots PNG reais e sanitizados em `images/` para os quatro dashboards oficiais.
- As imagens foram capturadas diretamente no Grafana em Chromium desktop/headless 1920x1080, sem abrir a Raspberry.

## Atualizacao adicional de imagens

- Screenshots brutos anteriores foram removidos do pacote para evitar dados sensiveis embutidos em pixels.
- O README agora referencia apenas quatro screenshots reais sanitizados em `images/`, um para cada dashboard oficial.
