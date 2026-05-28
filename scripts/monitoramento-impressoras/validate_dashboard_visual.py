#!/usr/bin/env python3
import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboards" / "printer-dashboard.json"
OUT = ROOT / "docs" / "mockups" / "visual-validation.json"


def main():
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    content = dashboard["panels"][0]["options"]["content"]
    cards = len(re.findall(r'<article class="printer-card', content))
    columns = 6
    rows = math.ceil(cards / columns) if columns else 0
    def css_clamp(min_value, preferred, max_value):
        return max(min_value, min(preferred, max_value))
    viewport_w, viewport_h = 1920, 1080
    available_h = viewport_h - 30
    margin = css_clamp(6, available_h * 0.006, 14)
    gap = css_clamp(7, viewport_w * 0.0045, 16)
    top_h = css_clamp(72, available_h * 0.08, 170)
    row_gap = css_clamp(6, available_h * 0.0045, 14)
    grid_h = available_h - (margin * 2) - top_h - row_gap
    card_h = (grid_h - (rows - 1) * gap) / rows
    card_w = (viewport_w - (margin * 2) - (columns - 1) * gap) / columns
    checks = {
        "cards_41": cards == 41,
        "single_screen_no_pages": "printer-page" not in content and "PÁGINA" not in content,
        "grid_6_columns": "repeat(6,minmax(0,1fr))" in content,
        "grid_7_rows": "repeat(7,minmax(0,1fr))" in content,
        "light_theme": dashboard.get("style") == "light",
        "white_background": "background:#f4f7fb" in content,
        "card_title_font_tv": "clamp(13px,.72vw,28px)" in content,
        "metric_font_tv": "clamp(36px,2.35vw,92px)" in content and "clamp(42px,2.7vw,108px)" in content,
        "no_template_variables": dashboard.get("templating") == {"list": []},
        "no_scroll_animation": "animation:scroll" not in content and "marquee" not in content,
        "no_no_data_literal": "No data" not in content,
        "math_fits_1080": rows == 7 and card_h >= 118,
    }
    geometry = {
        "viewport": "1920x1080",
        "top_height_px": top_h,
        "grid_columns": columns,
        "grid_rows": rows,
        "estimated_card_width_px": round(card_w, 2),
        "estimated_card_height_px": round(card_h, 2),
        "estimated_cards": cards,
    }
    result = {
        "ok": all(checks.values()),
        "checks": checks,
        "geometry": geometry,
        "grafana_renderer": "unavailable: Grafana returned 'No image renderer available/installed'",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
