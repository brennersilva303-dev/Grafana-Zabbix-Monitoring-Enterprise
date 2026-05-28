#!/usr/bin/env python3
import configparser
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
OUT = ROOT / "dashboards" / "zabbix-datasource.json"
load_dotenv(ENV)

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000").rstrip("/")
TOKEN = SEU_TOKEN
USER = os.getenv("GRAFANA_USER", "SEU_USUARIO")
PASSWORD = SUA_SENHA
ZABBIX_TYPES = {"alexanderzobnin-zabbix-datasource", "alexanderzobnin-zabbix-app", "zabbix"}


def session():
    sess = requests.Session()
    if TOKEN:
        sess.headers.update({"Authorization": f"Bearer {TOKEN}"})
    else:
        sess.auth = (USER, PASSWORD)
    return sess


def from_api():
    sess = session()
    response = sess.get(f"{GRAFANA_URL}/api/datasources", timeout=20)
    response.raise_for_status()
    datasources = response.json()
    candidates = []
    for ds in datasources:
        ds_type = (ds.get("type") or "").lower()
        name = (ds.get("name") or "").lower()
        url = (ds.get("url") or "").lower()
        if ds_type in ZABBIX_TYPES or "zabbix" in ds_type or "zabbix" in name or "zabbix" in url:
            candidates.append(ds)
    if not candidates:
        raise RuntimeError("Nenhum datasource Zabbix encontrado na API do Grafana")
    candidates.sort(key=lambda item: 0 if "zabbix" in (item.get("type") or "").lower() else 1)
    return candidates[0], "grafana_api"


def from_provisioning():
    roots = [
        Path("/etc/grafana/provisioning/datasources"),
        ROOT / "provisioning",
        ROOT / "provisioning" / "datasources",
    ]
    pattern = re.compile(r"^\s*(name|uid|type|url):\s*[\"']?([^\"'\n#]+)", re.I | re.M)
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.y*ml")):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "zabbix" not in text.lower():
                continue
            found = {}
            for key, value in pattern.findall(text):
                found[key.lower()] = value.strip()
            if found:
                return {
                    "name": found.get("name", "Zabbix"),
                    "uid": found.get("uid", "zabbix"),
                    "url": found.get("url", ""),
                    "type": found.get("type", "alexanderzobnin-zabbix-datasource"),
                }, f"provisioning:{path}"
    raise RuntimeError("Nenhum datasource Zabbix encontrado em arquivos de provisioning")


def append_env(info):
    lines = ENV.read_text(encoding="utf-8").splitlines()
    drop = {
        "GRAFANA_DATASOURCE_NAME",
        "GRAFANA_DATASOURCE_UID",
        "GRAFANA_DATASOURCE_URL",
        "GRAFANA_DATASOURCE_TYPE",
    }
    kept = [line for line in lines if line.split("=", 1)[0] not in drop]
    def quote(value):
        value = str(value or "").replace("'", "'\\''")
        return f"'{value}'"
    kept.extend(
        [
            f"GRAFANA_DATASOURCE_NAME={quote(info.get('name'))}",
            f"GRAFANA_DATASOURCE_UID={quote(info.get('uid'))}",
            f"GRAFANA_DATASOURCE_URL={quote(info.get('url'))}",
            f"GRAFANA_DATASOURCE_TYPE={quote(info.get('type'))}",
        ]
    )
    ENV.write_text("\n".join(kept) + "\n", encoding="utf-8")
    os.chmod(ENV, 0o600)


def main():
    try:
        try:
            info, source = from_api()
        except Exception as api_error:
            print(f"Aviso: API do Grafana indisponivel ou sem permissao: {api_error}", file=sys.stderr)
            info, source = from_provisioning()

        result = {
            "name": info.get("name"),
            "uid": info.get("uid"),
            "url": info.get("url"),
            "type": info.get("type"),
            "source": source,
        }
        if not result["uid"]:
            raise RuntimeError("Datasource Zabbix detectado sem UID")
        OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        append_env(result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"Erro ao detectar datasource Zabbix: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
