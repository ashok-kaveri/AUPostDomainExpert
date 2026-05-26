---
name: aupost-automation-writer
description: Use when working inside the AUPostDomainExpert project after US/AC generation, dashboard TC generation, and AI QA browser verification are complete, and the user wants Playwright TypeScript automation written for an AU Post Shopify card. Reuse existing automation POM locators first, create new locators only when missing, use saved AI QA locator traces when available, and write spec files in the aupost-test-automation repo.
---

# AU Post Automation Writer

Use this skill to write Playwright TypeScript automation for the AU Post Shopify app after TCs are reviewed and AI QA evidence is captured.

## First Reads

1. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/CLAUDE.md`
2. Read the automation flow reference:
   `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-automation-writer/references/automation_flow.md`
3. Check for AI QA locator trace:
   `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/data/ai_qa_locator_traces/{card_id}.json`
4. Inspect existing POMs in `/Users/madan/Documents/AU_Post/aupost-test-automation/auPost/support/pages/`

## Automation Repo

`AUTOMATION_CODEBASE_PATH`: `/Users/madan/Documents/AU_Post/aupost-test-automation`

## POM Priority

Always search and reuse existing POMs before creating new locators:

| Page | File |
|---|---|
| Shipping grid | `auPost/support/pages/aupost/shippingPage.ts` |
| Manual label | `auPost/support/pages/aupost/manualLabelPage.ts` |
| Order summary | `auPost/support/pages/aupost/orderSummaryPage.ts` |
| Settings | `auPost/support/pages/aupost/settingsPage.ts` |
| Products list | `auPost/support/pages/aupost/productsPage.ts` |
| Product details | `auPost/support/pages/aupost/productDetailsPage.ts` |
| Pickup | `auPost/support/pages/aupost/pickupPage.ts` |
| Rates log / FAQ | `auPost/support/pages/aupost/ratesLogFaqPage.ts` |
| App navigation | `auPost/support/pages/aupost/auPostAppPage.ts` |
| Base class | `auPost/support/pages/basePage.ts` |
| Shopify order summary | `auPost/support/pages/shopifyUI/shopify_OrderSummary.ts` |
| Shopify order grid | `auPost/support/pages/shopifyUI/shopify_OrderGrid.ts` |

## Spec File Rules

Create a separate new spec file per card in the appropriate folder:

| Feature | Folder |
|---|---|
| Label generation variants | `tests/label_generation/` |
| Return labels | `tests/returnLabels/` |
| Packaging options | `tests/packaging/` |
| Signature / insurance / DG / ATL | `tests/product_Special_Service/` |
| Pickup requests | `tests/pickup/` |
| App installation / onboarding | `tests/onboarding/` |
| Product configuration | `tests/product/` |
| Order summary / documents | `tests/orderSummary/` |
| Settings | `tests/settings/` |

## Spec Contract (required for all specs)

```typescript
import { test, expect } from '../../src/setup/fixtures';
import ShopifyOrderUploader from '../../src/helpers/createOrder';

const store = process.env.STORE;

test.describe.configure({ mode: 'serial' });

test.describe('Feature Name', { tag: '@smoke' }, () => {
  let sharedOrderID: string;
  let orderUploader: ShopifyOrderUploader;

  test.beforeAll(async () => {
    orderUploader = new ShopifyOrderUploader();
    sharedOrderID = (await orderUploader.uploadOrder()) as string;
    expect(sharedOrderID).toBeTruthy();
  });

  test('1. Navigate to order', async ({ pages }) => {
    test.setTimeout(60000);
    await pages.shopifyAdmin.navigateToStore(store);
    await pages.shopifyAdmin.searchAndOpenOrder(sharedOrderID);
  });
});
```

## POM Rules

```typescript
import { Page, Locator } from '@playwright/test';
import BasePage from '../basePage';

export class MyNewPage extends BasePage {
  readonly myButton: Locator;  // ← ALL locators readonly in constructor

  constructor(page: Page) {
    super(page);
    // App iframe content → use this.appFrame
    this.myButton = this.appFrame.getByRole('button', { name: 'Submit' });
    // Shopify admin content → use this.page
    this.shopifyLink = this.page.getByRole('link', { name: 'Orders' });
  }
}
```

## Critical Locator Rules

- **AU Post iframe selector** (used by `BasePage.appFrame`):
  `iframe[src*="qa-aupost.pluginhive.io"], iframe[src*="pluginhive.io"], iframe[src*="aupost"]`
  (NOT `iframe[name="app-iframe"]` — that is the FedEx selector; never use it in AU Post tests)
- App content → always use `this.appFrame` (FrameLocator)
- Shopify admin content → use `this.page`
- More Actions on Shopify page → `this.page.getByRole('button', { name: 'More actions' }).first()`
- AU Post Generate Label link → `this.page.getByRole('link', { name: /AU\s*Post Generate Label/i })`
- Au Post Return Label link → `this.page.getByRole('link', { name: 'Au Post Return Label' })`
- Signature checkbox → `this.appFrame.getByRole('checkbox', { name: 'Request Signature?' })`
- Insurance checkbox → `this.appFrame.getByRole('checkbox', { name: /Insure package|Insurance/i })`
- Declared Value → `this.appFrame.getByRole('spinbutton', { name: 'Declared Value' })`
- Settings route → `this.navigateToAuPostRoute('setting')` ← SINGULAR

## Automatable Cases

Prefer: Positive and UI-safe Edge cases
Skip: backend-only, API mocking required, unstable negatives, mobile viewport

## Result Format

Return:
- Automation decision (automate / skip per TC, with reason)
- Locator trace used (if any)
- Files created or modified
- Cases automated vs skipped
- Test run result (if run)
- Follow-up needed (new POM locators required, etc.)
