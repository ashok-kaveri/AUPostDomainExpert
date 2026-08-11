# AU Post Handoff Document Formats

This reference is based on `pipeline/handoff_docs.py` and AU Post release package conventions.

---

## HOW TO FIND NAVIGATION STEPS (priority order — follow this every time)

When writing "Where to Find" and "Step-by-Step Walkthrough" sections, use this order:

### 1. AI QA Evidence (BEST — use if available)
The AI QA verifier ran real `navigate` / `click` / `fill` actions in the live app.
The `ai_qa_evidence` field contains those exact steps — button names, URLs, element labels.
**Extract the walkthrough from the evidence steps directly.** This is ground truth for any feature, including brand-new ones.

### 2. Frontend Source Code (for NEW features without AI QA evidence)
The frontend codebase (path from the `FRONTEND_CODE_PATH` env var in this project's `.env`) has:
- Exact button text strings (e.g. `"Generate Label"`, `"Insure package"`)
- Route paths (e.g. `/apps/aupost-qa/setting`)
- React component structure showing which screen a feature lives in
- Screen folders: `src/screens/orders/`, `src/screens/settings/`, `src/screens/products/`, `src/screens/pickup/`, `src/screens/returnLabel/`, `src/screens/manifest/`

When using from Claude app: read the relevant screen file directly to extract button labels and flow.

### 3. Backend Source Code (for API / business logic)
The backend codebase (path from the `BACKEND_CODE_PATH` env var) has:
- API endpoint names and routes
- Feature flag / toggle names
- Service/option names (e.g. service codes T28, E86J)

### 4. Test Cases + AC Text (tertiary)
TCs describe expected steps. AC text describes intended behaviour.
Use only if source code is unavailable or incomplete.

### 5. Navigation Unknown — Check Index, Then Ask QA

If no source gives clear navigation steps, follow this exact sequence:

**Step A — Check if code is indexed:**
```python
from rag.code_indexer import get_index_stats
stats = get_index_stats()
# stats = {"frontend": N, "backend": M, "total": T, ...}
```
- If `frontend == 0` or `backend == 0` → code is NOT indexed or stale
- Tell the user: "The code index is empty/stale. Re-index first, then retry."
- Re-index command:
  ```bash
  .venv/bin/python -m ingest.run_ingest --sources codebase
  ```
  (run from this project's root)
- After re-indexing: retry `_fetch_code_context()` and search again.

**Step B — If still not found after indexing (or index is current but no results):**
Add a `⚠️ QA NOTE` block at the TOP of the support guide document:

```markdown
---
> ⚠️ **QA NOTE — Navigation Confirmation Needed**
> For card: **[Card Name]**
>
> The following navigation steps could not be determined from available sources
> (AI QA evidence, frontend/backend code, AC/TC text).
> Please confirm the exact steps before sharing this document with the support team:
>
> - [ ] **Where to find**: _e.g. "Which app sidebar section / Settings sub-page contains this feature?"_
> - [ ] **Step N**: _e.g. "What is the exact button/link label? Is it inside a dropdown or directly visible?"_
> - [ ] **Step N+1**: _e.g. "After clicking, what does the user see? Any dialog/modal/redirect?"_
>
> Once confirmed, update the Walkthrough section below with the actual steps.
> If re-indexing the codebase resolves this, regenerate the document.
---
```

**When using from the Claude app (no dashboard):**
Post the QA NOTE message to the QA team via Slack using `aupost-slack-operator`:
```
Hey team, I generated a support guide for [Card Name] but couldn't determine the exact navigation steps for [feature]. 
Could someone confirm: [specific question about the missing step]?
Once confirmed I'll update the doc. Thanks!
```
Channel: C09F65XF4ER (or DM the relevant QA person)

Do NOT invent paths. A wrong walkthrough is worse than an honest unknown with a clear question.

---

## APP NAVIGATION MAP (embed in every walkthrough — do not guess)

The Australia Post app is embedded inside Shopify admin as an **iframe** (src matches `qa-aupost.pluginhive.io`).

### App Sidebar (INSIDE iframe) — exact routes

| Sidebar label | Route | What's there |
|---|---|---|
| Shipping | `/apps/aupost-qa/shopify` | All Orders grid |
| Settings | `/apps/aupost-qa/setting` | Account, Packaging, Services, etc. (**SINGULAR** — NOT `/settings`) |
| Products | `/apps/aupost-qa/products` | Product dimension + service config |
| PickUp | `/apps/aupost-qa/pickup` | Schedule AU Post pickup |
| Rates Log | `/apps/aupost-qa/rateslog` | Rate request/response JSON logs |
| Manifest | `/apps/aupost-qa/manifest` | Manifest generation |
| FAQ | `/apps/aupost-qa/faq` | Help articles |

### Shopify Admin Sidebar (OUTSIDE iframe)

- **Orders** — Shopify orders list (click an order → More Actions to reach the AU Post app)
- **Products** — Shopify product catalog

### All Orders Grid (Shipping page)

Tabs: **All | Pending | Label Generated | Manifest Completed | Returns**
Columns: Order#, Label created date, Customer, Label status, Shipping Service, Subtotal, Shipping Cost, Packages, Products, Weight, Messages
Click any order row → opens Order Summary page for that order

### Settings Sections (at `/apps/aupost-qa/setting`)

1. Account Settings
2. Packaging
3. Product Settings
4. Rates Settings
5. Documents/Labels
6. Packing Slip
7. Additional Settings
8. International Shipping
9. Pickup Settings
10. Shop Contact Details

### Two Account Types — always state which applies

| Feature | eParcel | MyPost Business |
|---|---|---|
| Domestic shipping | ✅ | ✅ |
| International shipping | ✅ | ❌ |
| Extra Cover max | **$5,000 AUD** | **$1,000 AUD** |
| Dangerous Goods | ✅ (domestic only) | ❌ |
| Service codes | T28 (Parcel Post), E86J (Express Post) | Standard, Express |

---

## NAVIGATION STEP TEMPLATES (use exact button/link names below)

### Manual Label Generation

```
1. Shopify admin → Orders → click order row
2. Click More Actions button (on the Shopify order page, NOT inside iframe)
3. Click "AU Post Generate Label" link  ← EXACT name (role=link)
4. AU Post app opens in iframe — label generation page:
   LEFT PANEL:
     a. Click "Generate Packages" button
     b. Click "Get Shipping Rates" button
     c. Select a rate radio button (service options appear)
   RIGHT PANEL (SideDock — configure BEFORE generating label):
     - Signature:        check "Request Signature?" checkbox
     - ATL:              check "Authority to Leave" checkbox  (cannot combine with Signature)
     - Insurance:        check "Insure package" checkbox
                         → "Insurance Details" dialog opens
                         → Enter amount in "Declared Value" spinbutton
                         → Max: $5,000 AUD (eParcel) / $1,000 AUD (MyPost Business)
     - Safe Drop:        safe drop related checkbox
     - Dangerous Goods:  dangerous goods checkbox (eParcel domestic only)
5. Click "Generate Label" button
6. Redirects to Order Summary page
   → Confirm "label generated" status badge is visible
```

### Return Label — Way A (from Order Summary)

```
1. Open Order Summary page (click an order in Shipping grid, or after label generation)
2. Click "Return packages" tab  ← exact tab name
3. Click "Return Packages" button
4. Enter return quantity
5. Click "Refresh Rates"
6. Select return service radio button
7. Click "Generate Return Label"
8. Confirm "SUCCESS" badge and "Download Label" link visible
```

### Return Label — Way B (from Shopify admin)

```
1. Shopify admin → Orders → click order row
2. Click More Actions button
3. Click "Au Post Return Label" link  ← EXACT name (note lowercase "u")
   (NOT "Create return label" — that is Shopify-native)
   (NOT "Generate Return Label")
```

### Order Summary Page — Key Buttons

```
Print Documents       → opens PluginHive document viewer in a NEW TAB
More Actions ▾        → dropdown:
  - Download Documents  → downloads ZIP (label PDF + request/response JSON)
  - Cancel Label
  - Return Label
  - How To              → modal → "Click Here" button downloads RequestResponse ZIP
Tabs: Packages | Return packages
← #XXXX               → back to Shipping grid
```

### Checking Label/Shipment Request via Download Documents

```
1. Order Summary → click "More Actions" button
2. Click "Download Documents"
3. ZIP downloads: contains label PDF + createShipment request JSON + response JSON
4. Verify JSON fields:
   items[0].product_id          → service code ("T28"=Parcel Post, "E86J"=Express Post)
   items[0].length/width/height → package dimensions (cm)
   items[0].weight              → package weight (kg)
   options.signature_on_delivery → true/false
   options.authority_to_leave    → true/false
   options.extra_cover.amount    → declared value AUD
   trackingNumbers[0]            → Article ID (tracking number)
```

### Products Configuration (for Signature, ATL, Insurance, DG)

```
1. AU Post app sidebar → Products  (/apps/aupost-qa/products)
2. Click "Search and filter results" button → type product name → Enter
3. Click the product row
4. Configure:
   - "Is Signature Needed" dropdown  ← DROPDOWN not checkbox
   - "Authority to Leave" checkbox
   - "Insure package" checkbox → "Declared Value $" spinbutton
   - "Is Dangerous Goods" checkbox  (eParcel only)
   - Length / Width / Height spinbuttons (cm) + Weight (kg)
5. Click "Save" → toast: "Products Successfully Saved"
```

### Settings Navigation (for Settings-related features)

```
1. AU Post app sidebar → Settings  (/apps/aupost-qa/setting — SINGULAR)
2. Scroll to the relevant section (see Settings Sections list above)
3. Key global options:
   - "Is Insurance Required For Forward Shipments?" checkbox
   - "Is Delivery Signature Needed" combobox/dropdown
4. Save section
```

### Pickup Scheduling

```
1. AU Post app sidebar → PickUp  (/apps/aupost-qa/pickup)
2. Page heading: "Pickup"
3. Table columns: Orders, Pickup Status, Pickup Requested Date, Pickup Number
4. Schedule pickup → confirm toast: "Pickup requested."
```

### Rates Log

```
1. During manual label flow: after "Get Shipping Rates" → click ⋯ menu → "View Logs"
   → Dialog shows JSON Request (left textarea) + Response (right textarea) IN PAGE (no download)
2. After label generated: Order Summary → More Actions → Download Documents → ZIP with JSON
   OR: More Actions → How To → "Click Here" button → downloads RequestResponse ZIP
```

---

## Support Guide Tone

Professional, practical, support-ready.

Audience:

- support team
- demo team
- implementation/support leads

The support reader should be able to explain the feature to a merchant without asking engineering.

Use:

- clear brief description
- explicit account type coverage
- concrete paths and steps
- "what support should observe"

Avoid:

- technical words anywhere in the body — code, class, file, or method names, API or schema jargon, internal engineering terms. Three exemptions: the request/log callouts, the `Technical Cards` section, and toggle keys in the index table and `Toggles & Prerequisites` tables
- deep code/internal implementation details
- vague "works correctly" wording
- unsupported claims
- excessive QA/test-count language

---

## Per-Card Support Guide Required Sections

```markdown
# Support Guide: <Story ID or concise feature name>

## Brief Description
Very crisp. 1 short paragraph.

## Account Type Coverage
- **eParcel**: <what applies, or "Not affected">
- **MyPost Business**: <what applies, or "Not affected">
- If one account type only: state clearly "This feature is available for [eParcel / MyPost Business] accounts only."

## Toggles & Prerequisites
State whether a feature toggle is required.
If none: "No toggle required — available automatically."
List prerequisites and scope.

## Step-by-Step Support Walkthrough
Use Scenario A/B/C when useful. Put the exact navigation inside the action step, taken from the
APP NAVIGATION MAP and NAVIGATION STEP TEMPLATES above — for example Shopify admin Orders,
More Actions, "AU Post Generate Label", the SideDock options, app sidebar Shipping/Settings/
Products/PickUp/Rates Log/Manifest, or the Order Summary buttons.

## Expected Behaviour
Summarize the key signal support should observe: status badge text, downloadable label, UI change.
```

`Account Type Coverage` is the one section AU Post keeps that the other carrier guides do not — eParcel versus MyPost Business changes what support can promise, so it stays on every card. Account-type limits belong there, not in a separate limitations section.

Do not add `Release Details`, `Where to Find This in the App`, `Business-Safe Explanation`, `Merchant-Safe Explanation`, `Q&A` / `Common Questions & Troubleshooting`, `Support Escalation Packet`, `Known Limitations` / `Rollout Notes`, or `References`. The card section ends after `Expected Behaviour`, and navigation lives inside the walkthrough steps.

---

## Combined Support Guide Required Sections

```markdown
# <Release> Support Guide

## Included Story Cards
| Story ID | Story Title | Toggle Name | Trello card link |
|---|---|---|---|

## <Story ID> - <Card title>
### Brief Description
...

## Technical Cards
### <Story ID> - <Card title>
...
```

Do not add a `How Support Should Use This Package` section. The index page is followed directly by the first card section.

Index page rules:

- use exactly four columns: `Story ID`, `Story Title`, `Toggle Name`, `Trello card link`
- `Story ID` is the story/card number only
- `Story Title` is the card title
- `Toggle Name` is the exact toggle name, or `None` when the card needs no toggle. Source it from anywhere in the card evidence — description, comments, checklists, attachments, approved AC, TCs, QA notes — because the exact key is often only in a comment. Comma-separate multiple keys. Never guess a key; write `Not stated` and flag it when a card clearly needs one but names none
- list technical cards in their normal position here even though their body section moves to the end
- `Trello card link` is a markdown link to the card, labelled with the story id, for example `[941](https://trello.com/c/abc123)`; use `-` when no card URL is known

---

## Technical Cards Section Structure

```markdown
## Technical Cards

### <Story ID> - <Card title>
Two to four lines: what changed, and why it matters.
```

Rules:

- one `## Technical Cards` H2, placed after the last normal card section, and omitted when the release has no technical cards
- a technical card is developer-only work — API-only change, library or version upgrade, refactor, internal clean-up, infrastructure — with nothing support or the merchant can see or do
- a card with both a technical part and a visible part stays a normal card
- each entry is an H3 so the short entries flow together; the renderer already breaks a page before the `## Technical Cards` H2 itself, so never hand-place a break
- no walkthrough, toggles, account-coverage, or expected-behaviour subsections inside these entries
- plain wording still applies; name a version, endpoint, or field only when the entry makes no sense without it

---

## Combined Business Brief Required Structure

```markdown
# What's New: <Release>

## Release Overview
2-3 sentences describing the release value.

## Included Updates
| Story ID | Story Title | Toggle Name | Trello card link |
|---|---|---|---|

## <Story ID> - <Card title>
Per-card plain-English business brief.

## Technical Cards
### <Story ID> - <Card title>
...
```

---

## Per-Card Business Brief Format

```markdown
# <Feature Name in Plain English>
*One punchy sentence — the headline value for merchants.*

---

### Brief Description
2–3 sentences on what frustration or inefficiency existed before this change.

---

### What's New
- <Action verb + what merchant can now do>
- <Action verb + what merchant can now do>
- <3–5 bullets total>

---

### Who Benefits
- **<Merchant type>**: <how they benefit in 1–2 sentences>
- **<Merchant type>**: <how they benefit>

---

### Why It Matters
2–3 sentences on business outcome: time saved, fewer support tickets, merchant satisfaction.

---

### Availability
<eParcel only | MyPost Business only | Both account types> — available in <release name>.
If no setup needed: "Available automatically — no setup required."
```

### Business Brief Rules

- Max ~400 words total
- Plain business English only — no API, JSON, iframe, regex, backend, frontend
- No developer or QA names
- No test case counts or QA notes
- No internal Trello links in the body
- Highlight account type restriction if feature is eParcel-only or MyPost Business-only
- Only mention toggles if the merchant or support team must act to enable the feature

---

## Tone Guide

**Support Guide**: Professional, practical, support-ready. Clear paths and what to observe.

**Business Brief**: Plain English, merchant-friendly. Someone who has never opened the app should understand it in under 2 minutes.

---

## Release QA Guardrails

- Build release packages from full live Trello card context when available: description, labels, comments, checklists, approved AC/TCs, and AI QA evidence.
- Treat QA comments as required review input because late caveats often appear there.
- Exclude cards labelled `SL: ON Hold`, `SL: Carrier Platform`, `Spill Over`, or `SL: Closed By Support` from both the index table and the body, matching labels case-insensitively. Match on Trello labels, not on title text — an `SL:` prefix in a card title is a story id and never excludes a card. Include an excluded card only when the user names it. Report every exclusion and the label behind it; never drop a card silently.
- Run a toggle audit per card across the whole card, not only the description. The exact toggle key is often only in a QA or developer comment. Never guess a key. `detect_toggles` in this repo has not received the markdown-bold-key hardening MCSL and FedEx got, so a `**bold**` toggle key can be missed — prefer the card evidence and say when the helper missed one.
- Run a technical-card audit per card and collect developer-only cards into the trailing `Technical Cards` section.
- Run an account-type audit per card. eParcel versus MyPost Business is the axis that varies here, and it is never optional. Extra Cover is $5,000 AUD on eParcel and $1,000 AUD on MyPost Business; international is eParcel only; Dangerous Goods is eParcel domestic only.
- After a release package is generated, send the consolidated toggle list as a Slack DM to `ashok@pluginhive.com` per the `Toggle List Follow-Up` section of `SKILL.md`. AU Post toggle keys follow the FedEx shop-domain convention, `"<shop>.myshopify.com.<flag>": true,`. There is no default QA store here — ask when no shop domain is stated. Skip the DM when no card has a toggle.
- Do not include a generic `Where to Find This in the App` section. The detailed walkthrough is the source of truth for where support should go.
- Keep feature-specific paths and carrier-specific steps inside the walkthrough sections.
- Every story card section starts on a new PDF page, including the first — the index page stands alone. `render_pdf_bytes` inserts a page break before each `<Story ID> - <Title>` heading, so do not add manual page breaks or blank filler.
- Before final PDF generation, verify no card starts at the bottom of a page without the card detail table/content following on the same page.
- Run a card-by-card payload/log audit before final PDF generation:
  - If QA/support must inspect a carrier request, response, payload, rates log, createShipment request/response JSON, tracking payload, or report source field, include the exact node or log field.
  - Put exact nodes/fields in the walkthrough as a highlighted callout using one of these exact labels: `Request node to verify:`, `Request nodes to verify:`, `Request/response nodes to verify:`, or `Request/log fields to verify:`.
  - Use the exact AU Post paths from the `Checking Label/Shipment Request` section above.
  - Say where the payload comes from: the rates log dialog during the label flow, or `More Actions -> Download Documents` / `More Actions -> How To -> Click Here` after the label exists.
  - Keep those node names out of merchant-safe wording.
  - Do not invent fields for UI-only, sync-only, report-only, or performance-only cards.

---

## PDF Rendering

Use `pipeline.handoff_docs.render_pdf_bytes` through the skill helper script `scripts/render_handoff_pdf.py`. This gives the shared PluginHive handoff styling — the same header panel, palette, tables, and footer as the MCSL and FedEx handoff PDFs.

For release handoff, render one combined Support Guide PDF and one combined Business Brief PDF. Create individual PDFs only for explicit single-card requests.

---

## Quality Checklist (before finalising)

- [ ] Navigation paths use exact route names (not guesses) from APP NAVIGATION MAP
- [ ] Button/link names match EXACT labels from NAVIGATION STEP TEMPLATES, including `/apps/aupost-qa/setting` in the singular and the exact casing of "Au Post Return Label"
- [ ] Account type restriction stated clearly on every card (eParcel-only, MyPost Business-only, or both)
- [ ] Extra Cover limits stated correctly ($5,000 eParcel / $1,000 MyPost Business)
- [ ] Exact request/log node names cited as highlighted callouts where verification is possible
- [ ] No technical jargon in the body of either document, outside the three exemptions
- [ ] No card carrying an excluded label reached the index table or the body
- [ ] Technical-only cards sit in the trailing `Technical Cards` section
- [ ] Every card's toggle was searched for across comments, checklists, and QA evidence
- [ ] No invented toggles, limitations, or ownership
- [ ] Business Brief under 400 words
