"""
Smart AC Verifier  —  Agentic QA for AU Post Shopify App
=========================================================
  AC text
    │
    ▼
  1. Claude extracts each scenario
    │
    ▼  (per scenario)
  2. Domain Expert consultation — Claude queries domain RAG + code RAG,
     synthesises ≤200 words about: expected behaviour, API signals, key checks
    │
    ▼
  3. Code RAG — automation POM + backend API context fetched
    │
    ▼
  4. Claude plans: nav_clicks[], look_for[], api_to_watch[], plan sentence
    │
    ▼  (agentic loop — up to 15 steps)
  5. Browser action: navigate / click / fill / scroll / observe / download_zip
  6. Capture: AX tree (depth 6, 250 lines) + screenshot (base64) + network calls
  7. Claude decides next action OR gives verdict OR asks QA
    │
    ▼
  ✅ pass / ❌ fail / ⚠️ partial / 🔶 qa_needed  per scenario

If Claude can't find a feature:
  → status = "qa_needed"
  → Dashboard shows Claude's question + QA text input
  → QA answers → re-run that scenario with the guidance injected
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Callable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

import config

logger = logging.getLogger(__name__)

_CODEBASE       = Path(config.AUTOMATION_CODEBASE_PATH)
_AUTH_JSON      = _CODEBASE / "auth.json"
_ENV_FILE       = _CODEBASE / ".env"
MAX_STEPS       = 15
_ANTI_BOT_ARGS  = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-setuid-sandbox",
]
_CHALLENGE_PHRASES = [
    "connection needs to be verified",
    "let us know you",
    "verify you are human",
    "just a moment",
    "checking your browser",
]


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class VerificationStep:
    action: str
    description: str
    target: str = ""
    success: bool = True
    screenshot_b64: str = ""
    network_calls: list[str] = field(default_factory=list)


@dataclass
class ScenarioResult:
    scenario: str
    status: str = "pending"         # pass | fail | partial | skipped | qa_needed
    verdict: str = ""
    steps: list[VerificationStep] = field(default_factory=list)
    qa_question: str = ""
    bug_report: dict = field(default_factory=dict)


@dataclass
class VerificationReport:
    card_name: str
    app_url: str
    scenarios: list[ScenarioResult] = field(default_factory=list)
    summary: str = ""

    @property
    def passed(self) -> int:
        return sum(1 for s in self.scenarios if s.status == "pass")

    @property
    def failed(self) -> int:
        return sum(1 for s in self.scenarios if s.status in ("fail", "partial"))

    @property
    def qa_needed(self) -> "list[ScenarioResult]":
        return [s for s in self.scenarios if s.status == "qa_needed"]

    def to_automation_context(self) -> str:
        """Convert verified flows into context string for automation writer."""
        lines = [f"=== Smart AC Verification: {self.card_name} ===", f"App: {self.app_url}", ""]
        for sv in self.scenarios:
            icon = {"pass": "✅", "fail": "❌", "partial": "⚠️"}.get(sv.status, "⏭️")
            lines.append(f"{icon} {sv.scenario}")
            for step in sv.steps:
                if step.action in ("click", "fill", "navigate") and step.target:
                    lines.append(f"   [{step.action}] '{step.target}' — {step.description}")
                if step.network_calls:
                    for nc in step.network_calls[:3]:
                        lines.append(f"   [api] {nc}")
            if sv.verdict:
                lines.append(f"   Result: {sv.verdict}")
            lines.append("")
        return "\n".join(lines)


# ── Prompts ───────────────────────────────────────────────────────────────────

_EXTRACT_PROMPT = dedent("""\
    Extract each testable scenario from the acceptance criteria below.
    Return ONLY a JSON array of concise scenario title strings. No explanation.
    Example: ["User can enable Signature on Delivery", "Success toast shown after Save"]

    Acceptance Criteria:
    {ac}
""")

_APP_WORKFLOW_GUIDE = dedent("""\
## AU Post Shopify App — Key Workflows

### TWO DIFFERENT PRODUCTS PAGES — DO NOT CONFUSE THEM

❶  nav_clicks: "AppProducts"  →  <app_base>/products
   PURPOSE: Edit AU Post-specific settings on an EXISTING product already in Shopify.
   HOW: Click a product row in the list → URL becomes <app_base>/products/<product_id>

   EXACT FIELDS on the product edit page:
   ┌─ Product Dimensions ────────────────────────────────────────────┐
   │  Length [input]  cm   Width [input]  cm   Height [input]  cm    │
   │  Weight [input]  kg                                             │
   └─────────────────────────────────────────────────────────────────┘
   ┌─ Special Services ──────────────────────────────────────────────┐
   │  ☐ Signature on Delivery                                        │
   │  ☐ Authority to Leave (ATL)                                     │
   │  ☐ Extra Cover + declared value (AUD)                           │
   │  ☐ Safe Drop                                                    │
   │  ☐ Dangerous Goods (eParcel domestic only)                      │
   └─────────────────────────────────────────────────────────────────┘
   SAVE: "Save" button → success toast "Products Successfully Saved"
   ⚠️ There is NO "Add product" button here. You CANNOT create new products here.
   ⚠️ Use "Test Product A" or "Test Product B" as default test products.

❷  nav_clicks: "ShopifyProducts"  →  admin.shopify.com/store/<store>/products
   PURPOSE: Shopify's own product management — the ONLY place to ADD or create new products.
   ⚠️ This is NOT the AU Post app — it's the Shopify admin products page.

RULE: scenario about "signature / ATL / extra cover / safe drop / dangerous goods / dimensions on a product"
  → nav_clicks: "AppProducts"  (edit AU Post settings on existing product in the app)
RULE: scenario about "add new product / create product / product with many variants"
  → nav_clicks: "ShopifyProducts"  (create/edit in Shopify admin)

### All App Page URLs (direct navigation)
- nav_clicks: "Shipping"    → <app_base>/shopify      — All Orders grid
- nav_clicks: "PickUp"      → <app_base>/pickup       — Pickups list
- nav_clicks: "Settings"    → <app_base>/settings     — App Settings
- nav_clicks: "FAQ"         → <app_base>/faq
- nav_clicks: "Rates Log"   → <app_base>/rateslog     — Rate request history
- nav_clicks: "Orders"      → admin.shopify.com/store/<store>/orders
- nav_clicks: "AppProducts" → <app_base>/products

### ⚠️ How to Generate a Label (CORRECT FLOW — via Shopify Orders)
Label generation happens through the Shopify admin Orders section:
1. Click "Orders" in the Shopify LEFT sidebar (not the app sidebar)
2. Click on an order ID to open the order detail page
3. Click "More Actions" button (top-right dropdown on the order page)
4. You will see label options:
   - "Generate Label" → manual label generation (user picks service/package)
   - "Auto-Generate Label" → automatically picks service and generates
5. Click the desired option → the AU Post app opens inside Shopify for label creation
6. Manual flow: Generate Packages → Get Shipping Rates → select service → Generate Label

### How to Cancel a Label
1. Order Summary → click "More Actions" → click "Cancel Label"
2. Confirm cancellation

### How to Regenerate a Label (after cancel)
1. After cancelling → order status reverts to Pending
2. Go to Shopify Orders → click the same order → More Actions → "Generate Label" again

### App's Own Shipping / Orders Grid (inside the app iframe)
- Click "Shipping" in the app sidebar → shows "All Orders" grid inside the iframe
- Grid columns: Order#, Label created date, Customer, Label status, Shipping Service,
  Subtotal, Shipping Cost, Packages, Products, Weight, Messages
- Tab filters: All | Pending | Label Generated
- Label statuses: "label generated" (green), "inprogress" (yellow), "failed" (red),
  "auto cancelled" (grey), "label cancelled"
- Top-right buttons: "Generate New Labels", "How to", "Help", "Generate Report"
- ⚠️ CLICK AN ORDER ROW to open the Order Summary page for that order (inside the app)
- Do NOT click "Generate New Labels" — that creates labels across multiple orders

### Settings Navigation
- Click "Settings" in app sidebar → Settings page with multiple tabs/sections
- Sections: Account, Packages, Additional Services, Rates, Print Settings, Notifications

### Label Status Values (inside app's Shipping page)
- Pending          → no label yet
- In Progress      → label being generated
- Label Generated  → label created successfully
- Failed           → label generation failed

### ⚠️ Full Verification Flow by Scenario Type

─────────────────────────────────────────────────────────
SCENARIO GROUP A — SideDock Special Services
(Signature on Delivery / Authority to Leave / Extra Cover / Safe Drop / Dangerous Goods)
─────────────────────────────────────────────────────────
order_action = create_new  (verifier creates a fresh Shopify order BEFORE the browser opens)
nav_clicks: ["Orders"]  (start on Shopify Orders page)

STEP 1 — Navigate to fresh order and start manual label:
  The fresh order just created is the MOST RECENT order at the top.
  → Click on it → More Actions → "Generate Label" (use MANUAL label flow)
  → Generate Packages → Get Shipping Rates (rates appear as radio buttons)

STEP 2 — Configure SideDock BEFORE clicking Generate Label:
  The SideDock is on the RIGHT SIDE — ALWAYS VISIBLE during manual label generation.
  SideDock options (configure ONLY what the scenario tests):
    Signature on Delivery  → check checkbox (⚠️ cannot combine with ATL)
    Authority to Leave     → check checkbox (⚠️ cannot combine with Signature)
    Extra Cover            → check checkbox → fill declared value (AUD)
                             Max: $5,000 (eParcel) / $1,000 (MyPost Business)
    Safe Drop              → check checkbox
    Dangerous Goods        → check checkbox (eParcel domestic only)

STEP 3 — Generate Label:
  → Select first radio button service
  → Click "Generate Label" button → Order Summary opens
  → Verify "label generated" badge visible (Strategy 1)

STEP 4 — Verify JSON fields via Download Documents ZIP (Strategy 2):
  → More Actions → Download Documents
  → ZIP extracted automatically — JSON content appears in next step context
  → Verify these fields:
      Signature:             options.signature_on_delivery = true
      ATL:                   options.authority_to_leave = true
      Extra Cover:           options.extra_cover.amount = <declared_value>
      Dangerous Goods:       items[0].contains_dangerous_goods = true
      Service code:          items[0].product_id (T28=Parcel Post, E86J=Express Post)
      Tracking number:       trackingNumbers[0]
  → action=verify based on JSON values

─────────────────────────────────────────────────────────
SCENARIO GROUP B — Product-Level Configuration
(Dimensions / Product-specific Signature / Extra Cover on product)
─────────────────────────────────────────────────────────
order_action = create_new
nav_clicks: ["AppProducts"]  (start on the AU Post app Products page)

STEP 1 — Configure product in AU Post app:
  → Click "Products" in app sidebar → products list loads
  → Click search icon → type "Test Product A" → press Enter → click product row
  → Configure ONLY what the scenario tests:
      Dimensions: fill Length, Width, Height (cm) + Weight (kg) → Save
      Signature: check "Signature on Delivery" → Save
      Extra Cover: check "Extra Cover" → fill declared value → Save
  → Click "Save" → toast "Products Successfully Saved"

STEP 2 — Generate label on fresh order and verify JSON:
  action=navigate, path="orders"
  → The fresh order is the MOST RECENT order at the top
  → Click it → More Actions → "Generate Label"
  → Generate Packages → Get Rates → select service → Generate Label
  → Verify via Download Documents ZIP (Strategy 2)

─────────────────────────────────────────────────────────
SCENARIO GROUP C — No Label Needed
─────────────────────────────────────────────────────────
- "Settings only" → App sidebar → Settings → configure → verify
- "Rates log / Rates Log" → App sidebar → Rates Log → verify entries
- "Order grid / filter / navigation" → App sidebar → Shipping → All Orders
- "Return label" → App sidebar → Shipping → Label Generated tab → click order
  → Return packages tab → Return Packages → Refresh Rates → select → Generate Return Label
  → Verify: "SUCCESS" badge + "Download Label" link visible
- "Download documents / verify label" → App sidebar → Shipping → Label Generated tab
  → click first "label generated" order → Order Summary → More Actions → Download Documents
- "Next/Previous order navigation" → Order Summary → use Previous / Next buttons

─────────────────────────────────────────────────────────
SCENARIO GROUP D — Return Labels
─────────────────────────────────────────────────────────
WAY A — From app Order Summary:
1. App sidebar → Shipping → Label Generated tab → click first order
2. Click "Return packages" tab
3. Click "Return Packages" button
4. Enter return quantity
5. Click "Refresh Rates" → rates load
6. Select service radio button
7. Click "Generate Return Label"
8. Verify: "SUCCESS" badge + "Download Label" link visible

WAY B — From Shopify admin:
1. Shopify admin → Orders → click order → More Actions → "Generate Return Label"
   ⚠️ NOT "Create return label" — that is a Shopify-native feature
2. Same as Way A from step 4

─────────────────────────────────────────────────────────
SCENARIO GROUP E — eParcel vs MyPost Business Account Type
─────────────────────────────────────────────────────────
- eParcel: supports international, extra cover up to $5,000, dangerous goods
- MyPost Business: domestic only, extra cover up to $1,000, NO dangerous goods
- Verify by checking account type in Settings → Account Settings
- Verify by attempting to set dangerous goods (only available for eParcel)

### ⚠️ How to Access the Order Summary Page
WAY 1 — From the app's Shipping / Orders grid (PREFERRED for verifying existing labels):
1. Click "Shipping" in the app sidebar → All Orders grid loads
2. Click on any order ROW with "label generated" status → Order Summary opens

WAY 2 — After generating a label:
- After completing label generation, the app redirects to Order Summary automatically

### ⚠️ How to Verify Label and Documents — 3 Strategies

Order Summary Page buttons:
- "← #XXXX" back arrow → back to Shipping grid
- Label status badge next to order number: "label generated" / "Pending" / "Failed"
- "Print Documents" button → opens PluginHive document viewer in a NEW BROWSER TAB
- "Upload Documents" button → upload custom docs
- "More Actions" dropdown:
  - "Download Documents" → downloads ZIP with label PDF + request/response JSON
  - "Cancel Label" → cancel the label
  - "Return Label" → opens return label flow
  - "How To" → modal with instructions; click "Click Here" button to download RequestResponse ZIP
- TWO TABS: "Packages" | "Return packages"
- Previous / Next buttons → navigate between orders

STRATEGY 1 — Verify label EXISTS (for "label is generated" scenarios):
1. Navigate to Shipping → click order with "label generated" status → Order Summary opens
   OR after label generation → page redirects to Order Summary automatically
2. Look for "label generated" status badge
3. Look for "Print Documents" and "More Actions" buttons visible
4. Take a screenshot — if "label generated" visible, verdict = PASS

STRATEGY 2 — Verify JSON field values (signature, ATL, extra cover, service code, etc.):
Use for: "JSON has correct field values", "options.signature_on_delivery=true", "service code", etc.
STEPS:
1. On Order Summary → action=click, target="More Actions"
2. action=download_zip, target="Download Documents"
   → ZIP extracted automatically — JSON content appears in your NEXT step context
3. Read JSON fields:
   - Service code:             items[0].product_id (T28=Parcel Post, E86J=Express Post, PLT=Intl Economy)
   - Signature on Delivery:    options.signature_on_delivery (true/false)
   - Authority to Leave:       options.authority_to_leave (true/false)
   - Extra Cover amount:       options.extra_cover.amount (AUD value)
   - Dangerous Goods:          items[0].contains_dangerous_goods (true/false)
   - Tracking number:          trackingNumbers[0]
   - Article ID:               items[0].article_id
   - Package length (cm):      items[0].length
   - Package width (cm):       items[0].width
   - Package height (cm):      items[0].height
   - Package weight (kg):      items[0].weight
   - Sender postcode:          from.postcode
   - Receiver postcode:        to.postcode
4. action=verify with finding based on JSON values → verdict = PASS/FAIL

STRATEGY 3 — Visual verification via Print Documents (for label content / tracking number):
1. On Order Summary → click "Print Documents" button
   → A NEW BROWSER TAB opens with PluginHive document viewer
2. action=switch_tab
3. action=screenshot → read label visually
4. action=verify based on what is visible
5. action=close_tab

WHICH STRATEGY TO USE:
- "label is generated" / "label status"                      → Strategy 1
- JSON field values (signature, ATL, extra cover, service)   → Strategy 2 (Download Documents ZIP)
- Visual label content / tracking number / document present  → Strategy 3 (Print Documents → new tab)

⚠️ For JSON field verification: Strategy 2 works (Download Documents ZIP has request JSON inside).
⚠️ Print Documents is NOT a download — it opens a NEW TAB. Use switch_tab + screenshot + close_tab.

### ⚠️ Manual Label Generation — Full Flow
1. Shopify Orders → click an order → More Actions → "Generate Label"
2. Inside the app (iframe):
   LEFT SIDE:
   a. Click "Generate Packages" button → packages auto-calculated
   b. Click "Get shipping rates" button → AU Post rates load as radio buttons
   c. Select a shipping service (click its radio button)
   RIGHT SIDE — The SideDock (ALWAYS VISIBLE — configure before generating label):
   d. Configure SideDock options as needed (Signature, ATL, Extra Cover, Safe Drop, Dangerous Goods)
   e. Click "Generate Label" button → label is created
3. After generation the Order Summary page opens automatically

### ⚠️ The SideDock — Manual Label Options Panel (ALWAYS VISIBLE)
The SideDock is a panel on the RIGHT SIDE of the Manual Label page.
It is ALWAYS visible — no need to open or toggle it.
Settings configured here OVERRIDE any product-level settings for this label.

SideDock contains (top to bottom):
1. SIGNATURE ON DELIVERY
   - Checkbox: "Signature on Delivery"
   - ⚠️ Cannot combine with Authority to Leave
   - Verifiable in JSON: options.signature_on_delivery = true

2. AUTHORITY TO LEAVE (ATL)
   - Checkbox: "Authority to Leave"
   - ⚠️ Cannot combine with Signature on Delivery
   - Verifiable in JSON: options.authority_to_leave = true

3. EXTRA COVER
   - Checkbox: "Extra Cover"
   - After checking → input field appears: declared value (AUD)
   - Max: $5,000 AUD (eParcel) / $1,000 AUD (MyPost Business)
   - Verifiable in JSON: options.extra_cover.amount = <value>

4. SAFE DROP
   - Checkbox: "Safe Drop"
   - Leave parcel in a safe location if no one home

5. DANGEROUS GOODS
   - Checkbox: "Dangerous Goods"
   - eParcel domestic only — NOT available for MyPost Business
   - Verifiable in JSON: items[0].contains_dangerous_goods = true

### ⚠️ AU Post App — Product Config (AppProducts page)
URL: <app_base>/products
1. Click "Products" in app sidebar
2. Search product: click search/filter button → type product name → press Enter
3. Click product row → product detail page opens
4. Configure ONLY what the scenario tests:
   - Dimensions: Length (cm), Width (cm), Height (cm), Weight (kg)
   - Signature on Delivery: checkbox
   - Authority to Leave: checkbox
   - Extra Cover: checkbox + declared value (AUD)
   - Safe Drop: checkbox
   - Dangerous Goods: checkbox (eParcel only)
5. Click "Save" → toast "Products Successfully Saved"
6. Back button (aria-label="products") → back to product list
Use "Test Product A" or "Test Product B" as default test products.

### ⚠️ How to Generate a Return Label
WAY A — From Inside the App:
1. Open Order Summary page in the app (Shipping → click order with "label generated")
2. Click the "Return packages" tab (next to "Packages" tab)
3. Click "Return Packages" button → Return Label page opens
4. Enter return quantity (default 1)
5. Click "Refresh Rates" button → rates load
6. Select a shipping service radio button
7. Click "Generate Return Label" button
8. Verify: "SUCCESS" badge appears + "Download Label" link visible

WAY B — From Shopify Admin:
1. Shopify admin → Orders → click the order
2. More Actions → "Generate Return Label"
   ⚠️ NOT "Create return label" — that is a different Shopify feature
3. Same steps as Way A from step 4

### ⚠️ How to View Rate Logs (Rates Log page)
⚠️ CRITICAL: Rates Log at <app_base>/rateslog shows requests from STOREFRONT CHECKOUT ONLY.
- API-created test orders do NOT appear in Rates Log — it will be EMPTY.
- For JSON field verification on test orders → use Download Documents ZIP (Strategy 2).

HOW TO USE Rates Log (only for storefront checkout rate scenarios):
1. Click "Rates Log" in the app sidebar
2. List of rate requests: each row has order ID, date, status
3. Click a row → expands to show request/response JSON

### ⚠️ eParcel vs MyPost Business Account Types
eParcel:
  - Higher-volume merchants
  - Domestic + international shipping
  - Extra Cover: up to $5,000 AUD
  - Supports Dangerous Goods (domestic only)
  - Services: T28 (Parcel Post), E86J (Express Post), PLT (Intl Economy)

MyPost Business:
  - Smaller-volume businesses
  - Domestic shipping ONLY
  - Extra Cover: up to $1,000 AUD
  - NO Dangerous Goods support
  - Services: Standard, Express

### ⚠️ Pickup Scheduling — Full Flow
1. Navigate to "PickUp" in the app sidebar
2. Click "Schedule Pickup" or equivalent button
3. Fill pickup details: date, time, location, package count
4. Submit → pickup confirmation number generated
5. Verify: pickup appears in list with "SUCCESS" status
""")

# ── Selective workflow guide trimmer ─────────────────────────────────────────

_WG_ALWAYS = [
    "All App Page URLs",
    "TWO DIFFERENT PRODUCTS",
    "How to Generate a Label",
    "How to Cancel a Label",
    "How to Regenerate a Label",
    "App's Own Shipping",
    "Settings Navigation",
    "Label Status Values",
    "Full Verification Flow by Scenario Type",
    "How to Access the Order Summary Page",
    "How to Verify Label and Documents",
]

_WG_CONDITIONAL: list[tuple[list[str], str]] = [
    (["signature on delivery", "authority to leave", "atl", "extra cover",
      "safe drop", "dangerous goods"],
     "SCENARIO GROUP A"),
    (["product dimension", "product weight", "product config", "appproducts",
      "dimensions on product", "product length", "product width"],
     "SCENARIO GROUP B"),
    (["return label", "generate return", "return package"],
     "SCENARIO GROUP D"),
    (["eparcel", "mypost", "account type", "mypost business"],
     "SCENARIO GROUP E"),
    (["signature on delivery", "authority to leave", "atl", "extra cover",
      "safe drop", "dangerous goods", "manual label", "generate label",
      "sidedock", "side dock"],
     "Manual Label Generation"),
    (["signature", "atl", "authority to leave", "extra cover", "safe drop",
      "dangerous goods"],
     "The SideDock"),
    (["product", "appproducts", "dimensions", "weight", "height", "length", "width"],
     "AU Post App — Product Config"),
    (["return label", "generate return"],
     "How to Generate a Return Label"),
    (["rates log", "rate log", "api log", "request json"],
     "How to View Rate Logs"),
    (["eparcel", "mypost", "account type", "extra cover limit",
      "dangerous goods", "5000", "1000"],
     "eParcel vs MyPost Business"),
    (["pickup", "pick up", "schedule pickup"],
     "Pickup Scheduling"),
    (["download document", "download documents", "verify json",
      "verify label", "label json", "print document"],
     "How to Verify Label and Documents"),
]


def _trim_workflow_guide(scenario: str) -> str:
    """Return only workflow guide sections relevant to this scenario."""
    s = scenario.lower()

    raw_sections = re.split(r"\n(?=###)", _APP_WORKFLOW_GUIDE)

    kept: list[str] = []
    for sec in raw_sections:
        sec_lower = sec.lower()

        if any(ah.lower() in sec_lower for ah in _WG_ALWAYS):
            kept.append(sec)
            continue

        for keywords, header_match in _WG_CONDITIONAL:
            if header_match.lower() in sec_lower:
                if any(kw in s for kw in keywords):
                    kept.append(sec)
                break

    result = "\n".join(kept) if kept else _APP_WORKFLOW_GUIDE

    # Safety net: if result is less than 35% of full guide, use full
    if len(result) < len(_APP_WORKFLOW_GUIDE) * 0.35:
        logger.warning("[guide] Trim too aggressive (%.0f%%) — falling back to full guide for '%s…'",
                       100 * len(result) / len(_APP_WORKFLOW_GUIDE), scenario[:50])
        return _APP_WORKFLOW_GUIDE

    saved = len(_APP_WORKFLOW_GUIDE) // 4 - len(result) // 4
    logger.debug("[guide] Trimmed workflow guide: saved ~%d tokens (%.0f%%) for scenario '%s…'",
                 saved, 100 * saved / (len(_APP_WORKFLOW_GUIDE) // 4), scenario[:50])
    return result


_DOMAIN_EXPERT_PROMPT = dedent("""\
    You are the domain expert for the PluginHive Australia Post Shopify app.
    A QA engineer is about to verify this scenario in the live app.

    SCENARIO: {scenario}
    FEATURE:  {card_name}

    {preconditions_section}

    Using the domain knowledge and code context below, answer these questions
    concisely (max 200 words total):

    1. EXPECTED BEHAVIOUR — What should happen in the UI when this works correctly?
    2. API SIGNALS — What AU Post/backend API calls or request fields should appear
       (e.g. "options.signature_on_delivery=true in createShipment request",
             "items[0].product_id=T28 for Parcel Post")?
    3. KEY THINGS TO CHECK — Specific UI elements, values, or network calls that
       confirm this scenario is implemented and working.

    Be specific. If the scenario mentions "Extra Cover = $500", explain exactly
    what that means and what JSON field to verify.

    DOMAIN KNOWLEDGE (PluginHive docs / AU Post API):
    {domain_context}

    CODE KNOWLEDGE (automation POM / backend):
    {code_context}

    Answer in plain text — no JSON, no headings, just 3 short paragraphs.
""")

_PLAN_PROMPT = dedent("""\
    You are a QA engineer verifying a feature in the AU Post Shopify App.

    SCENARIO: {scenario}
    APP URL:  {app_url}

{app_workflow_guide}

    DOMAIN EXPERT INSIGHT (what this feature should do + what API signals to watch):
    {expert_insight}

    CODE KNOWLEDGE (automation POM patterns + backend API):
    {code_context}

    IMPORTANT: We test WEB (desktop browser) ONLY. SKIP any scenario that involves mobile
    viewports, responsive breakpoints, or screen widths ≤ 768 px. If the scenario is
    mobile-only, set plan = "SKIP — mobile/responsive testing is out of scope"
    and order_action = "none".

    Plan how to verify this. The browser will ALWAYS start at the app home page.

    Navigation rules:
    - For label generation scenarios (generate new label) → nav_clicks: ["Orders"]
    - For verifying an EXISTING label / downloading documents → nav_clicks: ["Shipping"]
    - For app settings scenarios → nav_clicks: ["Settings"]
    - For product configuration (dimensions, signature, extra cover on product)
      → nav_clicks: ["AppProducts"]
    - For adding a new product → nav_clicks: ["ShopifyProducts"]
    - ONLY use these exact values: "Orders", "Shipping", "Settings", "PickUp",
      "AppProducts", "ShopifyProducts", "FAQ", "Rates Log"

    ORDER JUDGMENT — pick order_action:

    | Scenario contains ANY of these phrases                                          | order_action          |
    |---------------------------------------------------------------------------------|-----------------------|
    | "cancel label", "return label", "download document", "verify label",            |                       |
    | "print document", "label shows", "next/previous order", "order summary nav",    | existing_fulfilled    |
    | "address update", "update address", "regenerate", "re-generate label"           |                       |
    |---------------------------------------------------------------------------------|-----------------------|
    | "generate label", "create label", "auto-generate label", "manual label",        |                       |
    | "signature on delivery", "authority to leave", "atl", "extra cover",            | create_new            |
    | "safe drop", "dangerous goods", "domestic label", "international label",        |                       |
    | "parcel post", "express post", "eparcel label", "mypost label"                  |                       |
    |---------------------------------------------------------------------------------|-----------------------|
    | "bulk", "50 orders", "100 orders", "batch label", "select all orders",          | create_bulk           |
    | "auto-generate labels", "bulk print"                                            |                       |
    |---------------------------------------------------------------------------------|-----------------------|
    | "settings", "configure", "pickup", "schedule pickup", "rates log",              | none                  |
    | "navigation", "order grid", "filter orders", "tab shows", "sidebar"             |                       |

    When in doubt between create_new and existing_fulfilled → prefer create_new.
    When in doubt between existing_fulfilled and existing_unfulfilled → prefer existing_fulfilled.

    Respond ONLY in JSON:
    {{
      "app_path": "",
      "look_for": ["UI element or behaviour that proves this scenario is implemented"],
      "api_to_watch": ["API endpoint path fragment to watch in network calls"],
      "nav_clicks": ["e.g. Orders | Shipping | Settings | AppProducts | ShopifyProducts | PickUp | FAQ | Rates Log"],
      "plan": "one sentence: how you will verify this scenario",
      "order_action": "none" | "existing_fulfilled" | "existing_unfulfilled" | "create_new" | "create_bulk"
    }}
""")

_STEP_PROMPT = dedent("""\
    You are verifying this AC scenario in the AU Post Shopify App.

    SCENARIO: {scenario}

    DOMAIN EXPERT INSIGHT (what this feature does + what to look for):
    {expert_insight}

    APP WORKFLOW GUIDE:
{app_workflow_guide}

    CURRENT PAGE: {url}
    ACCESSIBILITY TREE (what is visible):
    {ax_tree}

    NETWORK CALLS SEEN SO FAR:
    {network_calls}

    STEPS TAKEN SO FAR ({step_num}/{max_steps}):
    {steps_taken}

    CODE KNOWLEDGE:
    {code_context}

    Decide your NEXT action. Respond ONLY in JSON — no extra text:
    {{
      "action":       "click" | "fill" | "select" | "scroll" | "observe" | "navigate" | "verify" | "qa_needed" | "switch_tab" | "close_tab" | "download_zip" | "download_file" | "reset_order",
      "target":       "<exact element name from accessibility tree — required for click/fill/select/download_zip/download_file>",
      "value":        "<text to type (fill) OR option to select (select)>",
      "path":         "<relative path only e.g. 'shopify' or 'settings' — NEVER put a full URL here — required for navigate>",
      "description":  "one sentence: what you are doing and why",
      "verdict":      "pass | fail | partial  — ONLY when action=verify",
      "finding":      "what you observed      — ONLY when action=verify",
      "question":     "your question for QA   — ONLY when action=qa_needed",
      "order_action": "<required ONLY for reset_order — one of: existing_fulfilled | existing_unfulfilled | create_new | create_bulk>"
    }}

    Rules:
    - action=verify      → you have clear evidence to give a verdict
    - action=qa_needed   → you genuinely cannot locate the feature after looking carefully
    - action=reset_order → use ONLY when you discover you have the WRONG test data mid-run
                           (e.g. you need an order with a label but got an unfulfilled order)
                           Set "order_action" to what you actually need.
    - action=select      → use for ANY dropdown or combobox (packing method, weight unit, etc.)
                           target = dropdown label name, value = option text to select
    - action=fill        → use ONLY for free-text inputs (weight, dimensions, declared value)
    - action=click       → use for buttons, checkboxes, toggles, tabs, links
    - ONLY reference targets that literally appear in the accessibility tree above
    - Do NOT explore unrelated sections of the app
    - action=observe on first step to capture visible elements before interacting

    TWO COMPLETELY DIFFERENT PRODUCTS PAGES:
    - AppProducts  →  <app_base>/products  (AU Post app inside iframe)
        USE FOR: configure AU Post settings on an existing product
        → signature, ATL, extra cover, safe drop, dangerous goods, dimensions
        ⚠️ NO "Add product" button — cannot create products here
    - ShopifyProducts  →  admin.shopify.com/store/<store>/products
        USE FOR: create new product, edit Shopify fields
        ⚠️ This is NOT the AU Post app — no AU Post-specific fields here

    Document verification rules:
    - To verify LABEL EXISTS: look for "label generated" status badge (Strategy 1)
    - To verify JSON FIELD VALUES (signature, ATL, extra cover, service code):
      Strategy 2: More Actions → download_zip target="Download Documents"
      → ZIP with request/response JSON → verify field values
    - To verify VISUAL LABEL / TRACKING NUMBER / DOCUMENTS PRESENT:
      Strategy 3: click "Print Documents" → new tab → switch_tab → screenshot → verify → close_tab
    - After download_zip: next step sees JSON in context → action=verify directly
""")

_SUMMARY_PROMPT = dedent("""\
    QA lead summary for feature: {card_name}

    Scenario results:
    {results}

    Write 2-3 sentences. Call out any failures or blockers for sign-off.
""")


# ── Browser helpers ───────────────────────────────────────────────────────────

def get_auto_app_url() -> str:
    """Auto-detect app URL from automation repo .env (AUPOST_APP_URL or STORE)."""
    if not _ENV_FILE.exists():
        return ""
    env_vals: dict[str, str] = {}
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        env_vals[k.strip()] = v.strip().strip('"').strip("'")

    # Prefer explicit full app URL
    if env_vals.get("AUPOST_APP_URL"):
        return env_vals["AUPOST_APP_URL"]

    # Fallback: build from STORE slug
    store = env_vals.get("STORE", "")
    if store and not store.startswith("your-"):
        store = store.replace(".myshopify.com", "")
        app_slug = env_vals.get("AUPOST_APP_SLUG", "australia-post-rates-labels")
        return f"https://admin.shopify.com/store/{store}/apps/{app_slug}"

    return ""


def _auth_ctx_kwargs() -> dict:
    kw: dict = {"viewport": {"width": 1400, "height": 1000}}
    if _AUTH_JSON.exists():
        try:
            json.loads(_AUTH_JSON.read_text(encoding="utf-8"))
            kw["storage_state"] = str(_AUTH_JSON)
        except Exception:
            pass
    return kw


def _ax_tree(page) -> str:
    """
    Accessibility tree as readable text.
    Captures BOTH the main Shopify page AND the AU Post app iframe.
    Uses a 10s thread timeout per snapshot so large pages never hang.
    """
    import concurrent.futures as _cf

    lines: list[str] = []

    def _walk(n: dict, d: int = 0, prefix: str = "") -> None:
        if d > 6 or len(lines) > 250:
            return
        role, name = n.get("role", ""), n.get("name", "")
        skip = {"generic", "none", "presentation", "document", "group", "list", "region"}
        if role and name and role not in skip:
            ln = f"{'  ' * d}{prefix}{role}: '{name}'"
            c = n.get("checked")
            if c is not None:
                ln += f" [checked={c}]"
            v = n.get("value", "")
            if v and role in ("textbox", "combobox"):
                ln += f" [value='{v[:30]}']"
            lines.append(ln)
        for ch in n.get("children", []):
            _walk(ch, d + 1, prefix)

    def _snapshot_with_timeout(fn, timeout=10):
        with _cf.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(fn)
            try:
                return fut.result(timeout=timeout)
            except (_cf.TimeoutError, Exception):
                return None

    # 1. Main page (Shopify admin chrome)
    try:
        ax = _snapshot_with_timeout(lambda: page.accessibility.snapshot(interesting_only=True))
        if ax:
            _walk(ax)
    except Exception as e:
        lines.append(f"(main page snapshot error: {e})")

    # 2. AU Post app iframe
    try:
        for frame in page.frames:
            if frame is page.main_frame:
                continue
            frame_url = frame.url or ""
            if not frame_url or ("shopify" not in frame_url and "pluginhive" not in frame_url
                                 and "apps" not in frame_url):
                continue
            try:
                frame_ax = _snapshot_with_timeout(
                    lambda f=frame: f.accessibility.snapshot(interesting_only=True)
                )
                if frame_ax:
                    lines.append(f"\n--- [APP IFRAME: {frame_url[:60]}] ---")
                    _walk(frame_ax, prefix="")
                    lines.append("--- [END IFRAME] ---")
            except Exception:
                pass
    except Exception:
        pass

    return "\n".join(lines) or "(no interactive elements)"


def _screenshot(page) -> str:
    """Base64 PNG of current page."""
    try:
        raw = page.screenshot(full_page=False, scale="css")
        return base64.standard_b64encode(raw).decode()
    except Exception:
        try:
            return base64.standard_b64encode(page.screenshot(full_page=False)).decode()
        except Exception:
            return ""


_NET_JS = """() =>
    performance.getEntriesByType('resource')
      .filter(e => ['xmlhttprequest','fetch'].includes(e.initiatorType))
      .slice(-40).map(e => e.name)
"""

def _network(page, endpoints: list[str]) -> list[str]:
    """
    Recent API/XHR calls matching endpoint paths.
    Checks BOTH the main page AND iframe frames.
    """
    all_entries: list[str] = []

    try:
        entries = page.evaluate(_NET_JS)
        all_entries.extend(entries or [])
    except Exception:
        pass

    try:
        for frame in page.frames:
            if frame is page.main_frame:
                continue
            frame_url = frame.url or ""
            if not frame_url or ("shopify" not in frame_url and "pluginhive" not in frame_url
                                 and "apps" not in frame_url):
                continue
            try:
                entries = frame.evaluate(_NET_JS)
                all_entries.extend(entries or [])
            except Exception:
                pass
    except Exception:
        pass

    seen: set[str] = set()
    hits: list[str] = []
    for e in all_entries:
        if e not in seen:
            seen.add(e)
            hits.append(e)

    if endpoints:
        return [e for e in hits if any(ep in e for ep in endpoints)]
    return [e for e in hits if "/api/" in e or "auspost" in e.lower()
            or "pluginhive" in e.lower() or "australia-post" in e.lower()]


def _app_frame(page):
    return page.frame_locator('iframe[name="app-iframe"]')


def _do_action(page, action: dict, app_base: str) -> bool:
    """Execute a Claude-decided browser action. Returns True on success."""
    atype  = action.get("action", "observe")
    target = action.get("target", "").strip()
    value  = action.get("value", "")
    path   = action.get("path", "").strip("/")

    if atype == "navigate":
        if not path:
            url = app_base
        elif path.startswith("http://") or path.startswith("https://"):
            url = path
        elif "admin.shopify.com" in path or "myshopify.com" in path:
            url = "https://" + path.lstrip("/")
        elif path.startswith("store/"):
            url = "https://admin.shopify.com/" + path
        else:
            url = f"{app_base}/{path}"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(800)
            return True
        except Exception:
            return False

    if atype in ("observe", "verify", "qa_needed"):
        return True

    if atype == "scroll":
        try:
            page.evaluate("window.scrollBy(0, 400)")
        except Exception:
            pass
        return True

    if atype == "switch_tab":
        try:
            ctx = page.context
            pages = ctx.pages
            if len(pages) > 1:
                new_tab = pages[-1]
                new_tab.bring_to_front()
                new_tab.wait_for_load_state("domcontentloaded", timeout=10_000)
                action["_new_page"] = new_tab
            return True
        except Exception as e:
            logger.debug("switch_tab failed: %s", e)
            return False

    if atype == "close_tab":
        try:
            ctx = page.context
            if len(ctx.pages) > 1:
                page.close()
                main_page = ctx.pages[0]
                main_page.bring_to_front()
                action["_new_page"] = main_page
            return True
        except Exception as e:
            logger.debug("close_tab failed: %s", e)
            return False

    frame = _app_frame(page)

    if atype == "download_zip":
        try:
            tmp_dir  = tempfile.mkdtemp(prefix="sav_zip_")
            zip_path = os.path.join(tmp_dir, "aupost_download.zip")

            el_to_click = None
            for fn in [
                lambda: frame.get_by_role("button", name=target, exact=False),
                lambda: frame.get_by_role("link",   name=target, exact=False),
                lambda: frame.get_by_text(target, exact=False),
                lambda: page.get_by_role("button",  name=target, exact=False),
                lambda: page.get_by_role("link",    name=target, exact=False),
                lambda: page.get_by_text(target, exact=False),
            ]:
                try:
                    el = fn()
                    if el.count() > 0:
                        el_to_click = el.first
                        break
                except Exception:
                    continue

            if el_to_click is None:
                logger.debug("download_zip: target '%s' not found in page/iframe", target)
                return False

            with page.expect_download(timeout=30_000) as dl_info:
                el_to_click.click(timeout=5_000)

            dl = dl_info.value
            dl.save_as(zip_path)
            page.wait_for_timeout(500)

            extracted: dict[str, object] = {}
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for name in zf.namelist():
                        ext = name.rsplit(".", 1)[-1].lower()
                        if ext == "json":
                            raw_text = zf.read(name).decode("utf-8", errors="replace")
                            try:
                                extracted[name] = json.loads(raw_text)
                            except Exception:
                                extracted[name] = raw_text
                        elif ext in ("csv", "txt", "xml", "log"):
                            raw_text = zf.read(name).decode("utf-8", errors="replace")
                            extracted[name] = raw_text[:3000]
                        else:
                            info = zf.getinfo(name)
                            extracted[name] = f"({ext.upper()} binary — {info.file_size:,} bytes)"
            except Exception as zip_err:
                logger.debug("ZIP extraction error: %s", zip_err)
                extracted["_error"] = str(zip_err)

            action["_zip_content"] = extracted
            logger.info(
                "download_zip: extracted %d file(s) from ZIP — %s",
                len(extracted), list(extracted.keys()),
            )

            try:
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

            return True

        except Exception as e:
            logger.debug("download_zip failed: %s", e)
            return False

    if atype == "download_file":
        try:
            tmp_dir  = tempfile.mkdtemp(prefix="sav_file_")
            tmp_path = os.path.join(tmp_dir, "aupost_download")

            el_to_click = None
            for fn in [
                lambda: frame.get_by_role("button", name=target, exact=False),
                lambda: frame.get_by_role("link",   name=target, exact=False),
                lambda: frame.get_by_text(target, exact=False),
                lambda: page.get_by_role("button",  name=target, exact=False),
                lambda: page.get_by_role("link",    name=target, exact=False),
                lambda: page.get_by_text(target, exact=False),
            ]:
                try:
                    el = fn()
                    if el.count() > 0:
                        el_to_click = el.first
                        break
                except Exception:
                    continue

            if el_to_click is None:
                logger.debug("download_file: target '%s' not found", target)
                return False

            with page.expect_download(timeout=30_000) as dl_info:
                el_to_click.click(timeout=5_000)

            dl = dl_info.value
            filename = dl.suggested_filename or "download"
            save_path = os.path.join(tmp_dir, filename)
            dl.save_as(save_path)
            page.wait_for_timeout(500)

            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            content: dict = {"filename": filename}

            if ext == "csv":
                import csv as _csv
                try:
                    raw = Path(save_path).read_text(encoding="utf-8-sig", errors="replace")
                    lines = raw.splitlines()
                    reader = _csv.reader(lines)
                    rows = list(reader)
                    headers = rows[0] if rows else []
                    sample  = rows[1:6]
                    content["headers"]    = headers
                    content["row_count"]  = len(rows) - 1
                    content["sample_rows"] = sample
                    content["raw_preview"] = "\n".join(lines[:20])
                    logger.info("download_file: CSV '%s' — %d rows, headers: %s",
                                filename, len(rows) - 1, headers)
                except Exception as csv_err:
                    content["raw_preview"] = Path(save_path).read_text(
                        encoding="utf-8", errors="replace")[:3000]
                    logger.debug("CSV parse error: %s", csv_err)

            elif ext in ("xlsx", "xls"):
                size = os.path.getsize(save_path)
                content["note"] = f"Excel file ({size:,} bytes)"
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(save_path, read_only=True, data_only=True)
                    ws = wb.active
                    rows = list(ws.iter_rows(values_only=True))
                    content["headers"]    = [str(c) for c in (rows[0] if rows else [])]
                    content["row_count"]  = len(rows) - 1
                    content["sample_rows"] = [[str(c) for c in r] for r in rows[1:6]]
                    wb.close()
                except ImportError:
                    pass

            elif ext == "pdf":
                size = os.path.getsize(save_path)
                content["note"] = f"PDF file ({size:,} bytes)"

            else:
                size = os.path.getsize(save_path)
                raw  = Path(save_path).read_bytes()
                try:
                    content["raw_preview"] = raw.decode("utf-8", errors="replace")[:2000]
                except Exception:
                    content["note"] = f"{ext.upper()} file ({size:,} bytes)"

            action["_file_content"] = content
            logger.info("download_file: downloaded '%s' — %s", filename, list(content.keys()))

            try:
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

            return True

        except Exception as e:
            logger.debug("download_file failed: %s", e)
            return False

    if not target:
        return False

    if atype == "click":
        for fn in [
            lambda: frame.get_by_role("button",   name=target, exact=False),
            lambda: frame.get_by_role("checkbox", name=target, exact=False),
            lambda: frame.get_by_role("switch",   name=target, exact=False),
            lambda: frame.get_by_role("link",     name=target, exact=False),
            lambda: frame.get_by_role("tab",      name=target, exact=False),
            lambda: frame.get_by_text(target, exact=False),
            lambda: page.get_by_role("button", name=target, exact=False),
            lambda: page.get_by_text(target, exact=False),
        ]:
            try:
                el = fn()
                if el.count() > 0:
                    el.first.click(timeout=5_000)
                    page.wait_for_timeout(400)
                    return True
            except Exception:
                continue
        logger.debug("Click target not found: '%s'", target)
        return False

    if atype == "fill":
        for fn in [
            lambda: frame.get_by_label(target, exact=False),
            lambda: frame.get_by_placeholder(target, exact=False),
            lambda: frame.get_by_role("textbox", name=target, exact=False),
        ]:
            try:
                el = fn()
                if el.count() > 0:
                    el.first.clear()
                    el.first.fill(value, timeout=5_000)
                    return True
            except Exception:
                continue
        return False

    if atype == "select":
        if not value:
            logger.debug("select action requires value — skipping")
            return False

        for fn in [
            lambda: frame.get_by_label(target, exact=False),
            lambda: frame.get_by_role("combobox", name=target, exact=False),
            lambda: page.get_by_label(target, exact=False),
            lambda: page.get_by_role("combobox", name=target, exact=False),
        ]:
            try:
                el = fn()
                if el.count() > 0:
                    try:
                        el.first.select_option(value, timeout=5_000)
                        page.wait_for_timeout(400)
                        return True
                    except Exception:
                        pass
                    try:
                        el.first.click(timeout=5_000)
                        page.wait_for_timeout(300)
                        for opt_fn in [
                            lambda v=value: frame.get_by_role("option", name=v, exact=False),
                            lambda v=value: frame.get_by_text(v, exact=False),
                            lambda v=value: page.get_by_role("option", name=v, exact=False),
                            lambda v=value: page.get_by_text(v, exact=False),
                        ]:
                            opt = opt_fn()
                            if opt.count() > 0:
                                opt.first.click(timeout=3_000)
                                page.wait_for_timeout(400)
                                return True
                    except Exception:
                        pass
            except Exception:
                continue

        logger.debug("select: could not find dropdown '%s' or option '%s'", target, value)
        return False

    return True


# ── Code RAG helpers ──────────────────────────────────────────────────────────

def _extract_ui_elements(code_docs: list) -> list[str]:
    """Extract UI element names from POM code."""
    elements: list[str] = []
    seen: set[str] = set()

    patterns = [
        (r"getByRole\(['\"](\w+)['\"][\s\S]*?name:\s*['\"]([^'\"]+)['\"]",
         lambda m: f"{m.group(1)}: '{m.group(2)}'"),
        (r"getByLabel\(['\"]([^'\"]+)['\"]",
         lambda m: f"label: '{m.group(1)}'"),
        (r"getByPlaceholder\(['\"]([^'\"]+)['\"]",
         lambda m: f"placeholder: '{m.group(1)}'"),
        (r"getByText\(['\"]([^'\"]+)['\"]",
         lambda m: f"text: '{m.group(1)}'"),
    ]

    for doc in code_docs:
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        for pattern, formatter in patterns:
            try:
                for match in re.finditer(pattern, content):
                    entry = formatter(match)
                    if entry not in seen:
                        seen.add(entry)
                        elements.append(entry)
                        if len(elements) >= 25:
                            return elements
            except Exception:
                continue

    return elements


def _extract_backend_fields(code_docs: list, scenario: str) -> list[str]:
    """Extract backend field names from schema definitions."""
    fields: list[str] = []
    seen: set[str] = set()

    schema_pattern = re.compile(
        r"\b(\w+):\s*\{?\s*(?:type:\s*)?(?:String|Number|Boolean|Schema\.Types|mongoose\.Schema\.Types)"
    )
    assignment_pattern = re.compile(
        r"\b(is[A-Z]\w+|[a-z]+(?:[A-Z][a-z]+)+):\s*(?:false|true|0|null|''|\"\"|\[)")

    for doc in code_docs:
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        for pattern in (schema_pattern, assignment_pattern):
            try:
                for match in pattern.finditer(content):
                    f = match.group(1)
                    _SKIP = {
                        "get", "set", "use", "app", "res", "req", "err",
                        "type", "ref", "default", "required", "unique", "index",
                        "min", "max", "trim", "enum", "validate",
                    }
                    if len(f) < 3 or f in _SKIP:
                        continue
                    if f not in seen:
                        seen.add(f)
                        fields.append(f)
                        if len(fields) >= 15:
                            return fields
            except Exception:
                continue

    return fields


def _extract_api_endpoints(code_docs: list) -> list[str]:
    """Extract API endpoint URLs from frontend code."""
    endpoints: list[str] = []
    seen: set[str] = set()

    patterns = [
        re.compile(r"axios\.\w+\(['\"](/api/[^'\"]+)['\"]"),
        re.compile(r"['\"](/api/v\d[^'\"]+)['\"]"),
    ]

    for doc in code_docs:
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        for pattern in patterns:
            try:
                for match in pattern.finditer(content):
                    ep = match.group(1).rstrip("/")
                    if ep not in seen:
                        seen.add(ep)
                        endpoints.append(ep)
                        if len(endpoints) >= 8:
                            return endpoints
            except Exception:
                continue

    return endpoints


def _code_context(scenario: str, card_name: str) -> str:
    """Query automation POM + backend API + QA knowledge for structured context."""
    parts: list[str] = []
    query = f"{card_name} {scenario}"

    pom_docs: list = []
    be_docs: list = []
    fe_docs: list = []

    try:
        from rag.code_indexer import search_code

        label_docs = search_code(
            "generate label More Actions click order Shopify navigate",
            k=5, source_type="automation",
        )
        scenario_pom_docs = search_code(query, k=5, source_type="automation")
        pom_docs = (label_docs or []) + (scenario_pom_docs or [])
        be_docs  = search_code(query, k=3, source_type="backend") or []

        try:
            fe_docs = search_code(query, k=3, source_type="frontend") or []
        except Exception:
            fe_docs = []

    except Exception as e:
        logger.debug("Code RAG error: %s", e)

    # Section 1: UI elements
    try:
        ui_elements = _extract_ui_elements(pom_docs)
        if ui_elements:
            parts.append(
                "=== KNOWN UI ELEMENTS (from automation POM — use EXACT names for clicks/fills) ===\n"
                + "\n".join(ui_elements)
            )
        elif pom_docs:
            snippets = "\n---\n".join(
                f"[{d.metadata.get('file_path', '').split('/')[-1]}]\n{d.page_content[:600]}"
                for d in pom_docs[:5]
            )
            parts.append(f"=== AUTOMATION WORKFLOW (from POM) ===\n{snippets}")
    except Exception as e:
        logger.debug("UI element extraction error: %s", e)

    # Section 2: Verification fields
    try:
        fields = _extract_backend_fields(be_docs, scenario)
        if fields:
            parts.append(
                "=== VERIFICATION FIELDS (from backend — check these in downloaded ZIP JSON) ===\n"
                + ", ".join(fields)
            )
        elif be_docs:
            snippets = "\n---\n".join(d.page_content[:400] for d in be_docs)
            parts.append(f"=== Backend API ===\n{snippets}")
    except Exception as e:
        logger.debug("Backend field extraction error: %s", e)

    # Section 3: API endpoints
    try:
        endpoints = _extract_api_endpoints(fe_docs + be_docs)
        if endpoints:
            parts.append(
                "=== API ENDPOINTS TO WATCH (from frontend) ===\n"
                + "\n".join(endpoints)
            )
    except Exception as e:
        logger.debug("API endpoint extraction error: %s", e)

    # Section 4: Domain knowledge
    try:
        from rag.vectorstore import search as qs
        docs = qs(query, k=3)
        if docs:
            snippets = "\n---\n".join(d.page_content[:400] for d in docs)
            parts.append(f"=== DOMAIN KNOWLEDGE ===\n{snippets}")
    except Exception as e:
        logger.debug("QA knowledge RAG error: %s", e)

    return "\n\n".join(parts) if parts else "(no code context indexed yet)"


# ── Domain Expert ─────────────────────────────────────────────────────────────

def _ask_domain_expert(scenario: str, card_name: str, claude: "ChatAnthropic") -> str:
    """Ask the domain expert what this scenario should do."""
    query     = f"{card_name} {scenario}"
    api_query = f"{scenario} API request field AU Post Australia Post"
    domain_sections: list[str] = []
    code_parts:      list[str] = []

    _DOMAIN_SOURCES = [
        ("pluginhive_docs",  query,     "PluginHive Official Documentation",     4),
        ("pluginhive_seeds", query,     "PluginHive FAQ & Guides",               3),
        ("wiki",             query,     "Internal Wiki (Product & Engineering)", 5),
        ("sheets",           query,     "Test Cases & Acceptance Criteria",      3),
    ]

    try:
        from rag.vectorstore import search_filtered
        for src_type, q, label, k in _DOMAIN_SOURCES:
            try:
                docs = search_filtered(q, k=k, source_type=src_type)
                if docs:
                    def _fmt(d) -> str:
                        cat = d.metadata.get("category", "")
                        prefix = f"[{cat}] " if cat else ""
                        return f"{prefix}{d.page_content[:450]}"
                    chunks = "\n\n".join(_fmt(d) for d in docs)
                    domain_sections.append(f"[{label}]\n{chunks}")
            except Exception as e:
                logger.debug("Domain RAG sub-query failed (source_type=%s): %s", src_type, e)
    except ImportError as e:
        logger.debug("search_filtered not available — falling back: %s", e)
        try:
            from rag.vectorstore import search as rag_search
            docs = rag_search(query, k=8)
            if docs:
                domain_sections.append("\n\n".join(
                    f"[{d.metadata.get('source_type','doc')}] {d.page_content[:450]}"
                    for d in docs
                ))
        except Exception as e2:
            logger.debug("Fallback domain RAG also failed: %s", e2)

    try:
        from rag.code_indexer import search_code
        auto_docs = search_code(query, k=5, source_type="automation")
        if auto_docs:
            code_parts.append("\n---\n".join(
                f"[{d.metadata.get('file_path','').split('/')[-1]}]\n{d.page_content[:500]}"
                for d in auto_docs
            ))
        be_docs = search_code(query, k=4, source_type="backend")
        if be_docs:
            code_parts.append("\n---\n".join(
                f"[{d.metadata.get('file_path','').split('/')[-1]}]\n{d.page_content[:400]}"
                for d in be_docs
            ))
    except Exception as e:
        logger.debug("Code RAG error in expert: %s", e)

    domain_context = "\n\n---\n\n".join(domain_sections) or "(no domain knowledge indexed)"
    code_context   = "\n\n".join(code_parts)              or "(no code indexed)"

    preconditions = _get_preconditions(scenario)
    preconditions_section = (
        f"KNOWN PRE-REQUIREMENTS (from automation spec files):\n{preconditions}"
        if preconditions else ""
    )

    prompt = _DOMAIN_EXPERT_PROMPT.format(
        scenario=scenario,
        card_name=card_name,
        domain_context=domain_context[:4000],
        code_context=code_context[:3000],
        preconditions_section=preconditions_section,
    )

    try:
        resp = claude.invoke([HumanMessage(content=prompt)])
        answer = resp.content.strip()
        if isinstance(answer, list):
            answer = " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in answer)
        return answer[:1200]
    except Exception as e:
        logger.warning("Domain expert query failed: %s", e)
        return "(domain expert unavailable)"


# ── Claude helpers ────────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    """Extract JSON from Claude's response."""
    clean = re.sub(r"```(?:json)?\n?", "", raw.strip()).strip().rstrip("`").strip()
    try:
        return json.loads(clean)
    except Exception:
        pass

    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    return {}


def _extract_scenarios(ac: str, claude: ChatAnthropic) -> list[str]:
    resp = claude.invoke([HumanMessage(content=_EXTRACT_PROMPT.format(ac=ac))])
    raw  = resp.content.strip()
    data = _parse_json(raw)
    if isinstance(data, list):
        return data
    return [
        ln.strip("- ").strip()
        for ln in ac.splitlines()
        if ln.strip().startswith(("Given", "When", "Scenario", "Then", "-"))
    ][:12]


def _validate_order_action(scenario: str, claude_choice: str) -> str:
    """Python safety net: override clearly wrong order_action choices."""
    s = scenario.lower()

    _fulfilled_signals = [
        "cancel label", "cancel the label", "after cancellation", "after label cancel",
        "address update", "update address", "update the address", "update shipping address",
        "updated address", "regenerate", "re-generate",
        "return label", "generate return", "download document",
        "verify label", "print document", "label shows", "label generated",
        "next/previous order", "order summary nav",
    ]
    if any(kw in s for kw in _fulfilled_signals):
        if claude_choice in ("create_new", "existing_unfulfilled", "none"):
            logger.info(
                "[order_validate] Overriding '%s' → 'existing_fulfilled' "
                "(scenario signals a label must exist)", claude_choice
            )
            return "existing_fulfilled"

    _new_order_signals = [
        "generate label", "create label", "auto-generate label", "manual label",
        "signature on delivery", "authority to leave", " atl ",
        "extra cover", "safe drop", "dangerous goods",
        "domestic label", "international label",
        "parcel post", "express post", "eparcel label", "mypost label",
    ]
    if any(kw in s for kw in _new_order_signals):
        if claude_choice == "none":
            logger.info(
                "[order_validate] Overriding 'none' → 'create_new' "
                "(scenario signals label generation)"
            )
            return "create_new"

    _bulk_signals = ["bulk", "50 orders", "100 orders", "batch label", "select all orders",
                     "auto-generate labels", "bulk print"]
    if any(kw in s for kw in _bulk_signals):
        if claude_choice in ("none", "create_new", "existing_fulfilled"):
            logger.info("[order_validate] Overriding '%s' → 'create_bulk'", claude_choice)
            return "create_bulk"

    return claude_choice


def _setup_order_ctx(order_action: str, scenario: str, base_ctx: str) -> str:
    """Build the order context prefix for a given order_action."""
    from pipeline.order_creator import resolve_order

    if order_action == "create_bulk":
        orders = resolve_order(scenario, "create_bulk")
        if orders and isinstance(orders, list):
            names = [o["name"] for o in orders]
            return (
                f"BULK ORDERS CREATED: {len(orders)} fresh unfulfilled orders → {names}\n"
                f"Ready in Shopify admin → Orders list (Unfulfilled tab).\n"
                f"Flow: select all → Actions → Auto-Generate Labels\n\n" + base_ctx
            )
        return ("ORDER STRATEGY: Use existing unfulfilled orders in Shopify admin → "
                "Orders → Unfulfilled tab.\n\n" + base_ctx)

    if order_action == "create_new":
        order = resolve_order(scenario, "create_new")
        if order and isinstance(order, dict):
            return (
                f"FRESH ORDER CREATED: {order.get('name')} (id: {order.get('id')}) — "
                f"unfulfilled, ready for label generation. "
                f"Find it in Shopify admin → Orders → most recent order at the top.\n\n" + base_ctx
            )
        return ("ORDER STRATEGY: Use an existing UNFULFILLED order. "
                "Shopify admin LEFT sidebar → Orders → first unfulfilled order.\n\n" + base_ctx)

    if order_action == "existing_unfulfilled":
        return ("ORDER STRATEGY: Use an existing UNFULFILLED order. "
                "Shopify admin LEFT sidebar → Orders → first unfulfilled order in list.\n\n"
                + base_ctx)

    if order_action == "existing_fulfilled":
        return ("ORDER STRATEGY: Use an order that already HAS a label generated. "
                "App sidebar → Shipping → Label Generated tab → click first order row.\n\n"
                + base_ctx)

    # none
    return base_ctx


def _get_preconditions(scenario: str) -> str:
    """
    Returns hardcoded pre-requirements for known AU Post scenario types.
    Based on real automation spec files — exact flows, product names, JSON fields.
    Returns empty string for unknown scenarios (RAG + domain expert handle those).
    """
    s = scenario.lower()

    if "signature on delivery" in s or ("signature" in s and "atl" not in s
                                         and "authority" not in s):
        return dedent("""\
            PRE-REQUIREMENTS (AU Post — Signature on Delivery):
            1. order_action: create_new  (fresh Shopify order)
            FLOW during Manual Label:
            - SideDock: check 'Signature on Delivery' checkbox
              ⚠️ Cannot combine with Authority to Leave
            VERIFY via Download Documents ZIP (Strategy 2):
            - More Actions → Download Documents → ZIP extracted
            - JSON must contain: options.signature_on_delivery = true
            CLEANUP: Not required (SideDock settings apply per-label only)""")

    if "authority to leave" in s or " atl " in s or s.endswith("atl"):
        return dedent("""\
            PRE-REQUIREMENTS (AU Post — Authority to Leave / ATL):
            1. order_action: create_new  (fresh Shopify order)
            FLOW during Manual Label:
            - SideDock: check 'Authority to Leave' checkbox
              ⚠️ Cannot combine with Signature on Delivery
            VERIFY via Download Documents ZIP (Strategy 2):
            - More Actions → Download Documents → ZIP extracted
            - JSON must contain: options.authority_to_leave = true
            CLEANUP: Not required (SideDock settings apply per-label only)""")

    if "extra cover" in s:
        # Try to extract declared value from scenario text
        import re as _re
        amount_match = _re.search(r"\$?\s*(\d+(?:\.\d+)?)", scenario)
        amount = amount_match.group(1) if amount_match else "500"
        return dedent(f"""\
            PRE-REQUIREMENTS (AU Post — Extra Cover):
            1. order_action: create_new  (fresh Shopify order)
            FLOW during Manual Label:
            - SideDock: check 'Extra Cover' checkbox → fill declared value = '{amount}' (AUD)
              Max: $5,000 AUD (eParcel) / $1,000 AUD (MyPost Business)
            VERIFY via Download Documents ZIP (Strategy 2):
            - More Actions → Download Documents → ZIP extracted
            - JSON must contain: options.extra_cover.amount = {amount}
            CLEANUP: Not required (SideDock settings apply per-label only)""")

    if "safe drop" in s:
        return dedent("""\
            PRE-REQUIREMENTS (AU Post — Safe Drop):
            1. order_action: create_new  (fresh Shopify order)
            FLOW during Manual Label:
            - SideDock: check 'Safe Drop' checkbox
            VERIFY via Download Documents ZIP (Strategy 2):
            - More Actions → Download Documents → ZIP extracted
            - JSON must contain: options.safe_drop = true (or similar field)
            CLEANUP: Not required (SideDock settings apply per-label only)""")

    if "dangerous goods" in s or "dangerous" in s:
        return dedent("""\
            PRE-REQUIREMENTS (AU Post — Dangerous Goods):
            ⚠️ Dangerous Goods is eParcel DOMESTIC ONLY — NOT available for MyPost Business.
            1. order_action: create_new  (fresh Shopify order with AU domestic address)
            FLOW during Manual Label:
            - SideDock: check 'Dangerous Goods' checkbox (only visible for eParcel domestic)
            VERIFY via Download Documents ZIP (Strategy 2):
            - More Actions → Download Documents → ZIP extracted
            - JSON must contain: items[0].contains_dangerous_goods = true
            CLEANUP: Not required (SideDock settings apply per-label only)""")

    if "return label" in s or "generate return" in s:
        return dedent("""\
            PRE-REQUIREMENTS (AU Post — Return Label):
            order_action: existing_fulfilled  (need an order that already has a label)
            FLOW (WAY A — from inside the app):
            1. App sidebar → Shipping → Label Generated tab → click first order
            2. Click 'Return packages' tab
            3. Click 'Return Packages' button
            4. Enter return quantity (default 1)
            5. Click 'Refresh Rates' → rates load
            6. Select service radio button
            7. Click 'Generate Return Label'
            VERIFY: 'SUCCESS' badge + 'Download Label' link visible
            FLOW (WAY B — from Shopify admin):
            1. Shopify Orders → click order → More Actions → 'Generate Return Label'
               ⚠️ NOT 'Create return label' — that is Shopify-native""")

    if "parcel post" in s or "t28" in s:
        return dedent("""\
            PRE-REQUIREMENTS (AU Post — Parcel Post / T28):
            1. order_action: create_new  (fresh Shopify order)
            FLOW during Manual Label:
            - Generate Packages → Get Shipping Rates
            - Select 'Parcel Post' service radio button
            - Click 'Generate Label'
            VERIFY via Download Documents ZIP (Strategy 2):
            - JSON must contain: items[0].product_id = 'T28'""")

    if "express post" in s or "e86j" in s:
        return dedent("""\
            PRE-REQUIREMENTS (AU Post — Express Post / E86J):
            1. order_action: create_new  (fresh Shopify order)
            FLOW during Manual Label:
            - Generate Packages → Get Shipping Rates
            - Select 'Express Post' service radio button
            - Click 'Generate Label'
            VERIFY via Download Documents ZIP (Strategy 2):
            - JSON must contain: items[0].product_id = 'E86J'""")

    return ""  # Unknown scenario — RAG + domain expert will handle it


def _plan_scenario(
    scenario: str, app_url: str, ctx: str, expert_insight: str, claude: ChatAnthropic
) -> dict:
    preconditions = _get_preconditions(scenario)
    prompt = _PLAN_PROMPT.format(
        scenario=scenario, app_url=app_url,
        app_workflow_guide=_trim_workflow_guide(scenario),
        expert_insight=expert_insight or "(not available)",
        code_context=ctx[:5000],
    )
    if preconditions:
        prompt = prompt.replace(
            "Respond ONLY in JSON:",
            f"KNOWN PRE-REQUIREMENTS FOR THIS SCENARIO (from automation spec files):\n{preconditions}\n\n"
            "Respond ONLY in JSON:",
        )
    resp = claude.invoke([HumanMessage(content=prompt)])
    return _parse_json(resp.content) or {}


def _decide_next(
    claude: ChatAnthropic,
    scenario: str,
    url: str,
    ax: str,
    net: list[str],
    steps: list[VerificationStep],
    ctx: str,
    step_num: int,
    scr: str = "",
    expert_insight: str = "",
) -> dict:
    steps_text = "\n".join(
        f"  {i+1}. [{s.action}] {s.description} ({'✓' if s.success else '✗'})"
        for i, s in enumerate(steps)
    )
    prompt_text = _STEP_PROMPT.format(
        scenario=scenario,
        expert_insight=expert_insight or "(not available)",
        app_workflow_guide=_trim_workflow_guide(scenario),
        url=url,
        ax_tree=ax[:3000],
        network_calls="\n".join(net[-10:]) if net else "(none)",
        steps_taken=steps_text or "(just starting)",
        code_context=ctx[:3000],
        step_num=step_num,
        max_steps=MAX_STEPS,
    )
    if scr:
        msg = HumanMessage(content=[
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": scr,
                },
            },
            {"type": "text", "text": prompt_text},
        ])
    else:
        msg = HumanMessage(content=prompt_text)

    content = claude.invoke([msg]).content
    raw = content if isinstance(content, str) else \
        " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    parsed = _parse_json(raw)
    if parsed:
        logger.debug("[decide] action=%s target=%s", parsed.get("action"), parsed.get("target", ""))
        return parsed
    logger.warning("[decide] Could not parse JSON from Claude response — falling back to observe.\nRaw: %s", raw[:400])
    return {"action": "observe", "description": "JSON parse failed — re-observing page"}


# ── Core: verify one scenario ─────────────────────────────────────────────────

def _verify_scenario(
    page,
    scenario: str,
    card_name: str,
    app_base: str,
    plan_data: dict,
    ctx: str,
    claude: ChatAnthropic,
    progress_cb: Callable | None = None,
    qa_answer: str = "",
    first_scenario: bool = False,
    expert_insight: str = "",
) -> ScenarioResult:
    result       = ScenarioResult(scenario=scenario)
    net_seen: list[str] = []
    api_endpoints = plan_data.get("api_to_watch", [])

    if qa_answer:
        ctx = f"QA GUIDANCE: {qa_answer}\n\n{ctx}"

    # ── Order setup ───────────────────────────────────────────────────────────
    try:
        from pipeline.order_creator import infer_order_decision
        _claude_order = plan_data.get("order_action") or infer_order_decision(scenario)
        order_action  = _validate_order_action(scenario, _claude_order)
        logger.info("[order] scenario='%s…' → claude=%s validated=%s",
                    scenario[:60], _claude_order, order_action)
        ctx = _setup_order_ctx(order_action, scenario, ctx)
    except Exception as oe:
        logger.debug("[order] Order setup skipped (non-fatal): %s", oe)

    if first_scenario or not page.url.startswith(app_base.split("/apps/")[0]):
        try:
            page.goto(app_base, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(600)
        except Exception as e:
            result.status  = "fail"
            result.verdict = f"Could not navigate to app: {e}"
            return result
    else:
        try:
            page.goto(app_base, wait_until="domcontentloaded", timeout=20_000)
            page.wait_for_timeout(600)
        except Exception:
            pass

    nav_clicks = plan_data.get("nav_clicks", [])
    _store = app_base.split("/store/")[1].split("/")[0] if "/store/" in app_base else ""
    _APP_URL_MAP = {
        "shipping":        f"{app_base}/shopify",
        "appproducts":     f"{app_base}/products",
        "products":        f"{app_base}/products",
        "settings":        f"{app_base}/settings",
        "pickup":          f"{app_base}/pickup",
        "faq":             f"{app_base}/faq",
        "rates log":       f"{app_base}/rateslog",
        "orders":          f"https://admin.shopify.com/store/{_store}/orders",
        "shopifyproducts": f"https://admin.shopify.com/store/{_store}/products",
    }
    nav_failed: list[str] = []

    for nav_label in nav_clicks:
        clicked   = False
        label_low = nav_label.lower().strip()
        nav_url   = _APP_URL_MAP.get(label_low)

        if nav_url:
            try:
                page.goto(nav_url, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(600)
                clicked = True
                logger.info("Nav [%s] → %s", nav_label, nav_url)
            except Exception as e:
                logger.warning("Direct nav failed for '%s' (%s): %s", nav_label, nav_url, e)

        if not clicked:
            try:
                for fn in [
                    lambda l=nav_label: page.get_by_role("link", name=l, exact=True),
                    lambda l=nav_label: page.get_by_role("link", name=l, exact=False),
                    lambda l=nav_label: page.get_by_text(l, exact=False),
                ]:
                    loc = fn()
                    if loc.count() > 0:
                        loc.first.click(timeout=5_000)
                        page.wait_for_timeout(500)
                        clicked = True
                        break
            except Exception:
                pass

        if not clicked:
            nav_failed.append(nav_label)
            logger.warning("Nav '%s' not found — agentic loop will handle navigation", nav_label)
            result.steps.append(VerificationStep(
                action="observe",
                description=f"Nav '{nav_label}' not found — will navigate from current page state",
                success=False,
            ))

    # Detect bot-challenge page
    try:
        body = page.inner_text("body").lower()
        if any(p in body for p in _CHALLENGE_PHRASES):
            result.status  = "skipped"
            result.verdict = "⚠️ Shopify bot-detection challenge. Refresh auth.json and retry."
            return result
    except Exception:
        pass

    # Agentic loop
    active_page = page
    zip_ctx = ""

    for step_num in range(1, MAX_STEPS + 1):
        ax  = _ax_tree(active_page)
        scr = _screenshot(active_page)
        net = _network(active_page, api_endpoints)
        net_seen.extend(n for n in net if n not in net_seen)

        if progress_cb:
            progress_cb(step_num, f"Step {step_num}/{MAX_STEPS}")

        effective_ctx = f"{zip_ctx}{ctx}" if zip_ctx else ctx

        action = _decide_next(claude, scenario, active_page.url, ax, net_seen,
                              result.steps, effective_ctx, step_num, scr=scr,
                              expert_insight=expert_insight)

        atype = action.get("action", "observe")
        _desc = action.get("description", atype)
        _tgt  = action.get("target", "")

        logger.info("[step %d/%d] action=%-12s target=%-30s | %s",
                    step_num, MAX_STEPS, atype, _tgt[:30], _desc[:80])
        if progress_cb:
            progress_cb(step_num, f"[{atype}] {_desc[:60]}")

        step = VerificationStep(
            action=atype,
            description=_desc,
            target=_tgt,
            screenshot_b64=scr,
            network_calls=list(net),
        )
        result.steps.append(step)

        if atype == "verify":
            result.status  = action.get("verdict", "partial")
            result.verdict = action.get("finding", "")
            step.screenshot_b64 = _screenshot(active_page)
            break

        if atype == "qa_needed":
            result.status      = "qa_needed"
            result.qa_question = action.get("question", "I need more guidance to find this feature.")
            break

        if atype == "reset_order":
            new_order_action = action.get("order_action", "existing_fulfilled")
            logger.info("[reset_order] Agent requested order reset → %s", new_order_action)
            try:
                ctx = _setup_order_ctx(new_order_action, scenario, ctx)
                step.success = True
                step.description = f"Order reset → {new_order_action}: {action.get('description', '')}"
            except Exception as reset_err:
                logger.warning("[reset_order] failed: %s", reset_err)
                step.success = False
            continue

        step.success = _do_action(active_page, action, app_base)

        if "_zip_content" in action:
            zip_data = action["_zip_content"]
            zip_summary = json.dumps(zip_data, indent=2)[:4000]
            zip_ctx = (
                f"=== DOWNLOADED ZIP CONTENTS (from '{action.get('target','?')}') ===\n"
                f"{zip_summary}\n"
                f"========================================\n\n"
            )

        if "_file_content" in action:
            file_data = action["_file_content"]
            file_summary = json.dumps(file_data, indent=2)[:4000]
            zip_ctx = (
                f"=== DOWNLOADED FILE CONTENTS ('{file_data.get('filename','?')}') ===\n"
                f"{file_summary}\n"
                f"========================================\n\n"
            )
            logger.info("File content accumulated for next step (%d chars)", len(file_summary))

        if "_new_page" in action:
            active_page = action["_new_page"]

    else:
        result.status      = "qa_needed"
        _last_step_desc = result.steps[-1].description if result.steps else "nothing yet"
        result.qa_question = (
            f"I reached the step limit ({MAX_STEPS} steps) without being able to "
            f"conclusively verify this scenario. I last saw: {_last_step_desc}. "
            f"Please check the app manually and advise whether this AC passes."
        )
        result.verdict = f"Exhausted {MAX_STEPS} steps — QA review needed"

    return result


# ── Shopify auto-login helper ─────────────────────────────────────────────────

def _shopify_login(page, email: str, password: str, app_url: str) -> bool:
    """
    Log into Shopify admin using email + password, save the session to auth.json,
    and navigate to app_url.  Returns True on success, False on failure.
    """
    try:
        logger.info("SmartVerifier: auth.json missing — attempting Shopify login with %s", email)
        page.goto("https://accounts.shopify.com/login", wait_until="domcontentloaded", timeout=20_000)
        page.wait_for_timeout(1500)

        # Fill email
        email_sel = "input[type='email'], input[name='email'], input[id*='email']"
        page.wait_for_selector(email_sel, timeout=10_000)
        page.fill(email_sel, email)

        # Click Continue / Next
        for btn in ["button[type='submit']", "button:has-text('Continue')", "button:has-text('Next')"]:
            try:
                page.click(btn, timeout=3_000)
                break
            except Exception:
                pass
        page.wait_for_timeout(2000)

        # Fill password (may appear on next screen)
        pass_sel = "input[type='password'], input[name='password'], input[id*='password']"
        try:
            page.wait_for_selector(pass_sel, timeout=8_000)
            page.fill(pass_sel, password)
            for btn in ["button[type='submit']", "button:has-text('Log in')", "button:has-text('Sign in')"]:
                try:
                    page.click(btn, timeout=3_000)
                    break
                except Exception:
                    pass
        except Exception:
            pass  # password field not shown (e.g. SSO redirect)

        page.wait_for_timeout(4000)

        # Save session state to auth.json so subsequent runs skip login
        current_url = page.url
        if "login" not in current_url and "accounts.shopify" not in current_url:
            page.context.storage_state(path=str(_AUTH_JSON))
            logger.info("SmartVerifier: login successful — auth.json saved")
            return True

        # Navigate to the app URL and check again
        page.goto(app_url, wait_until="domcontentloaded", timeout=20_000)
        page.wait_for_timeout(3000)
        if "login" not in page.url:
            page.context.storage_state(path=str(_AUTH_JSON))
            logger.info("SmartVerifier: login successful (via app_url) — auth.json saved")
            return True

        logger.warning("SmartVerifier: login may have failed — still on %s", page.url)
        return False

    except Exception as exc:
        logger.warning("SmartVerifier: auto-login failed: %s", exc)
        return False


# ── Public entry point ────────────────────────────────────────────────────────

def verify_ac(
    app_url: str,
    ac_text: str,
    card_name: str,
    card_id: str = "",
    card_url: str = "",
    qa_name: str = "QA Team",
    progress_cb: "Callable[[int, str, int, str], None] | None" = None,
    qa_answers: "dict[str, str] | None" = None,
    auto_report_bugs: bool = True,
    stop_flag: "Callable[[], bool] | None" = None,
    max_scenarios: int | None = None,
    shopify_email: str = "",
    shopify_password: str = "",
) -> VerificationReport:
    """
    Verify AC scenarios for a card against the live AU Post Shopify app.

    Args:
        app_url:           Full AU Post app URL in Shopify admin
        ac_text:           Full AC markdown from the Trello card
        card_name:         Card title
        card_id:           Trello card ID — used to get dev members for bug DMs
        card_url:          Trello card URL — included in bug DM
        qa_name:           Name of QA running the verification
        progress_cb:       callback(scenario_idx, scenario_title, step_num, step_desc)
        qa_answers:        {scenario_text: qa_answer} for stuck scenarios
        auto_report_bugs:  If True, automatically DM developers when a bug is found
        max_scenarios:     Cap number of scenarios tested (None = test all).
        shopify_email:     Shopify admin email — used to auto-login if auth.json is missing.
        shopify_password:  Shopify admin password — used to auto-login if auth.json is missing.

    Returns:
        VerificationReport with per-scenario results + bug_report on failures
    """
    from playwright.sync_api import sync_playwright

    # Fall back to env vars for credentials if not explicitly passed
    if not shopify_email:
        shopify_email = os.getenv("USER_EMAIL", "")
    if not shopify_password:
        shopify_password = os.getenv("USER_PASSWORD", "")

    if not app_url:
        app_url = get_auto_app_url()
    if not app_url:
        raise ValueError(
            "App URL required. Set STORE in the automation repo .env, "
            "or enter the URL manually."
        )
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")

    claude = ChatAnthropic(
        model=config.CLAUDE_SONNET_MODEL,
        api_key=config.ANTHROPIC_API_KEY,
        temperature=0.1,
        max_tokens=4096,
        timeout=90,
    )

    report    = VerificationReport(card_name=card_name, app_url=app_url)
    scenarios = _extract_scenarios(ac_text, claude)
    total_extracted = len(scenarios)
    if max_scenarios and max_scenarios < len(scenarios):
        scenarios = scenarios[:max_scenarios]
        logger.info("SmartVerifier: capped to %d/%d scenarios for '%s' (max_scenarios=%d)",
                    len(scenarios), total_extracted, card_name, max_scenarios)
    else:
        logger.info("SmartVerifier: %d scenarios for '%s'", len(scenarios), card_name)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=False, args=_ANTI_BOT_ARGS)
            logger.debug("SmartVerifier: launched real Chrome")
        except Exception as e:
            logger.warning("Chrome not found (%s) — falling back to headless Chromium", e)
            browser = p.chromium.launch(headless=True, args=_ANTI_BOT_ARGS)

        # ── Auth: prefer saved session; fall back to credential-based login ──
        ctx = browser.new_context(**_auth_ctx_kwargs())
        if not _AUTH_JSON.exists() and shopify_email and shopify_password:
            _login_page = ctx.new_page()
            _shopify_login(_login_page, shopify_email, shopify_password, app_url)
            _login_page.close()
            # Reload context with the newly saved auth.json
            ctx.close()
            ctx = browser.new_context(**_auth_ctx_kwargs())
        page = ctx.new_page()

        for idx, scenario in enumerate(scenarios):
            if stop_flag and stop_flag():
                logger.info("SmartVerifier: stopped by user after %d scenarios", idx)
                break

            logger.info("[%d/%d] Verifying: %s", idx + 1, len(scenarios), scenario[:70])

            if progress_cb:
                progress_cb(idx + 1, scenario, 0, "🧠 Asking domain expert…")
            expert_insight = _ask_domain_expert(scenario, card_name, claude)
            logger.debug("Expert insight for '%s': %s", scenario[:50], expert_insight[:120])

            code_ctx  = _code_context(scenario, card_name)
            plan_data = _plan_scenario(scenario, app_url, code_ctx, expert_insight, claude)

            def _cb(step_num: int, desc: str, _i: int = idx, _sc: str = scenario) -> None:
                if progress_cb:
                    progress_cb(_i + 1, _sc, step_num, desc)

            qa_ans = (qa_answers or {}).get(scenario, "")

            sv = _verify_scenario(
                page=page,
                scenario=scenario,
                card_name=card_name,
                app_base=app_url,
                plan_data=plan_data,
                ctx=code_ctx,
                claude=claude,
                progress_cb=_cb,
                qa_answer=qa_ans,
                first_scenario=(idx == 0),
                expert_insight=expert_insight,
            )

            if auto_report_bugs and sv.status in ("fail", "partial") and card_id:
                if progress_cb:
                    progress_cb(idx + 1, scenario, MAX_STEPS, "🐛 Bug detected — notifying developer…")
                try:
                    from pipeline.bug_reporter import notify_devs_of_bug
                    steps_taken = [
                        f"{s.action}: {s.description}" for s in sv.steps
                        if s.action in ("click", "fill", "navigate", "observe")
                    ]
                    bug_result = notify_devs_of_bug(
                        card_id=card_id,
                        card_name=card_name,
                        card_url=card_url,
                        bug_description=sv.verdict,
                        scenario=scenario,
                        qa_name=qa_name,
                        verification_steps=steps_taken,
                    )
                    sv.bug_report = bug_result
                    logger.info(
                        "Bug report for '%s': sent=%s failed=%s",
                        scenario[:50], bug_result.get("sent_to"), bug_result.get("failed"),
                    )
                except Exception as e:
                    logger.warning("Bug auto-report failed: %s", e)
                    sv.bug_report = {"ok": False, "error": str(e)}

            report.scenarios.append(sv)

        ctx.close()
        browser.close()

    results_txt = "\n".join(
        f"- [{sv.status.upper()}] {sv.scenario}: {sv.verdict}"
        for sv in report.scenarios
    )
    resp = claude.invoke([HumanMessage(content=_SUMMARY_PROMPT.format(
        card_name=card_name, results=results_txt,
    ))])
    report.summary = resp.content.strip()

    return report


def reverify_failed(
    report: VerificationReport,
    app_url: str = "",
    card_id: str = "",
    card_url: str = "",
    qa_name: str = "QA Team",
    progress_cb: "Callable | None" = None,
    qa_answers: "dict[str, str] | None" = None,
    auto_report_bugs: bool = True,
    stop_flag: "Callable[[], bool] | None" = None,
) -> VerificationReport:
    """
    Re-run only the failed/partial/qa_needed scenarios from an existing report.

    Returns:
        Updated VerificationReport — previously-passing scenarios kept as-is,
        re-run results merged in, and summary regenerated.
    """
    from playwright.sync_api import sync_playwright

    failed_scenarios = [
        sv for sv in report.scenarios
        if sv.status in ("fail", "partial", "qa_needed")
    ]

    if not failed_scenarios:
        return report

    _app_url = (app_url or report.app_url or "").strip()
    if not _app_url:
        _app_url = get_auto_app_url()
    if not _app_url:
        raise ValueError(
            "App URL required. Set STORE in the automation repo .env, "
            "or enter the URL manually."
        )
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")

    claude = ChatAnthropic(
        model=config.CLAUDE_SONNET_MODEL,
        api_key=config.ANTHROPIC_API_KEY,
        temperature=0.1,
        max_tokens=4096,
        timeout=90,
    )

    card_name    = report.card_name
    failed_count = len(failed_scenarios)
    logger.info("reverify_failed: re-running %d scenario(s) for '%s'", failed_count, card_name)

    scenario_index: dict[str, int] = {
        sv.scenario: i for i, sv in enumerate(report.scenarios)
    }

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=False, args=_ANTI_BOT_ARGS)
        except Exception as e:
            logger.warning("Chrome not found (%s) — falling back to headless Chromium", e)
            browser = p.chromium.launch(headless=True, args=_ANTI_BOT_ARGS)

        ctx  = browser.new_context(**_auth_ctx_kwargs())
        page = ctx.new_page()

        for idx, old_sv in enumerate(failed_scenarios):
            if stop_flag and stop_flag():
                logger.info("reverify_failed: stop requested after %d/%d scenarios", idx, failed_count)
                break

            scenario = old_sv.scenario
            logger.info("[%d/%d] Re-verifying: %s", idx + 1, failed_count, scenario[:70])

            if progress_cb:
                progress_cb(idx + 1, scenario, 0, "🧠 Asking domain expert…")
            expert_insight = _ask_domain_expert(scenario, card_name, claude)

            code_ctx  = _code_context(scenario, card_name)
            plan_data = _plan_scenario(scenario, _app_url, code_ctx, expert_insight, claude)

            def _cb(step_num: int, desc: str, _i: int = idx, _sc: str = scenario) -> None:
                if progress_cb:
                    progress_cb(_i + 1, _sc, step_num, desc)

            qa_ans = (qa_answers or {}).get(scenario, "")

            new_sv = _verify_scenario(
                page=page,
                scenario=scenario,
                card_name=card_name,
                app_base=_app_url,
                plan_data=plan_data,
                ctx=code_ctx,
                claude=claude,
                progress_cb=_cb,
                qa_answer=qa_ans,
                expert_insight=expert_insight,
                first_scenario=(idx == 0),
            )

            if auto_report_bugs and new_sv.status in ("fail", "partial") and card_id:
                if progress_cb:
                    progress_cb(idx + 1, scenario, MAX_STEPS, "🐛 Bug detected — notifying developer…")
                try:
                    from pipeline.bug_reporter import notify_devs_of_bug
                    steps_taken = [
                        f"{s.action}: {s.description}" for s in new_sv.steps
                        if s.action in ("click", "fill", "navigate", "observe")
                    ]
                    bug_result = notify_devs_of_bug(
                        card_id=card_id,
                        card_name=card_name,
                        card_url=card_url,
                        bug_description=new_sv.verdict,
                        scenario=scenario,
                        qa_name=qa_name,
                        verification_steps=steps_taken,
                    )
                    new_sv.bug_report = bug_result
                    logger.info(
                        "Bug report for '%s': sent=%s failed=%s",
                        scenario[:50], bug_result.get("sent_to"), bug_result.get("failed"),
                    )
                except Exception as e:
                    logger.warning("Bug auto-report failed: %s", e)
                    new_sv.bug_report = {"ok": False, "error": str(e)}

            orig_idx = scenario_index.get(scenario)
            if orig_idx is not None:
                report.scenarios[orig_idx] = new_sv
            else:
                report.scenarios.append(new_sv)

        ctx.close()
        browser.close()

    results_txt = "\n".join(
        f"- [{sv.status.upper()}] {sv.scenario}: {sv.verdict}"
        for sv in report.scenarios
    )
    resp = claude.invoke([HumanMessage(content=_SUMMARY_PROMPT.format(
        card_name=card_name, results=results_txt,
    ))])
    report.summary = resp.content.strip()

    return report
