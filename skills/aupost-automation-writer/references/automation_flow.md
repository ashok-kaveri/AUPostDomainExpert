# AU Post Automation Writer Flow

This reference mirrors the dashboard `automation_writer.py` and `chrome_agent.py` conventions.

## Dashboard Flow

1. Find existing POM for the relevant page
2. Check AI QA locator trace for {card_id}
3. Navigate to real page in automation repo
4. Append new methods to existing POM OR create new POM class
5. Create new spec file in appropriate tests/ folder
6. Self-review spec against spec contract rules
7. Optionally run if QA asks
8. Commit only when explicitly asked

## Existing POM Priority

Always check these first — do NOT create duplicate locators:

```
auPost/support/pages/aupost/
  basePage.ts            ← iframe selector, navigateToAuPostRoute()
  auPostAppPage.ts       ← sidebar nav, navigateToAuPostRoute(route)
  shippingPage.ts        ← orders grid, 5 tabs, order row click
  manualLabelPage.ts     ← Generate Packages, Get Shipping Rates, Generate Label, SideDock
  orderSummaryPage.ts    ← Packages tab, Return packages tab, More Actions, Download Documents
  settingsPage.ts        ← ALL settings sections, Edit buttons, Save buttons
  productsPage.ts        ← Products table, searchAndOpenProduct()
  productDetailsPage.ts  ← dimensions, signature dropdown, dangerous goods, save
  pickupPage.ts          ← pickup table, schedule, toast
  ratesLogFaqPage.ts     ← View button, dialog, request/response textareas, closeLogsDialog()
  
auPost/support/pages/shopifyUI/
  shopify_OrderSummary.ts ← More actions button, AU Post Generate Label link, Au Post Return Label link
  shopify_OrderGrid.ts    ← order search, filter
```

## Automatable Case Filter

**Automate** (Positive and UI-safe Edge):
- Label generation flows (manual: Generate Packages → Get Shipping Rates → Generate Label)
- SideDock options (Request Signature?, Authority to Leave, Insure package, Dangerous Goods)
- Product configuration (dimensions, Is Signature Needed dropdown, Declared Value $)
- Settings configuration and persistence
- Return label generation (Way A from app, Way B from Shopify admin)
- Order grid filtering and tab navigation
- Pickup scheduling
- Download Documents ZIP and JSON field verification

**Skip** (do not automate):
- Backend-only API behavior (no UI surface)
- Cases requiring mock data injection
- MyPost Business international (not supported — will fail by design)
- Mobile / responsive / viewport
- Cases requiring real carrier network responses with specific values

## Assertions

Prefer final-state assertions:
```typescript
// Good — final state
await expect(pages.orderSummaryPage.labelGeneratedBadge).toBeVisible({ timeout: 30000 });
await expect(pages.shippingPage.orderRow(orderId)).toHaveText('label generated');

// Avoid — weak visibility check  
await expect(someElement).toBeVisible();  // without meaningful state check
```

Never use `page.waitForTimeout()` > 3000ms — use `expect()` with timeout instead.

## Critical Spec Contracts

```typescript
// ✅ Correct imports
import { test, expect } from '../../src/setup/fixtures';
import ShopifyOrderUploader from '../../src/helpers/createOrder';

// ✅ Always serial mode
test.describe.configure({ mode: 'serial' });

// ✅ Store from env
const store = process.env.STORE;

// ✅ Order creation in beforeAll
test.beforeAll(async () => {
  orderUploader = new ShopifyOrderUploader();
  sharedOrderID = (await orderUploader.uploadOrder()) as string;
  expect(sharedOrderID).toBeTruthy();
});

// ✅ Meaningful assertion in each test
test('2. Generate label', async ({ pages }) => {
  test.setTimeout(120000);
  await pages.manualLabelPage.generateLabelInApp();
  await expect(pages.orderSummaryPage.packagesSection).toBeVisible();
});

// ❌ Never use test.only
// ❌ Never import test from @playwright/test — must use fixtures
// ❌ Never put locators inside methods — must be readonly constructor properties
```

## Locator Trace Usage

When `data/ai_qa_locator_traces/{card_id}.json` exists:
1. Read the trace for exact button/field names Claude observed in the browser
2. Use `recommended_locators` to add new POM properties
3. Use `steps` to understand the flow
4. Confirm `surface` (iframe vs page) for each locator
5. Do NOT create duplicate locators if already in existing POM

## Route Helper

```typescript
// In any page class extending BasePage:
await this.navigateToAuPostRoute('shopify');    // → /apps/aupost-qa/shopify
await this.navigateToAuPostRoute('setting');    // → /apps/aupost-qa/setting (SINGULAR)
await this.navigateToAuPostRoute('products');   // → /apps/aupost-qa/products
await this.navigateToAuPostRoute('pickup');     // → /apps/aupost-qa/pickup
await this.navigateToAuPostRoute('rateslog');   // → /apps/aupost-qa/rateslog
await this.navigateToAuPostRoute('faq');        // → /apps/aupost-qa/faq
await this.navigateToAuPostRoute('manifest');   // → /apps/aupost-qa/manifest
```
