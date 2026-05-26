---
name: aupost-ai-qa-browser
description: Use when working inside the AUPostDomainExpert project to verify dashboard-generated AU Post Shopify app test cases in the real browser with Computer Use. Parse TC metadata, reuse automation/codebase/domain knowledge before navigation, safely drive Shopify/AU Post app flows for both eParcel and MyPost Business, ask QA only when blocked, and return pass/fail evidence without breaking current store/app state.
---

# AU Post AI QA Browser Skill

Use this skill to verify AU Post Shopify app test cases in a real live browser.

## First Reads

Before starting:
1. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/CLAUDE.md` — project architecture, account types, locators, flows
2. Read automation POM files from `/Users/madan/Documents/AU_Post/aupost-test-automation/auPost/support/pages/`:
   - `basePage.ts` — iframe selector, navigation helpers
   - `auPostAppPage.ts` — app sidebar navigation routes
   - `shippingPage.ts` — orders grid locators
   - `manualLabelPage.ts` — manual label generation locators (EXACT checkbox names)
   - `orderSummaryPage.ts` — order summary locators
   - `shopifyUI/shopify_OrderSummary.ts` — Shopify More Actions link names
   - `settingsPage.ts` — settings page locators
   - `productsPage.ts` + `productDetailsPage.ts` — products locators
   - `pickupPage.ts` — pickup locators
   - `ratesLogFaqPage.ts` — rates log locators

## TC Parsing

When given a test case, extract:
- TC ID and title
- Type: Positive / Negative / Edge
- Priority
- Execution Flow (see below)
- Account type: eParcel / MyPost Business
- Preconditions
- Steps (Given/When/And/Then)
- Expected Result
- Evidence type needed

## Execution Flows

| Flow | App Surface | Entry Point |
|---|---|---|
| `manual` | Shopify Orders → AU Post Generate Label → iframe | Shopify admin → Orders |
| `auto` | Shopify Orders → auto-generate → iframe | Shopify admin → Orders |
| `settings` | App iframe → /setting | Shopify admin → app → setting |
| `order-grid` | App iframe → /shopify | Shopify admin → app → shopify |
| `product-admin` | App iframe → /products | Shopify admin → app → products |
| `pickup` | App iframe → /pickup | Shopify admin → app → pickup |
| `return-label` | App iframe → Order Summary → Return packages tab | Order Summary |
| `rates-log` | App iframe → /rateslog | Shopify admin → app → rateslog |
| `none` | N/A — backend/API only | — |

## Critical Locators (from real automation POM)

### Iframe Selector
```
iframe[src*="qa-aupost.pluginhive.io"], iframe[src*="pluginhive.io"], iframe[src*="aupost"]
```

### Shopify More Actions (on page, NOT iframe)
- More Actions button: `role=button name="More actions"` (first match on page)
- Generate Label link: `role=link name=/AU\s*Post Generate Label/i` (on page)
- Return Label link: `role=link name="Au Post Return Label"` (on page)

### Manual Label Page (all in iframe)
- Generate Packages: `role=button name=/Generate Packages/i`
- Get Shipping Rates: `role=button name=/Get shipping rates|Fetch available shipping rates/i`
- Generate Label: `role=button name=/^Generate Label$/i`
- **Signature checkbox**: `role=checkbox name="Request Signature?"`
- **Insurance checkbox**: `role=checkbox name=/Insure package|Insurance/i`
- Insurance Declared Value: `role=spinbutton name="Declared Value"` (in "Insurance Details" dialog)
- Authority to Leave: `role=checkbox name="Authority to Leave"`
- More Actions: `role=button name=/More Actions/i`
- Return Packages: `role=button name=/Return Packages/i`

### Order Summary (in iframe)
- Packages tab: `role=tab name="Packages"`
- Return packages tab: `role=tab name="Return packages"`
- More Actions: `role=button name=/More Actions/i`
- Download Documents: `role=button name="Download Documents"` or menuitem
- Cancel Label: `role=button name="Cancel Label"` or menuitem
- Print Documents: opens popup to document-viewer.pluginhive.io

### Shipping Grid (in iframe)
- Tabs: All | Pending | Label Generated | Manifest Completed | Returns (5 tabs)
- Order row: `role=row` filtered by order number text → `role=link`
- Bulk More Actions: `role=button name="More actions"` (last)

### Settings Page (in iframe, route: /setting — SINGULAR)
- Heading: `h1` with text "Settings"
- Account Settings: `h2` with text "Account Settings"
- Rate Cost dropdown: `role=combobox name="Rate Cost"`
- Enable Rates Log: `role=checkbox name="Enable Rates Log"`
- Image Types: `role=combobox name="Image Types*"`
- Is Insurance Required: `role=checkbox name="Is Insurance Required For Forward Shipments?"`
- Delivery Signature: `role=combobox name="Is Delivery Signature Needed"`

### Products Page (in iframe, route: /products)
- Search: `role=button name="Search and filter results"`
- Product row button: `role=button name=<productName>`

### Product Details Page (in iframe)
- Length: `role=spinbutton name="Length"` + `role=combobox name="Length unit"`
- Width/Height/Weight: similar pattern
- Signature: `role=combobox name="Is Signature Needed"` ← DROPDOWN not checkbox
- Declared Value: `role=spinbutton name="Declared Value $"`
- Is Dangerous Goods: `role=checkbox name="Is Dangerous Goods"`
- Save: `role=button name="Save"`

### Pickup Page (in iframe, route: /pickup)
- Heading: `role=heading name="Pickup"`
- Table: `role=table`
- Toast: text "Pickup requested."

### Rates Log (in iframe, route: /rateslog)
- Heading: `role=heading name=/Rate Logs/i`
- View button per row: `role=button name=/^View$/i`
- Dialog: `role=dialog` with title "Rates Log"
- Request textarea: first `textarea` in dialog
- Response textarea: second `textarea` in dialog
- Close: `role=button name=/^Close$/i`

## Evidence Strategies

### Strategy 1 — Label Status Badge
For "label is generated" scenarios:
1. Navigate to app Shipping → click order with "label generated" status
2. Look for "label generated" status badge in Order Summary

### Strategy 2 — Download Documents ZIP (JSON field verification)
For signature, ATL, insurance, service code, dangerous goods scenarios:
1. Order Summary → More Actions → use `download_zip` action targeting "Download Documents"
   → The `download_zip` action clicks the element, intercepts the ZIP download, unzips it,
     parses JSON files, and stores content in `action["_zip_content"]` for the next step
2. ZIP extracted automatically — JSON content in context
3. Verify JSON fields:
   - `options.signature_on_delivery` = true
   - `options.authority_to_leave` = true
   - `options.extra_cover.amount` = declared value
   - `items[0].product_id` = 'T28' (Parcel Post) / 'E86J' (Express Post) / 'PLT' (Intl Economy)
   - `items[0].contains_dangerous_goods` = true
   - `trackingNumbers[0]` = tracking number
   - `items[0].length` / `width` / `height` / `weight` = dimensions

### Strategy 3 — Print Documents (visual PDF)
For label content / tracking number visible in PDF:
1. Order Summary → click Print Documents → new tab opens (document-viewer.pluginhive.io)
2. Switch to new tab → screenshot → verify visual content → close tab

## Safety Rules

- Do NOT change global Settings (rates, packaging, account) without first noting current state and restoring after
- Do NOT cancel labels unless explicitly testing cancellation
- Do NOT generate labels on orders that already have a label, unless testing regeneration
- For MyPost Business scenarios: do NOT attempt international shipping or Dangerous Goods
- Maximum **10 steps** per TC scenario. If still unresolved at step 10, return verdict=qa_needed with a specific question
- If blocked before step 10 and genuinely stuck, return qa_needed earlier — do not waste steps

## Locator Trace Handoff

After a successful (or partially successful) run involving new/discovered locators:
Save trace to `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/data/ai_qa_locator_traces/{card_id}.json`

The directory always exists. Write the JSON file directly using the Write tool.
If saving via Python: `PYTHONPATH=. .venv/bin/python -c "import json; ..."`

Trace shape:
```json
{
  "card_id": "...",
  "card_name": "...",
  "created_at": "...",
  "source": "aupost-ai-qa-browser",
  "tc_ids": ["TC-1"],
  "route": "/apps/aupost-qa/shopify",
  "page_context": "shippingPage | manualLabelPage | orderSummaryPage | settingsPage | ...",
  "steps": [{"action": "click", "target": "Request Signature?", "role": "checkbox", "surface": "iframe"}],
  "recommended_locators": [],
  "evidence": []
}
```

## Return Format

For each TC return:
```
TC-n: <title>
Verdict: ✅ Pass | ❌ Fail | ⚠️ Partial | 🔶 QA Needed
What was verified: ...
Evidence: Strategy used (1/2/3) + what was observed
Steps executed: N steps
Cleanup status: No changes made / restored to <state>
Learning: <new locator or flow discovered — if any>
```
