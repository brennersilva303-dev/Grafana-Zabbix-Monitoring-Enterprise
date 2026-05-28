#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "mockups"
REPORT = OUT / "grafana-tv-scale-report.json"
DASHBOARD_PATH = "/d/printer-monitoring/monitoramento-de-impressoras"


def env(name, default=""):
    return os.getenv(name, default).strip()


def chrome_driver(width, height, scale):
    opts = Options()
    opts.binary_location = env("CHROMIUM_BIN", "/usr/bin/chromium-browser")
    args = [
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        "--start-fullscreen",
        f"--window-size={width},{height}",
        f"--force-device-scale-factor={scale}",
    ]
    for arg in args:
        opts.add_argument(arg)
    return webdriver.Chrome(executable_path=env("CHROMEDRIVER_BIN", "/usr/bin/chromedriver"), options=opts)


def login(driver, base_url):
    user = env("GRAFANA_USER")
    password = env("GRAFANA_PASSWORD")
    if not user or not password:
        raise RuntimeError("GRAFANA_USER/GRAFANA_PASSWORD nao definidos no .env")
    driver.get(base_url + "/login")
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.NAME, "user"))).send_keys(user)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
    time.sleep(2)


def metrics(driver):
    return driver.execute_script(
        """
        const noc = document.querySelector('.noc-printers');
        const grid = document.querySelector('.grid-printers');
        const cards = Array.from(document.querySelectorAll('.printer-card'));
        const cardRects = cards.map(c => c.getBoundingClientRect());
        const body = document.body;
        const doc = document.documentElement;
        function rect(el) {
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return {x:r.x, y:r.y, width:r.width, height:r.height, bottom:r.bottom, right:r.right};
        }
        const minCard = cardRects.length ? {
          width: Math.min(...cardRects.map(r => r.width)),
          height: Math.min(...cardRects.map(r => r.height))
        } : {width:0, height:0};
        const maxBottom = cardRects.length ? Math.max(...cardRects.map(r => r.bottom)) : 0;
        return {
          url: location.href,
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
          nocRect: rect(noc),
          gridRect: rect(grid),
          cards: cards.length,
          minCard,
          maxCardBottom: maxBottom,
          viewportFillPercent: grid ? Math.round((grid.getBoundingClientRect().height / window.innerHeight) * 10000) / 100 : 0,
          hasVerticalOverflow: doc.scrollHeight > window.innerHeight + 2,
          hasHorizontalOverflow: doc.scrollWidth > window.innerWidth + 2
        };
        """
    )


def run_case(base_url, width, height, scale, kiosk):
    suffix = f"{width}x{height}-scale{str(scale).replace('.', '_')}-{kiosk}"
    url = f"{base_url}{DASHBOARD_PATH}?orgId=1&refresh=1m"
    if kiosk == "kiosk":
        url += "&kiosk"
    elif kiosk == "kiosktv":
        url += "&kiosk=tv"
    png = OUT / f"printer-dashboard-scale-{suffix}.png"
    driver = chrome_driver(width, height, scale)
    try:
        login(driver, base_url)
        driver.get(url)
        time.sleep(4)
        data = metrics(driver)
        data["requestedWindow"] = {"width": width, "height": height, "scale": scale, "kiosk": kiosk}
        data["screenshot"] = str(png)
        data["recommended"] = (
            data["cards"] == 41
            and not data["hasVerticalOverflow"]
            and data["viewportFillPercent"] >= 80
            and data["devicePixelRatio"] in (1, 1.0)
            and kiosk == "kiosk"
        )
        driver.save_screenshot(str(png))
        return data
    finally:
        driver.quit()


def main():
    load_dotenv(ROOT / ".env")
    OUT.mkdir(parents=True, exist_ok=True)
    base_url = env("GRAFANA_URL", "http://SEU_SERVIDOR_INTERNO").rstrip("/")
    cases = [
        (1920, 1080, 1, "normal"),
        (1920, 1080, 1, "kiosktv"),
        (1920, 1080, 1, "kiosk"),
        (1920, 1080, 1.25, "kiosk"),
        (1920, 1080, 1.5, "kiosk"),
        (3840, 2160, 1, "kiosk"),
    ]
    results = [run_case(base_url, *case) for case in cases]
    REPORT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"Relatorio: {REPORT}")


if __name__ == "__main__":
    main()
