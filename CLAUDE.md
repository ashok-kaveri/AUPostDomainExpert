# AUPostDomainExpert — Claude Session Context

> **Read this first in every session.** It captures all design decisions, bugs fixed,
> and current state of every major component.

---

## Project Overview

**AUPostDomainExpert** is an AI-powered QA assistant for the PluginHive Australia Post Shopify App.
It has three main capabilities:

1. **Domain Expert Chat** — RAG-backed chatbot answering questions about the AU Post Shopify app
2. **Smart AC Verifier** — Agentic browser-based acceptance criteria verifier (most complex component)
3. **Pipeline Dashboard** — Streamlit UI that orchestrates Trello cards → AC generation → verification

---

## Key File Map

| File | Purpose |
|------|---------|
| `pipeline/smart_ac_verifier.py` | Core agentic AC verifier (most worked-on file) |
| `ui/pipeline_dashboard.py` | Streamlit dashboard — threading for non-blocking runs |
| `pipeline/trello_client.py` | Trello REST API wrapper |
| `rag/code_indexer.py` | Indexes automation POM + backend code into ChromaDB |
| `rag/vectorstore.py` | PluginHive docs RAG search |
| `config.py` | All env-driven config: models, paths, ChromaDB, seed URLs |
| `ingest/web_scraper.py` | Web scraping for PluginHive AU Post docs |
| `ingest/run_ingest.py` | Ingestion pipeline entry point |
| `ingest/sheets_loader.py` | Loads eParcel + MyPost Business test cases from Google Sheets |

---

## Australia Post App — Two Account Types

### eParcel
- Australia Post's business parcel service for higher-volume merchants
- Supports: domestic + international shipping
- Extra Cover up to **$5,000 AUD**
- Dangerous goods support (domestic only)
- Services: Parcel Post, Express Post (+ Signature variants)

### MyPost Business
- Suitable for smaller-volume businesses
- Domestic shipping only
- Extra Cover up to **$1,000 AUD**
- No dangerous goods support
- Services: Standard, Express

---

## Smart AC Verifier — Full Architecture

### Flow
```
AC Text
  ↓
1. Claude extracts testable scenarios (JSON array)
  ↓ (per scenario)
2. Domain Expert consultation — Claude queries domain RAG + code RAG,
   synthesises ≤200 words about: expected behaviour, API signals, key checks
  ↓
3. Code RAG — automation POM + backend API context fetched
  ↓
4. Claude plans: nav_clicks[], look_for[], api_to_watch[], plan sentence
  ↓ (agentic loop — up to 10 steps)
5. Browser action: navigate / click / fill / scroll / observe / download_zip
6. Capture: AX tree (depth 6, 150 lines) + screenshot (base64) + network calls
7. Claude decides next action OR gives verdict OR asks QA
  ↓
✅ pass / ❌ fail / ⚠️ partial / 🔶 qa_needed  per scenario
```

### Actions Available to Claude
- `observe` — take stock of current page state (always first step)
- `click` — click button/link/checkbox (tries iframe first, then full page)
- `fill` — type into input field
- `scroll` — scroll page down 400px
- `navigate` — go to a URL path
- `switch_tab` — switch to most recently opened browser tab
- `close_tab` — close current tab, return to first tab
- `download_zip` — click element, intercept ZIP download, unzip, parse JSON files,
                    store content in `action["_zip_content"]` → injected into next step's context
- `verify` — final verdict (pass/fail/partial) with finding
- `qa_needed` — Claude is genuinely stuck, asks QA a question

### ZIP Download Feature (document verification)
The "More Actions" → "Download Documents" button on the Order Summary page downloads a ZIP
containing the label PDF + createShipment request/response JSON files.

Flow Claude should follow for field-level verification:
1. `click` "More Actions"
2. `download_zip` target="Download Documents"
   → ZIP extracted automatically, JSON content prepended to context for step 3
3. `observe` (sees JSON in context)
4. `verify` based on JSON field values

---

## AU Post App UI Architecture (Critical)

### Iframe Structure
- The AU Post app is embedded inside Shopify admin as an iframe: `iframe[name="app-iframe"]`
- App sidebar items (Shipping, Settings, PickUp, Products, FAQ, Rates Log) are **INSIDE** the iframe
- Shopify admin items (Orders, Products in admin sidebar) are **OUTSIDE** the iframe
- Navigation strategy: app nav items → search iframe first; Shopify nav → search full page first

### App Sidebar Navigation (inside iframe)
- **Shipping** → "All Orders" grid (All / Pending / Label Generated tabs)
- **PickUp** → Schedule Australia Post pickup
- **Products** → Map products to dimensions, signature, extra cover
- **Settings** → AU Post account, services, packages, additional services
- **FAQ** → Help articles
- **Rates Log** → Historical rate request log

### Shopify Admin Navigation (outside iframe, left sidebar)
- **Orders** — Shopify orders list (where you click More Actions → Generate Label)
- **Products** — Shopify product catalog (create/edit products)

### All Orders Grid (app Shipping page)
Columns: Order#, Label created date, Customer, Label status, Shipping Service,
         Subtotal, Shipping Cost, Packages, Products, Weight, Messages
Tab filters: All | Pending | Label Generated
Status values: "label generated" (green), "inprogress" (yellow), "failed" (red),
               "auto cancelled" (grey), "label cancelled"
**Click an order ROW → opens Order Summary page for that order**
Top-right buttons: "Generate New Labels", "How to", "Help", "Generate Report"

### Order Summary Page (after clicking an order or after label generation)
Buttons:
- "Print Documents" — opens **PluginHive document viewer** in a NEW TAB
- "Upload Documents" — upload custom docs
- "More Actions" dropdown:
  - "Download Documents" → downloads ZIP (label PDF + request/response JSON)
  - "Cancel Label"
  - "Return Label"
  - "How To" → modal with "Click Here" button (downloads RequestResponse ZIP)
- TWO TABS: "Packages" | "Return packages"
- "← #XXXX" back arrow → back to Shipping grid

### Label Generation Flows

**Manual Label** (user picks service):
Shopify Orders → order row → More Actions → "Generate Label"
→ App opens (iframe) with TWO areas:
  LEFT: a. "Generate Packages" → b. "Get Shipping Rates" → c. Select radio → d. "Generate Label"
  RIGHT: **The SideDock** (ALWAYS VISIBLE — configure BEFORE generating label)
→ Redirects to Order Summary

### The SideDock — Always Visible Right Panel in Manual Label Page
Contains (top to bottom):
1. **Signature on Delivery**: checkbox — recipient must sign; cannot combine with ATL
2. **Authority to Leave (ATL)**: checkbox — parcel left without signature; cannot combine with Signature
3. **Extra Cover**: checkbox → input declared value AUD
   - Max: $5,000 AUD (eParcel) / $1,000 AUD (MyPost Business)
4. **Safe Drop**: checkbox — leave in safe location
5. **Dangerous Goods**: checkbox (eParcel domestic only)

### Return Label Flows (two entry points)
**WAY A — From app Order Summary**:
Order Summary → "Return packages" tab → "Return Packages" button
→ Enter return quantity → "Refresh Rates" → select service → "Generate Return Label"
→ Verify: "SUCCESS" badge + "Download Label" link visible

**WAY B — From Shopify admin order page**:
Shopify Orders → click order → More Actions → **"Generate Return Label"**
(NOT "Create return label" — that is a Shopify-native feature)

### Rate Logs (ALL JSON — REST API only)
**Rate log (in-page, during manual label)**:
After "Get Shipping Rates" → click ⋯ → "View Logs"
→ Dialog shows JSON Request (left) + Response (right) IN THE PAGE (no download)

**Label log (ZIP, after label generated)**:
Strategy 2: More Actions → Download Documents → ZIP with label PDF + JSON

---

## Product Workflows

### When to Create vs Use Existing Products
- **DEFAULT**: Use existing products in Shopify admin. Do NOT create new ones unless explicitly needed.
- **AU Post App Products**: Search existing in app Products page (use "Test Product A" or "Test Product B")

### AU Post App Product Config (inside iframe)
1. Click "Products" in app sidebar
2. Click search/filter → type product name → press Enter
3. Click product row
4. NORMAL product: set Dimensions (L/W/H in cm + weight in kg) + options
   Do NOT touch Dangerous Goods unless scenario tests it
5. SPECIAL services: enable ONLY if scenario explicitly tests them
   - Signature on Delivery (cannot combine with ATL)
   - Authority to Leave (cannot combine with Signature)
   - Extra Cover + declared value
   - Dangerous Goods (eParcel only)
6. Click "Save" → toast: "Products Successfully Saved"

---

## Request JSON Field Paths (for verification)
All logs are **JSON** (REST API only).
```
# Package-level
items[0].length                              → package length (cm)
items[0].width                               → package width (cm)
items[0].height                              → package height (cm)
items[0].weight                              → package weight (kg)
items[0].product_id                          → service code
  "T28"  → Parcel Post
  "E86J" → Express Post
  "PLT"  → International Economy

# Shipment options
options.signature_on_delivery                → true / false
options.authority_to_leave                   → true / false
options.extra_cover.amount                   → declared value AUD
from.postcode                                → sender postcode (4 digits, Australian)
to.postcode                                  → receiver postcode

# Response fields
trackingNumbers[0]                           → Article ID (tracking number)
items[0].article_id                          → Article ID on item level

# Cubic weight formula (AU Post charges higher of actual vs cubic):
cubic_weight = L(cm) × W(cm) × H(cm) ÷ 4000
```

---

## Google Sheets — Test Cases

| Sheet | Sheet ID | Coverage |
|-------|----------|----------|
| eParcel | `1Uf9NyCCwaKpHGlLVvI7S9xOVEGDekJNIHJFFlUsOcoA` | eParcel label, tracking, returns, special services |
| MyPost Business | `1zLRpb2HSeb7XM4bJMb0ZCNWSDHr3zbFzN2meyhDnvEE` | MyPost label, tracking, returns |

Both sheets are ingested via `ingest/sheets_loader.py` using the `sheets` source.
Run: `python -m ingest.run_ingest --sources sheets`

---

## Streamlit Threading (Critical — Stop Button Fix)

Same threading pattern as the reference project:
The dashboard runs `verify_ac()` in a background `threading.Thread` so Streamlit's
UI stays responsive and the Stop button appears immediately.

---

## ChromaDB Collections

- `aupost_knowledge` — domain docs (PluginHive, AU Post API docs, test cases)
- `aupost_code_knowledge` — source code (automation POM + backend)

---

## Claude Models Used

| Purpose | Model | Config Key |
|---------|-------|-----------|
| Deep reasoning, AC verifier | claude-sonnet-4-6 | `CLAUDE_SONNET_MODEL` |
| Fast/lightweight tasks | claude-haiku-4-5-20251001 | `CLAUDE_HAIKU_MODEL` |
| Domain expert chat | same as Sonnet (default) | `DOMAIN_EXPERT_MODEL` |

---

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=...
TRELLO_API_KEY=...
TRELLO_TOKEN=...
TRELLO_BOARD_ID=...
BACKEND_CODE_PATH=~/Documents/aupost-Backend-Code/shopifyaupostapp
FRONTEND_CODE_PATH=~/Documents/aupost-Frontend-Code/shopify-aupost-web-client
AUTOMATION_CODEBASE_PATH=../aupost-test-automation
CLAUDE_SONNET_MODEL=claude-sonnet-4-6
CLAUDE_HAIKU_MODEL=claude-haiku-4-5-20251001
EPARCEL_SHEETS_ID=1Uf9NyCCwaKpHGlLVvI7S9xOVEGDekJNIHJFFlUsOcoA
MYPOST_SHEETS_ID=1zLRpb2HSeb7XM4bJMb0ZCNWSDHr3zbFzN2meyhDnvEE
```

---

## Running the Dashboard

```bash
cd /Users/ashokkumarn/Documents/Pluginhive/AILearning/AUPostDomainExpert
streamlit run ui/pipeline_dashboard.py
```

## Running Ingestion

```bash
# Seed URLs only (fast, ~300 chunks)
python -m ingest.run_ingest --sources pluginhive_seeds

# Google Sheets only (eParcel + MyPost)
python -m ingest.run_ingest --sources sheets

# Full default pipeline
python -m ingest.run_ingest
```
