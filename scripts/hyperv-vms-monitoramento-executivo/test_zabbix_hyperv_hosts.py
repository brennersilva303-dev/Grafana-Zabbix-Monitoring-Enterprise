#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERRO: biblioteca requests nao instalada. Execute ./run_all.sh", file=sys.stderr)
    sys.exit(2)

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
HOSTS = ["HYPERV_HOST_A", "HYPERV-HYPERV_HOST_B"]


class Zabbix:
    def __init__(self):
        load_dotenv(ROOT / ".env")
        self.url = os.getenv("ZABBIX_URL", "http://SEU_SERVIDOR_INTERNO")
        self.user = os.getenv("ZABBIX_USER", "SEU_USUARIO")
        self.password = os.getenv("ZABBIX_PASSWORD", "SUA_SENHA")
        self.auth = None
        self.req_id = 0

    def call(self, method, params=None, auth=True):
        self.req_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.req_id,
        }
        if auth and self.auth:
            payload["auth"] = self.auth
        response = requests.post(self.url, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(f"{method}: {data['error']}")
        return data["result"]

    def login(self):
        self.auth = self.call("user.login", {"user": self.user, "password": self.password}, auth=False)
        return self.auth


def find_host(zbx, wanted):
    exact = zbx.call(
        "host.get",
        {
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["ip", "dns", "useip", "type", "port"],
            "selectGroups": ["name"],
            "filter": {"host": [wanted]},
        },
    )
    if exact:
        return exact[0]
    candidates = []
    for field in ("host", "name"):
        candidates.extend(
            zbx.call(
                "host.get",
                {
                    "output": ["hostid", "host", "name", "status"],
                    "selectInterfaces": ["ip", "dns", "useip", "type", "port"],
                    "selectGroups": ["name"],
                    "search": {field: wanted},
                    "searchWildcardsEnabled": True,
                },
            )
        )
    wanted_l = wanted.lower()
    for host in candidates:
        if host.get("host", "").lower() == wanted_l or host.get("name", "").lower() == wanted_l:
            return host
    return candidates[0] if candidates else None


def main():
    LOGS.mkdir(exist_ok=True)
    zbx = Zabbix()
    result = {
        "zabbix_url": zbx.url,
        "api_version": None,
        "login_ok": False,
        "hosts": {},
        "errors": [],
    }

    try:
        result["api_version"] = zbx.call("apiinfo.version", auth=False)
        zbx.login()
        result["login_ok"] = True

        for host in HOSTS:
            matched = find_host(zbx, host)
            if not matched:
                result["hosts"][host] = {"found": False, "items": 0, "triggers": 0}
                result["errors"].append(f"Host nao encontrado no Zabbix: {host}")
                continue
            hostid = matched["hostid"]
            items = zbx.call("item.get", {"output": ["itemid"], "hostids": [hostid]})
            triggers = zbx.call(
                "trigger.get",
                {
                    "output": ["triggerid"],
                    "hostids": [hostid],
                    "filter": {"status": 0},
                },
            )
            result["hosts"][host] = {
                "found": True,
                "hostid": hostid,
                "zabbix_host": matched.get("host"),
                "zabbix_name": matched.get("name"),
                "interfaces": matched.get("interfaces", []),
                "groups": matched.get("groups", []),
                "items": len(items),
                "triggers": len(triggers),
            }
    except Exception as exc:
        result["errors"].append(str(exc))

    (LOGS / "zabbix-validation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["login_ok"] and all(result["hosts"].get(h, {}).get("found") for h in HOSTS) else 1


if __name__ == "__main__":
    sys.exit(main())
