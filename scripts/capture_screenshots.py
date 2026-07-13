"""截取 Easy Nginx 界面截图，用于公众号文章"""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = Path(__file__).resolve().parents[1] / "article" / "images"
OUT.mkdir(parents=True, exist_ok=True)

SITE_ID = "763bd705-abd6-4b6f-824d-2a545d40482b"


def shot(page, name, url, actions=None):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(url, wait_until="networkidle")
    if actions:
        actions(page)
    page.wait_for_timeout(500)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
    print(f"saved {name}.png")


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    shot(page, "01-site-list", f"{BASE}/")

    shot(page, "02-form-step1", f"{BASE}/site/new")

    def step3_actions(pg):
        pg.click("#nextStepBtn")
        pg.wait_for_timeout(300)
        pg.click("#nextStepBtn")
        pg.wait_for_timeout(300)
        pg.click("#addRuleBtn")
        pg.wait_for_timeout(300)

    shot(page, "03-forward-rules", f"{BASE}/site/{SITE_ID}/edit", step3_actions)

    def preview_actions(pg):
        pg.click("#previewBtn")
        pg.wait_for_timeout(800)

    shot(page, "04-config-preview", f"{BASE}/site/{SITE_ID}/edit", preview_actions)

    browser.close()

print("done")
