#!/usr/bin/env python3
"""
Interactive App Capture — Manual Navigation Mode
=================================================
Opens the AU Post Shopify app in Chrome (visible), waits for you to
navigate to each section manually, then captures the content on demand.

Usage:
    source .venv/bin/activate
    python -m ingest.interactive_capture

At each prompt:
  - Navigate to the section you want to capture
  - Expand any panels or settings you want included
  - Press ENTER to capture
  - Type 's' + ENTER to skip
  - Type 'q' + ENTER to quit and save what's been captured so far
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path

import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

STORE    = os.getenv("STORE", "")
APP_SLUG = os.getenv("AUPOST_APP_SLUG", "australia-post-rates-labels")
BASE_URL = f"https://admin.shopify.com/store/{STORE}/apps/{APP_SLUG}" if STORE else ""
AUTH_JSON = Path(config.AUTOMATION_CODEBASE_PATH) / "auth.json"

# Sections to capture — label shown at prompt, metadata name for the doc
CAPTURE_TARGETS = [
    {"label": "Settings → Account Settings (expand to show fields)",
     "name": "Settings — Account Settings (eParcel / MyPost Business)"},
    {"label": "Settings → Packages (show packing method, dimensions fields)",
     "name": "Settings — Packages Configuration"},
    {"label": "Settings → Additional Services (Signature, ATL, Extra Cover, Safe Drop, Dangerous Goods)",
     "name": "Settings — Additional Services"},
    {"label": "Settings → Rate Settings (services, markup, display options)",
     "name": "Settings — Rate Settings"},
    {"label": "Settings → Print Settings (label format, size)",
     "name": "Settings — Print Settings"},
    {"label": "Settings → Notifications",
     "name": "Settings — Notifications"},
    {"label": "Shipping Orders page (/shopify) — All Orders grid",
     "name": "Shipping Orders Dashboard (All Orders Grid)"},
    {"label": "Products page (/products) — product list",
     "name": "Products — Shipping Configuration"},
    {"label": "Products page — click a product row to show detail fields",
     "name": "Products — Product Detail Page (Dimensions, Special Services)"},
    {"label": "PickUp page (/pickup)",
     "name": "PickUp Scheduling"},
    {"label": "Rates Log page (/rateslog)",
     "name": "Rates Log — API Request & Response Viewer"},
    {"label": "FAQ page (/faq)",
     "name": "FAQ — Frequently Asked Questions"},
    {"label": "Manual Label — Shopify Orders → click order → More Actions → Generate Label → show SideDock",
     "name": "Manual Label Generation — SideDock Configuration"},
    {"label": "Order Summary — after label generation (show buttons: Print Documents, More Actions, Download Documents)",
     "name": "Order Summary Page"},
]


def _clean(text: str) -> str:
    text = re.sub(r'\n{4,}', '\n\n', text)
    text = re.sub(r' {3,}', '  ', text)
    return text.strip()[:12000]


def run_interactive_capture() -> None:
    if not AUTH_JSON.exists():
        print(f"ERROR: auth.json not found at {AUTH_JSON}")
        sys.exit(1)

    if not STORE:
        print("ERROR: STORE environment variable not set. Set it to your Shopify store name.")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright")
        sys.exit(1)

    captured_docs: list[dict] = []

    print("\n" + "=" * 60)
    print("AU Post App — Interactive Capture Mode")
    print("=" * 60)
    print(f"Store: {STORE}")
    print(f"Opening Chrome to: {BASE_URL}/settings")
    print("Navigate to each section manually, then press ENTER to capture.")
    print("=" * 60 + "\n")

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
        except Exception:
            browser = pw.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )

        context = browser.new_context(
            storage_state=str(AUTH_JSON),
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1400, "height": 1000},
        )
        page = context.new_page()

        # Open app settings page to start
        print("Loading app…")
        page.goto(f"https://admin.shopify.com/store/{STORE}", wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(2000)
        page.goto(f"{BASE_URL}/settings", wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(4000)

        app_frame = page.frame_locator('iframe[name="app-iframe"]')
        app_main  = app_frame.locator("#AppFrameMain")

        for i, target in enumerate(CAPTURE_TARGETS, 1):
            print(f"\n[{i}/{len(CAPTURE_TARGETS)}] Navigate to: {target['label']}")
            user_input = input("    Press ENTER to capture, 's' to skip, 'q' to quit: ").strip().lower()

            if user_input == "q":
                print("Quitting…")
                break
            if user_input == "s":
                print(f"    Skipped: {target['name']}")
                continue

            # Give React a moment to finish rendering after any user interaction
            page.wait_for_timeout(1500)

            captured = ""
            try:
                captured = app_main.inner_text(timeout=10_000)
            except Exception:
                try:
                    captured = app_frame.locator("body").inner_text(timeout=8_000)
                except Exception as e:
                    print(f"    ERROR capturing: {e}")
                    continue

            captured = _clean(captured)

            if len(captured) < 100:
                print(f"    WARNING: only {len(captured)} chars captured — page may not be loaded yet.")
                retry = input("    Retry? (ENTER to retry, 's' to skip): ").strip().lower()
                if retry == "s":
                    continue
                page.wait_for_timeout(2000)
                try:
                    captured = _clean(app_main.inner_text(timeout=10_000))
                except Exception:
                    pass

            captured_docs.append({
                "name": target["name"],
                "content": captured,
                "chars": len(captured),
            })
            print(f"    ✓ Captured {len(captured)} chars for: {target['name']}")

        browser.close()

    # ── Save results ──────────────────────────────────────────────────────────
    if not captured_docs:
        print("\nNo sections captured.")
        return

    # Save as JSON for review
    output_path = Path(__file__).parent / "captured_app_content.json"
    with open(output_path, "w") as f:
        json.dump(captured_docs, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved {len(captured_docs)} sections to: {output_path}")
    print("\nSummary:")
    for doc in captured_docs:
        print(f"  • {doc['name']}: {doc['chars']} chars")

    print("\nNext step: run the ingest pipeline to load this into ChromaDB.")
    print("  python -m ingest.run_ingest --sources app")


if __name__ == "__main__":
    run_interactive_capture()
