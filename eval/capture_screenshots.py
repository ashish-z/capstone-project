"""Capture Streamlit screenshots into demo_screenshots/.

Run while `streamlit run app/streamlit_app.py` is up on http://localhost:8501.

Uses Playwright + Chromium so it can wait for Streamlit's WebSocket render
to settle (plain headless `--screenshot` snapshots before content streams in).

Usage:
    PYTHONPATH=src python eval/capture_screenshots.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

_REPO = Path(__file__).resolve().parents[1]
_OUT = _REPO / "demo_screenshots"
_OUT.mkdir(exist_ok=True)

PAGES = [
    ("01-triage-console", "http://localhost:8501/", 25_000),
    ("02-monitoring", "http://localhost:8501/Monitoring", 8_000),
    ("03-sessions", "http://localhost:8501/Sessions", 8_000),
]


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 2200})
        page = ctx.new_page()

        for name, url, settle_ms in PAGES:
            print(f"→ {name} {url}")
            page.goto(url, wait_until="networkidle", timeout=60_000)
            # Streamlit renders progressively over a websocket; give it time.
            page.wait_for_timeout(settle_ms)
            out = _OUT / f"{name}.png"
            page.screenshot(path=str(out), full_page=True)
            size = out.stat().st_size
            print(f"  saved {out.relative_to(_REPO)}  ({size / 1024:.1f} KB)")

        browser.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(f"Usage: {sys.argv[0]}  (no args)")
    t0 = time.time()
    main()
    print(f"Done in {time.time() - t0:.1f}s")
