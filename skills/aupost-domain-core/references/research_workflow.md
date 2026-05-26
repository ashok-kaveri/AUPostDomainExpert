# AU Post Domain Research Workflow

## Local Sources

Read in this order when researching for the AU Post project:

1. `CLAUDE.md` — project architecture, session context, account types, key locators
2. `pipeline/` modules — smart_ac_verifier.py, card_processor.py, domain_validator.py, requirement_research.py
3. `config.py` — env-driven paths and model settings
4. Automation repo at `AUTOMATION_CODEBASE_PATH` (`/Users/madan/Documents/AU_Post/aupost-test-automation`)
   - `auPost/support/pages/` — all POM page objects (basePage.ts, shippingPage.ts, manualLabelPage.ts, orderSummaryPage.ts, settingsPage.ts, productsPage.ts, productDetailsPage.ts, pickupPage.ts, ratesLogFaqPage.ts, auPostAppPage.ts)
   - `auPost/support/pages/shopifyUI/` — shopify_OrderSummary.ts, shopify_OrderGrid.ts
5. Backend repo at `BACKEND_CODE_PATH` (`/Users/madan/Documents/shopify-australia-post-app`)
6. Frontend repo at `FRONTEND_CODE_PATH` (`/Users/madan/Documents/shopify-au-post-web-client`)
7. Wiki at `AUPOST_WIKI` (`/Users/madan/Documents/aupost-wiki`)
8. ChromaDB RAG: `aupost_knowledge` (domain) + `aupost_code_knowledge` (code)

## Browse Triggers

Browse official/current sources when:
- user explicitly asks to research, browse, verify, or use latest/current information
- AU Post REST API limits or service codes need verification
- eParcel vs MyPost Business feature differences are unclear
- PluginHive documentation may be outdated in RAG
- a public URL is referenced that has not been read yet

## Preferred Web Sources

- Australia Post developer documentation: https://developers.auspost.com.au/
- PluginHive AU Post app docs: https://www.pluginhive.com/knowledge-base/ (AU Post section)
- Official Shopify docs: https://shopify.dev/
- PluginHive product page: https://www.pluginhive.com/product/australia-post-shopify-shipping-app-rates-label-tracking/

## Key Domain Facts To Verify Online

When local RAG is uncertain:
- Current eParcel service codes and surcharges
- MyPost Business rate calculation rules
- AU Post Extra Cover limits and claim process
- Dangerous Goods classification rules
- International service eligibility by country

## Research Summary Shape

Return results as:
- **Local project**: what CLAUDE.md / AGENTS.md / POM says
- **Automation pattern**: what the automation spec or POM page object does
- **Web/source**: what official docs say (with URL)
- **Open question**: anything that could not be resolved

## Applying Research To US/AC

Add to AC output:
- account-type prerequisites (eParcel vs MyPost Business)
- AU Post API constraints (declared value limits, service code availability)
- edge scenarios found in research (e.g. Dangerous Goods not allowed for MyPost Business)
- regression scenarios for bug cards
- source attribution for each scenario

## Applying Research To TC

When generating TCs:
- choose browser-verifiable scenarios only
- reference correct app surface (iframe vs Shopify admin)
- specify exact prerequisites (account type, order state, SideDock options)
- specify evidence source (Strategy 1: label status badge, Strategy 2: Download Documents ZIP JSON, Strategy 3: Print Documents PDF)

## Applying Research To AI QA

When running browser verification:
- use automation POM locators before improvising
- respect iframe vs Shopify admin split
- use EXACT SideDock checkbox names: "Request Signature?", "Authority to Leave", "Insure package"
- use EXACT Shopify More Actions link names: "AU Post Generate Label", "Au Post Return Label"
- never change global Settings without cleanup plan
- ask QA if genuinely blocked after 12+ steps
