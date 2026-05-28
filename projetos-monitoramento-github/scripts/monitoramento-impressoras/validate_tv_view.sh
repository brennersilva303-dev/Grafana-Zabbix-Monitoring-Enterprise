#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
SHOT_DIR="${ROOT_DIR}/docs/mockups/validation"
mkdir -p "$LOG_DIR" "$SHOT_DIR"

set -a
source "${ROOT_DIR}/.env"
set +a

: "${GRAFANA_URL:?Defina GRAFANA_URL no .env}"
: "${GRAFANA_USER:?Defina GRAFANA_USER no .env}"
: "${GRAFANA_PASSWORD:?Defina GRAFANA_PASSWORD no .env}"

export ROOT_DIR LOG_DIR SHOT_DIR GRAFANA_URL GRAFANA_USER GRAFANA_PASSWORD
export CHROMIUM_BIN="${CHROMIUM_BIN:-/usr/bin/chromium-browser}"
export CHROMEDRIVER_BIN="${CHROMEDRIVER_BIN:-/usr/bin/chromedriver}"

python3 <<'PY'
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(os.environ["ROOT_DIR"])
LOG = Path(os.environ["LOG_DIR"]) / "tv_validation.log"
SHOT_DIR = Path(os.environ["SHOT_DIR"])
BASE = os.environ["GRAFANA_URL"].rstrip("/")
USER = os.environ["GRAFANA_USER"]
PASSWORD = SUA_SENHA
CHROMIUM = os.environ["CHROMIUM_BIN"]
CHROMEDRIVER = os.environ["CHROMEDRIVER_BIN"]
DASHBOARD = "/d/printer-monitoring/monitoramento-de-impressoras"
STAMP = datetime.now().strftime("%Y-%m-%d-%H%M%S")


def write(line=""):
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def driver_for(width=1920, height=1080, scale=1):
    opts = Options()
    opts.binary_location = CHROMIUM
    for arg in [
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        "--start-fullscreen",
        "--disable-infobars",
        "--disable-pinch",
        "--overscroll-history-navigation=0",
        "--force-device-scale-factor=1",
        "--high-dpi-support=1",
        "--window-position=0,0",
        f"--window-size={width},{height}",
    ]:
        opts.add_argument(arg)
    driver = webdriver.Chrome(executable_path=CHROMEDRIVER, options=opts)
    driver.set_window_size(width, height)
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": width,
        "height": height,
        "deviceScaleFactor": scale,
        "mobile": False,
        "screenWidth": width,
        "screenHeight": height,
        "positionX": 0,
        "positionY": 0,
        "dontSetVisibleSize": False,
    })
    return driver


def login(driver):
    driver.get(BASE + "/login")
    wait = WebDriverWait(driver, 25)
    wait.until(EC.presence_of_element_located((By.NAME, "user"))).send_keys(USER)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    time.sleep(2)


def measure(driver):
    return driver.execute_script(
        """
        const cards = Array.from(document.querySelectorAll('.printer-card'));
        const grid = document.querySelector('.grid-printers');
        const noc = document.querySelector('.noc-printers');
        function rect(el) {
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return {
            x: Math.round(r.x * 100) / 100,
            y: Math.round(r.y * 100) / 100,
            width: Math.round(r.width * 100) / 100,
            height: Math.round(r.height * 100) / 100,
            right: Math.round(r.right * 100) / 100,
            bottom: Math.round(r.bottom * 100) / 100
          };
        }
        const cardRects = cards.map((card, index) => {
          const r = card.getBoundingClientRect();
          return {
            index: index + 1,
            name: (card.querySelector('.line-top strong') || {}).textContent || '',
            x: Math.round(r.x * 100) / 100,
            y: Math.round(r.y * 100) / 100,
            width: Math.round(r.width * 100) / 100,
            height: Math.round(r.height * 100) / 100,
            right: Math.round(r.right * 100) / 100,
            bottom: Math.round(r.bottom * 100) / 100,
            visible: r.top >= -1 && r.left >= -1 && r.bottom <= window.innerHeight + 1 && r.right <= window.innerWidth + 1
          };
        });
        const hidden = cardRects.filter(c => !c.visible);
        const hasPages = document.body.innerText.match(/P[ÁA]GINA\\s+\\d+\\s*\\/\\s*\\d+|page\\s+\\d+\\s*\\/\\s*\\d+/i);
        const doc = document.documentElement;
        const body = document.body;
        return {
          url: location.href,
          title: document.title,
          innerWidth: window.innerWidth,
          innerHeight: window.innerHeight,
          outerWidth: window.outerWidth,
          outerHeight: window.outerHeight,
          devicePixelRatio: window.devicePixelRatio,
          visualViewport: window.visualViewport ? {
            width: window.visualViewport.width,
            height: window.visualViewport.height,
            scale: window.visualViewport.scale
          } : null,
          screen: {
            width: screen.width,
            height: screen.height,
            availWidth: screen.availWidth,
            availHeight: screen.availHeight
          },
          document: {
            clientWidth: doc.clientWidth,
            clientHeight: doc.clientHeight,
            scrollWidth: doc.scrollWidth,
            scrollHeight: doc.scrollHeight,
            bodyScrollWidth: body.scrollWidth,
            bodyScrollHeight: body.scrollHeight
          },
          cardsTotal: cards.length,
          cardsVisible: cardRects.filter(c => c.visible).length,
          hiddenCards: hidden,
          gridRect: rect(grid),
          nocRect: rect(noc),
          maxCardBottom: cardRects.length ? Math.max(...cardRects.map(c => c.bottom)) : 0,
          maxCardRight: cardRects.length ? Math.max(...cardRects.map(c => c.right)) : 0,
          minCardHeight: cardRects.length ? Math.min(...cardRects.map(c => c.height)) : 0,
          minCardWidth: cardRects.length ? Math.min(...cardRects.map(c => c.width)) : 0,
          hasVerticalScroll: doc.scrollHeight > window.innerHeight + 1 || body.scrollHeight > window.innerHeight + 1,
          hasHorizontalScroll: doc.scrollWidth > window.innerWidth + 1 || body.scrollWidth > window.innerWidth + 1,
          hasPaginationText: !!hasPages,
          hasNoDataText: document.body.innerText.includes('No data'),
          hasGrafanaMenu: !!document.querySelector('[aria-label="Toggle menu"], .sidemenu, .navbar-page-btn'),
          bodyTextSample: document.body.innerText.slice(0, 500)
        };
        """
    )


def validate(data):
    checks = {
        "viewport_1920x1080": data["innerWidth"] == 1920 and data["innerHeight"] == 1080,
        "device_pixel_ratio_1": data["devicePixelRatio"] == 1,
        "cards_41": data["cardsTotal"] == 41,
        "visible_41": data["cardsVisible"] == 41,
        "no_hidden_cards": len(data["hiddenCards"]) == 0,
        "no_vertical_scroll": not data["hasVerticalScroll"],
        "no_horizontal_scroll": not data["hasHorizontalScroll"],
        "no_pagination": not data["hasPaginationText"],
        "no_no_data": not data["hasNoDataText"],
        "all_cards_inside_height": data["maxCardBottom"] <= data["innerHeight"] + 1,
        "all_cards_inside_width": data["maxCardRight"] <= data["innerWidth"] + 1,
    }
    return checks, all(checks.values())


def run_case(name, query, screenshot_name):
    driver = driver_for()
    try:
        login(driver)
        url = f"{BASE}{DASHBOARD}?orgId=1&refresh=1m{query}"
        driver.get(url)
        time.sleep(5)
        data = measure(driver)
        checks, ok = validate(data)
        png = SHOT_DIR / f"{STAMP}-{screenshot_name}.png"
        json_path = SHOT_DIR / f"{STAMP}-{screenshot_name}.json"
        driver.save_screenshot(str(png))
        payload = {
            "case": name,
            "status": "APROVADO" if ok else "REPROVADO",
            "checks": checks,
            "metrics": data,
            "screenshot": str(png),
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        write(f"== {name}: {'APROVADO' if ok else 'REPROVADO'} ==")
        write(json.dumps({
            "viewport": f"{data['innerWidth']}x{data['innerHeight']}",
            "dpr": data["devicePixelRatio"],
            "cards": f"{data['cardsVisible']}/{data['cardsTotal']}",
            "scrollV": data["hasVerticalScroll"],
            "scrollH": data["hasHorizontalScroll"],
            "maxBottom": data["maxCardBottom"],
            "maxRight": data["maxCardRight"],
            "screenshot": str(png),
            "failed": [k for k, v in checks.items() if not v],
        }, indent=2, ensure_ascii=False))
        return payload
    finally:
        driver.quit()


def main():
    LOG.write_text(f"Validacao TV iniciada: {datetime.now().isoformat()}\n", encoding="utf-8")
    write(f"Dashboard base: {BASE}{DASHBOARD}")
    cases = [
        ("ANTES_normal", "", "before-normal"),
        ("DURANTE_kiosk_tv", "&kiosk=tv", "during-kiosktv"),
        ("FINAL_kiosk", "&kiosk", "after-kiosk"),
    ]
    results = [run_case(*case) for case in cases]
    final = results[-1]
    summary = {
        "final_status": final["status"],
        "final_screenshot": final["screenshot"],
        "final_checks": final["checks"],
        "final_metrics": {
            "viewport": f"{final['metrics']['innerWidth']}x{final['metrics']['innerHeight']}",
            "devicePixelRatio": final["metrics"]["devicePixelRatio"],
            "cards": f"{final['metrics']['cardsVisible']}/{final['metrics']['cardsTotal']}",
            "maxCardBottom": final["metrics"]["maxCardBottom"],
            "maxCardRight": final["metrics"]["maxCardRight"],
            "scrollHeight": final["metrics"]["document"]["scrollHeight"],
            "scrollWidth": final["metrics"]["document"]["scrollWidth"],
        }
    }
    write("== RESUMO FINAL ==")
    write(json.dumps(summary, indent=2, ensure_ascii=False))
    if final["status"] != "APROVADO":
        write("VALIDACAO FINAL REPROVADA")
        sys.exit(1)
    write("VALIDACAO FINAL APROVADA: 41/41 cards visiveis dentro do viewport 1920x1080")


if __name__ == "__main__":
    main()
PY
