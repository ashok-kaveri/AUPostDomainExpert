"""
App Navigator — AU Post Shopify App UI Deep Capture
====================================================
Uses a live Playwright browser session (auth.json) to visit every section
of the AU Post Shopify embedded app and capture all visible UI content.

What is captured per page/section:
  • All headings, labels, descriptions and help text
  • Every form field label and its available options (selects, radios, checkboxes)
  • Toggle/switch labels with explanatory text
  • Table column headers (shipping orders, packaging boxes, request log, etc.)
  • Error messages and status messages shown in the UI
  • Navigation menu items visible in the sidebar

This gives the RAG knowledge base a complete, accurate picture of every
setting, option and field in the app — exactly as the user sees it.

Sections navigated
------------------
  1.  Shipping Orders Dashboard      /shopify
  2.  Settings — Account             /settings  → Account tab
  3.  Settings — Packages            /settings  → Packages tab
  4.  Settings — Additional Services /settings  → Additional Services tab
  5.  Settings — Rates               /settings  → Rate Settings tab
  6.  Settings — Print Settings      /settings  → Print Settings tab
  7.  Settings — Notifications       /settings  → Notifications tab
  8.  Products                       /products
  9.  Manual Label (side dock)       from Shopify Orders → More Actions → Generate Label
 10.  PickUp Scheduling              /pickup
 11.  Rates Log                      /rateslog

Usage (standalone):
    source .venv/bin/activate
    python -m ingest.app_navigator
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config

logger = logging.getLogger(__name__)

STORE    = os.getenv("STORE", "")
APP_SLUG = os.getenv("AUPOST_APP_SLUG", "australia-post-rates-labels")
BASE_URL = f"https://admin.shopify.com/store/{STORE}/apps/{APP_SLUG}" if STORE else ""
AUTH_JSON = Path(config.AUTOMATION_CODEBASE_PATH) / "auth.json"

_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=config.CHUNK_SIZE,
    chunk_overlap=config.CHUNK_OVERLAP,
)

# ---------------------------------------------------------------------------
# Page sections to capture
# ---------------------------------------------------------------------------
_APP_SECTIONS = [
    {
        "name": "Shipping Orders Dashboard (All Orders Grid)",
        "path": "/shopify",
        "description": (
            "Main shipping orders list — All Orders grid inside the AU Post app iframe.\n"
            "Columns: Order#, Label created date, Customer, Label status, Shipping Service,\n"
            "         Subtotal, Shipping Cost, Packages, Products, Weight, Messages\n"
            "Tab filters: All | Pending | Label Generated\n"
            "Label statuses: 'label generated' (green), 'inprogress' (yellow), 'failed' (red),\n"
            "                'auto cancelled' (grey), 'label cancelled'\n"
            "Top-right buttons: 'Generate New Labels', 'How to', 'Help', 'Generate Report'\n"
            "Click an order ROW → opens Order Summary page for that order\n"
            "Do NOT click 'Generate New Labels' — that creates new labels across multiple orders."
        ),
    },
    {
        "name": "Settings — Account Settings",
        "path": "/settings",
        "description": (
            "Account Settings — AU Post account configuration.\n"
            "Two account types supported:\n"
            "  1. eParcel — Australia Post's business service for higher-volume merchants\n"
            "     • Supports domestic + international shipping\n"
            "     • Extra Cover up to $5,000 AUD\n"
            "     • Dangerous goods support (domestic only)\n"
            "     • Services: Parcel Post, Express Post (+ Signature variants)\n"
            "  2. MyPost Business — suitable for smaller-volume businesses\n"
            "     • Domestic shipping only\n"
            "     • Extra Cover up to $1,000 AUD\n"
            "     • No dangerous goods support\n"
            "     • Services: Standard, Express\n"
            "Fields: Account Number, API Key/Secret, Account Type selection\n"
            "Button: 'Save Account Settings' → success toast on save"
        ),
    },
    {
        "name": "Settings — Packages Configuration",
        "path": "/settings",
        "description": (
            "Packages Settings — packaging and weight configuration.\n"
            "• Default package dimensions (Length, Width, Height in cm)\n"
            "• Default package weight (kg)\n"
            "• Packing method: Weight Based / Box Packing\n"
            "• Custom boxes: Name, Inner/Outer dimensions, Empty weight, Max weight\n"
            "• AU Post box presets for eParcel and MyPost Business\n"
            "• Max weight per package\n"
            "• Volumetric weight formula: L(cm) × W(cm) × H(cm) ÷ 4000\n"
            "  (AU Post charges higher of actual vs cubic weight)\n"
            "Button: 'Save' → success toast on save"
        ),
    },
    {
        "name": "Settings — Additional Services",
        "path": "/settings",
        "description": (
            "Additional Services — special shipping options.\n"
            "The SideDock (always visible during manual label generation) contains:\n"
            "  1. Signature on Delivery: checkbox — recipient must sign\n"
            "     ⚠️ Cannot combine with Authority to Leave\n"
            "  2. Authority to Leave (ATL): checkbox — parcel left without signature\n"
            "     ⚠️ Cannot combine with Signature on Delivery\n"
            "  3. Extra Cover: checkbox → input declared value AUD\n"
            "     Max: $5,000 AUD (eParcel) / $1,000 AUD (MyPost Business)\n"
            "  4. Safe Drop: checkbox — leave in safe location\n"
            "  5. Dangerous Goods: checkbox (eParcel domestic only)\n"
            "Global settings for default values of the above services.\n"
            "Button: 'Save Additional Services' → success toast"
        ),
    },
    {
        "name": "Settings — Rate Settings",
        "path": "/settings",
        "description": (
            "Rate Settings — shipping rate configuration for checkout.\n"
            "• Enable/disable individual AU Post carrier services for checkout display\n"
            "• Display name override per service\n"
            "• Markup: flat amount (AUD) or percentage (%) per service\n"
            "• Free shipping threshold\n"
            "• Rate request mode: Live rates or Flat rate\n"
            "• Show transit days / delivery estimate at checkout\n"
            "• Fallback rate — shown if AU Post API returns no rates\n"
            "• Rate adjustment (markup/discount)\n"
            "Service codes:\n"
            "  T28  → Parcel Post\n"
            "  E86J → Express Post\n"
            "  PLT  → International Economy\n"
            "Button: 'Save Rate Settings' → success toast"
        ),
    },
    {
        "name": "Settings — Print Settings",
        "path": "/settings",
        "description": (
            "Print Settings — label format and printing configuration.\n"
            "• Label Format: PDF / ZPL / EPL\n"
            "• Label Size: A4 / A5 / 4x6 thermal\n"
            "• Number of label copies\n"
            "• Auto-print vs manual download\n"
            "• Include packing slip with label\n"
            "• Include commercial invoice (for international shipments)\n"
            "Button: 'Save Print Settings' → success toast"
        ),
    },
    {
        "name": "Settings — Notifications",
        "path": "/settings",
        "description": (
            "Notifications — email alerts configuration.\n"
            "• Shipment notification to customer: on label generation / pickup / delivery\n"
            "• Send tracking email to customer with Australia Post tracking number\n"
            "• Send copy to merchant email\n"
            "• Notification triggers: On Label Generation, On Dispatch, On Delivery\n"
            "• Custom notification message template\n"
            "Button: 'Save Notifications' → success toast"
        ),
    },
    {
        "name": "Products — Shipping Configuration",
        "path": "/products",
        "description": (
            "Configure AU Post shipping settings for individual Shopify products.\n"
            "Shows a searchable list of all products in the Shopify store.\n"
            "Search: click search/filter button → type product name → press Enter\n"
            "Click product row → opens product detail page\n"
            "\nPer-product settings:\n"
            "  • Dimensions: Length, Width, Height (cm)\n"
            "  • Weight (kg)\n"
            "  • Signature on Delivery: checkbox\n"
            "  • Authority to Leave (ATL): checkbox\n"
            "  • Extra Cover: checkbox + declared value (AUD)\n"
            "  • Safe Drop: checkbox\n"
            "  • Dangerous Goods: checkbox (eParcel only)\n"
            "Button: 'Save' → toast 'Products Successfully Saved'\n"
            "⚠️ There is NO 'Add product' button here. Use Shopify admin to create products.\n"
            "Test products: 'Test Product A' or 'Test Product B'"
        ),
    },
    {
        "name": "Manual Label Generation — SideDock Configuration",
        "path": None,   # opened from Shopify Orders → More Actions → Generate Label
        "description": (
            "Manual label generation flow — accessed from Shopify Orders.\n"
            "Flow: Shopify admin → Orders → click order → More Actions → 'Generate Label'\n"
            "\nThe page has TWO areas:\n"
            "LEFT SIDE — Package & Rates area:\n"
            "  a. 'Generate Packages' button → packages auto-calculated\n"
            "  b. 'Get Shipping Rates' button → AU Post rates load as radio buttons\n"
            "  c. Select a shipping service radio button\n"
            "  d. 'Generate Label' button → label is created\n"
            "\nRIGHT SIDE — The SideDock (ALWAYS VISIBLE — configure BEFORE generating label):\n"
            "  1. Signature on Delivery: checkbox\n"
            "     ⚠️ Cannot combine with ATL\n"
            "  2. Authority to Leave (ATL): checkbox\n"
            "     ⚠️ Cannot combine with Signature on Delivery\n"
            "  3. Extra Cover: checkbox → input declared value AUD\n"
            "     Max: $5,000 AUD (eParcel) / $1,000 AUD (MyPost Business)\n"
            "  4. Safe Drop: checkbox\n"
            "  5. Dangerous Goods: checkbox (eParcel domestic only)\n"
            "\nAfter generating: redirects to Order Summary page automatically."
        ),
    },
    {
        "name": "Order Summary Page",
        "path": None,   # opened after label generation or from Shipping grid
        "description": (
            "Order Summary — after label generation or clicking order from Shipping grid.\n"
            "\nButtons visible:\n"
            "  • 'Print Documents' — opens PluginHive document viewer in a NEW TAB\n"
            "  • 'Upload Documents' — upload custom docs\n"
            "  • 'More Actions' dropdown:\n"
            "      - 'Download Documents' → downloads ZIP with label PDF + request/response JSON\n"
            "      - 'Cancel Label' → cancel the label\n"
            "      - 'Return Label' → opens return label flow\n"
            "      - 'How To' → modal with usage instructions\n"
            "  • TWO TABS: 'Packages' | 'Return packages'\n"
            "  • '← #XXXX' back arrow → back to Shipping grid\n"
            "  • Previous / Next buttons → navigate between orders\n"
            "\nLabel status badge: 'label generated' / 'Pending' / 'Failed'\n"
            "\nVerification strategies:\n"
            "  Strategy 1: Check 'label generated' badge\n"
            "  Strategy 2: More Actions → Download Documents → ZIP with request JSON\n"
            "              JSON fields: items[0].product_id, options.signature_on_delivery,\n"
            "              options.authority_to_leave, options.extra_cover.amount,\n"
            "              from.postcode, to.postcode, trackingNumbers[0]\n"
            "  Strategy 3: Print Documents → new tab → screenshot → visual verification"
        ),
    },
    {
        "name": "Return Label Generation",
        "path": None,   # opened from Order Summary → Return packages tab
        "description": (
            "Return label generation — two entry points:\n"
            "\nWAY A — From app Order Summary:\n"
            "  1. Order Summary → 'Return packages' tab\n"
            "  2. Click 'Return Packages' button\n"
            "  3. Enter return quantity\n"
            "  4. Click 'Refresh Rates' → rates load\n"
            "  5. Select service radio button\n"
            "  6. Click 'Generate Return Label'\n"
            "  7. Verify: 'SUCCESS' badge + 'Download Label' link visible\n"
            "\nWAY B — From Shopify admin order page:\n"
            "  1. Shopify admin → Orders → click order\n"
            "  2. More Actions → 'Generate Return Label'\n"
            "     ⚠️ NOT 'Create return label' — that is a Shopify-native feature\n"
            "  3. Same steps as Way A from step 4"
        ),
    },
    {
        "name": "PickUp Scheduling",
        "path": "/pickup",
        "description": (
            "Request Australia Post courier pickup for ready-to-ship packages.\n"
            "Access: App sidebar → PickUp\n"
            "\nPickup scheduling fields:\n"
            "  • Pickup Date — date AU Post should arrive\n"
            "  • Pickup Time — time window for collection\n"
            "  • Location description — where driver should collect\n"
            "  • Package count and total weight\n"
            "\nResult: AU Post returns a pickup confirmation number.\n"
            "Pickup is scheduled via Australia Post REST API.\n"
            "Pickup appears in the PickUp list with status and confirmation number."
        ),
    },
    {
        "name": "Rates Log — API Request & Response Viewer",
        "path": "/rateslog",
        "description": (
            "The Rates Log page shows raw AU Post API requests and responses for debugging.\n"
            "Columns: Date/Time, Order ID, Request Type, Status (Success/Error), Error message\n"
            "Click a log entry → shows:\n"
            "  • Full JSON request body sent to AU Post API\n"
            "  • Full JSON response body received\n"
            "  • HTTP status code\n"
            "\nAll logs are JSON (REST API only — no SOAP/XML).\n"
            "\nKey request JSON fields to verify:\n"
            "  items[0].length                  → package length (cm)\n"
            "  items[0].width                   → package width (cm)\n"
            "  items[0].height                  → package height (cm)\n"
            "  items[0].weight                  → package weight (kg)\n"
            "  items[0].product_id              → service code (T28=Parcel Post, E86J=Express Post)\n"
            "  options.signature_on_delivery    → true / false\n"
            "  options.authority_to_leave       → true / false\n"
            "  options.extra_cover.amount       → declared value AUD\n"
            "  from.postcode                    → sender postcode (4 digits)\n"
            "  to.postcode                      → receiver postcode\n"
            "  trackingNumbers[0]               → Article ID (tracking number)"
        ),
    },
    {
        "name": "FAQ — Frequently Asked Questions",
        "path": "/faq",
        "description": (
            "In-app FAQ page covering common merchant questions about the AU Post Shopify app.\n"
            "Topics: rate display setup, label printing, return labels,\n"
            "special services configuration, account setup, troubleshooting.\n"
            "Covers both eParcel and MyPost Business account types."
        ),
    },
]


# ---------------------------------------------------------------------------
# Inline knowledge documents
# ---------------------------------------------------------------------------
_INLINE_KNOWLEDGE = [
    {
        "name": "App Navigation Structure",
        "content": (
            "AU Post Shopify App — Navigation Structure\n"
            "==========================================\n"
            "The app is embedded in Shopify admin as an iframe.\n\n"
            "App sidebar links (INSIDE the iframe):\n"
            "  • Shipping  → /shopify    — All Orders grid\n"
            "  • PickUp    → /pickup     — Schedule Australia Post pickup\n"
            "  • Products  → /products   — Map products to dimensions, signature, extra cover\n"
            "  • Settings  → /settings   — AU Post account, services, packages, rates\n"
            "  • FAQ       → /faq        — Help articles\n"
            "  • Rates Log → /rateslog   — Historical rate request log\n\n"
            "Shopify admin links (OUTSIDE iframe, left sidebar):\n"
            "  • Orders   — Shopify orders list (generate labels from here)\n"
            "  • Products — Shopify product catalog (create/edit products)\n\n"
            "Navigation strategy:\n"
            "  - App nav items (Shipping, Settings, PickUp, Products, FAQ, Rates Log) → search iframe first\n"
            "  - Shopify admin items (Orders, Products in admin) → search full page first\n"
        ),
    },
    {
        "name": "App Error Messages and Status Indicators",
        "content": (
            "AU Post App — Error Messages and Status Indicators\n"
            "===================================================\n\n"
            "Label status values in All Orders grid:\n"
            "  • label generated — AU Post label created successfully, tracking number assigned\n"
            "  • inprogress      — label being generated\n"
            "  • failed          — label generation failed (see request log for details)\n"
            "  • auto cancelled  — label cancelled automatically\n"
            "  • label cancelled — label cancelled manually\n\n"
            "Common toast messages:\n"
            "  ✅ 'Products Successfully Saved' — after saving product settings\n"
            "  ✅ 'Settings saved successfully' — after saving any settings\n"
            "  ✅ 'Label generated successfully' — after label creation\n"
            "  ❌ 'Error generating label — check request log for details'\n"
            "  ❌ 'Unable to fetch rates — check AU Post account settings'\n\n"
            "Common errors:\n"
            "  INVALID_ACCOUNT — AU Post account credentials incorrect\n"
            "  SERVICE_UNAVAILABLE — Selected service not available for this route\n"
            "  INVALID_WEIGHT — Package weight is 0 or exceeds service maximum\n"
            "  DANGEROUS_GOODS_NOT_SUPPORTED — MyPost Business does not support dangerous goods\n"
            "  EXTRA_COVER_EXCEEDED — Declared value exceeds max ($5,000 eParcel / $1,000 MyPost)\n"
            "  SIGNATURE_ATL_CONFLICT — Cannot combine Signature on Delivery with Authority to Leave\n"
        ),
    },
    {
        "name": "AU Post Carrier Services Available in App",
        "content": (
            "AU Post Carrier Services — Available in AU Post Shopify App\n"
            "=============================================================\n\n"
            "eParcel Services (higher-volume businesses):\n"
            "  Domestic:\n"
            "  • T28  — Parcel Post (standard domestic)\n"
            "  • E86J — Express Post (next business day)\n"
            "  • T28S — Parcel Post + Signature\n"
            "  • E86JS— Express Post + Signature\n"
            "  International:\n"
            "  • PLT  — International Economy\n"
            "  • PTI  — International Standard\n"
            "  • EPI  — International Express\n\n"
            "MyPost Business Services (smaller-volume businesses):\n"
            "  Domestic only:\n"
            "  • Standard  — MyPost Business Standard\n"
            "  • Express   — MyPost Business Express\n\n"
            "Special Services (eParcel domestic):\n"
            "  • Signature on Delivery — recipient must sign (options.signature_on_delivery=true)\n"
            "  • Authority to Leave    — parcel left without signature (options.authority_to_leave=true)\n"
            "  • Extra Cover           — insurance up to $5,000 AUD (options.extra_cover.amount)\n"
            "  • Safe Drop             — leave in safe location\n"
            "  • Dangerous Goods       — eParcel domestic only\n\n"
            "Cubic weight formula (AU Post charges higher of actual vs cubic):\n"
            "  cubic_weight = L(cm) × W(cm) × H(cm) ÷ 4000\n"
        ),
    },
    {
        "name": "Download Documents ZIP — JSON Field Verification",
        "content": (
            "AU Post App — Download Documents ZIP for JSON Field Verification\n"
            "=================================================================\n\n"
            "The 'Download Documents' option under 'More Actions' on the Order Summary page\n"
            "downloads a ZIP containing:\n"
            "  • Label PDF\n"
            "  • createShipment request JSON (the request sent to AU Post API)\n"
            "  • createShipment response JSON (the response from AU Post API)\n\n"
            "Key fields in the request JSON to verify:\n"
            "  items[0].length                  → package length (cm)\n"
            "  items[0].width                   → package width (cm)\n"
            "  items[0].height                  → package height (cm)\n"
            "  items[0].weight                  → package weight (kg)\n"
            "  items[0].product_id              → service code\n"
            "    'T28'  → Parcel Post\n"
            "    'E86J' → Express Post\n"
            "    'PLT'  → International Economy\n"
            "  options.signature_on_delivery    → true / false\n"
            "  options.authority_to_leave       → true / false\n"
            "  options.extra_cover.amount       → declared value AUD\n"
            "  from.postcode                    → sender postcode (4 digits, Australian)\n"
            "  to.postcode                      → receiver postcode\n\n"
            "Key fields in the response JSON:\n"
            "  trackingNumbers[0]               → Article ID (tracking number)\n"
            "  items[0].article_id              → Article ID on item level\n\n"
            "How to access the ZIP:\n"
            "  1. On Order Summary page → click 'More Actions'\n"
            "  2. Click 'Download Documents'\n"
            "  3. ZIP downloads automatically and is unzipped by the verifier\n"
            "  4. JSON content is injected into next step context\n"
        ),
    },
]


# ---------------------------------------------------------------------------
# Browser capture helper
# ---------------------------------------------------------------------------

def _capture_page_via_browser(sections: list[dict]) -> list[Document]:
    """
    Launch a Playwright browser with auth.json, navigate to each app section,
    and capture the iframe text content.
    Returns list of Documents with captured content.
    """
    docs: list[Document] = []

    if not AUTH_JSON.exists():
        logger.warning("auth.json not found at %s — skipping live browser capture", AUTH_JSON)
        return docs

    if not STORE:
        logger.warning("STORE env var not set — skipping live browser capture")
        return docs

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("playwright not installed — skipping live browser capture")
        return docs

    logger.info("Starting browser-based app navigation for %d sections…", len(sections))

    with sync_playwright() as pw:
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ]
        try:
            browser = pw.chromium.launch(
                channel="chrome",
                headless=False,
                args=launch_args,
            )
        except Exception:
            logger.debug("Chrome channel unavailable, falling back to Chromium")
            browser = pw.chromium.launch(headless=False, args=launch_args)

        try:
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

            # ── Warm-up: load Shopify admin first so session cookies activate ──
            logger.info("  Warm-up: loading Shopify admin…")
            page.goto(
                f"https://admin.shopify.com/store/{STORE}",
                wait_until="domcontentloaded",
                timeout=60_000,
            )
            page.wait_for_timeout(3000)

            # ── Navigate to app once so sidebar loads ─────────────────────────
            page.goto(f"{BASE_URL}/shopify", wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(4000)

            app_frame = page.frame_locator('iframe[name="app-iframe"]')
            app_main  = app_frame.locator("#AppFrameMain")

            import re

            current_path: str | None = None

            for section in sections:
                name = section["name"]
                path = section.get("path")

                # Skip modal/drawer sections — no dedicated URL
                if path is None:
                    logger.info("  Skipping (modal, no URL): %s", name)
                    continue

                route = path.lstrip("/")
                url   = f"{BASE_URL}/{route}"

                logger.info("  Navigating to: %s", name)
                try:
                    if path != current_path:
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                        except Exception:
                            pass

                        try:
                            app_main.wait_for(state="visible", timeout=15_000)
                        except Exception:
                            pass
                        page.wait_for_timeout(4000)
                        current_path = path

                    # Capture full #AppFrameMain content
                    captured = ""
                    try:
                        captured = app_main.inner_text(timeout=10_000)
                    except Exception:
                        try:
                            captured = app_frame.locator("body").inner_text(timeout=8_000)
                        except Exception:
                            pass

                    captured = re.sub(r'\n{4,}', '\n\n', captured)
                    captured = re.sub(r' {3,}', '  ', captured)
                    captured = captured.strip()[:8000]

                    if captured and len(captured) > 150:
                        docs.append(Document(
                            page_content=(
                                f"App Section: {name}\n"
                                f"URL: {url}\n\n"
                                f"[Live captured UI content]\n"
                                f"{captured}"
                            ),
                            metadata={
                                "source": "app_navigation_live",
                                "source_type": "app",
                                "section": name,
                                "url": url,
                            },
                        ))
                        logger.info("    ✓ Captured %d chars from %s", len(captured), name)
                    else:
                        logger.info(
                            "    ⚠ Little/no content from %s (%d chars)",
                            name, len(captured),
                        )

                    page.wait_for_timeout(800)

                except Exception as e:
                    logger.warning("    ✗ Failed to capture %s: %s", name, e)

        finally:
            browser.close()

    return docs


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def load_app_knowledge() -> list[Document]:
    """
    Produce a full set of LangChain Documents covering every aspect of the
    AU Post Shopify app UI — settings, options, fields, navigation, errors.

    Strategy:
      1. Emit inline knowledge documents (structured content from deep app expertise)
      2. Attempt live browser capture for each section
      3. Load manually-captured content (from interactive_capture.py)
      4. Chunk and return all documents
    """
    all_docs: list[Document] = []

    # ── 1. Inline structured knowledge (always available) ─────────────────
    logger.info("Loading inline app knowledge (%d sections + %d docs)…",
                len(_APP_SECTIONS), len(_INLINE_KNOWLEDGE))

    for section in _APP_SECTIONS:
        content = (
            f"AU Post Shopify App — {section['name']}\n"
            f"{'=' * (len(section['name']) + 26)}\n\n"
            f"{section['description']}"
        )
        all_docs.append(Document(
            page_content=content,
            metadata={
                "source": "app_knowledge",
                "source_type": "app",
                "section": section["name"],
                "url": f"{BASE_URL}{section.get('path', '')}",
                "type": "structured_knowledge",
            },
        ))

    for item in _INLINE_KNOWLEDGE:
        all_docs.append(Document(
            page_content=item["content"],
            metadata={
                "source": "app_knowledge",
                "source_type": "app",
                "section": item["name"],
                "type": "structured_knowledge",
            },
        ))

    # ── 2. Load manually-captured content (from interactive_capture.py) ─────
    captured_json = Path(__file__).parent / "captured_app_content.json"
    manual_count = 0
    if captured_json.exists():
        try:
            import json as _json
            with open(captured_json) as f:
                manual_captures = _json.load(f)
            for item in manual_captures:
                all_docs.append(Document(
                    page_content=(
                        f"App Section: {item['name']}\n\n"
                        f"[Manually captured UI content]\n"
                        f"{item['content']}"
                    ),
                    metadata={
                        "source": "app_navigation_manual",
                        "source_type": "app",
                        "section": item["name"],
                        "type": "manual_capture",
                    },
                ))
                manual_count += 1
            logger.info("Loaded %d manually-captured sections from %s", manual_count, captured_json.name)
        except Exception as e:
            logger.warning("Failed to load captured_app_content.json: %s", e)

    # ── 3. Live browser capture (best effort) ─────────────────────────────
    live_docs = _capture_page_via_browser(_APP_SECTIONS)
    all_docs.extend(live_docs)
    logger.info(
        "App knowledge: %d structured + %d manual + %d live-captured docs",
        len(_APP_SECTIONS) + len(_INLINE_KNOWLEDGE), manual_count, len(live_docs),
    )

    # ── 4. Chunk all documents ────────────────────────────────────────────
    chunked = _SPLITTER.split_documents(all_docs)
    logger.info("App navigator produced %d chunks total", len(chunked))
    return chunked


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    docs = load_app_knowledge()
    print(f"\n✅ App navigator produced {len(docs)} document chunks")
    if docs:
        print("\nSample chunk:")
        print(docs[0].page_content[:500])
