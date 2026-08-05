# AU Post App - Support Guide

**Release**: SL AuPost v1.0.38  
**Date**: July 31, 2026

## Index

| Story Card | Ticket | Title |
|---|---|---|
| AI-034 | #395896 | Non-Shippable Digital Product Triggers Spurious $0 Shipping Line |
| AI-036 | - | Country-wise HS Codes for Products |

---

## AI-034 - Non-Shippable Digital Product Triggers Spurious $0 Shipping Line

**Ticket**: #395896 &nbsp;|&nbsp; **Type**: Bug fix &nbsp;|&nbsp; **Account type**: eParcel, MyPost Business and StarTrack - checkout rates only  
**Trello**: https://trello.com/c/PBcRsF4F

### Brief Description

When a cart mixed shippable products with a free non-shippable digital item, Shopify split it into separate delivery groups and asked the app for rates for the digital-only group. The app answered with a $0.00 Australia Post Standard rate, so the placed order carried two AU Post shipping lines - the one the shopper chose plus a phantom $0.00 line, which broke the merchant's ERP sync. The rates service now ignores non-shippable items entirely.

### At a Glance

- Reported by a Shopify Plus merchant whose orders auto-sync to an external ERP (store: tropeaka).
- **Not a mischarge** - the order total was always correct. The damage was the duplicate shipping line.
- Fix is in the rates service only. Label generation, manifests and tracking are untouched.
- No merchant setup or toggle needed - live for every store on this release.

### Where to Find It

- No UI change. Verify at Shopify checkout and on the placed order's shipping lines in Shopify admin.
- AU Post app sidebar -> **Rates Log** (/apps/aupost-qa/rateslog) to inspect the rate request and response.
- A product counts as non-shippable when **This is a physical product** is unchecked in Shopify.

### Walkthrough

1. Shopify admin -> Products -> open the digital product -> confirm **This is a physical product** is unchecked.
2. Add one physical product plus the free digital product to the cart and go to checkout.
3. Confirm AU Post rates appear once, for the shippable group only. Select a service and place the order.
4. Shopify admin -> Orders -> open the order -> check the shipping lines: exactly one AU Post line, matching what the shopper chose.
5. Repeat with a digital-only cart -> no AU Post rates are returned at all.
6. AU Post app -> **Rates Log** -> open the newest entry to confirm the non-shippable item was excluded from weight and packing.

### Expected Behaviour

- Digital-only cart or delivery group -> empty rates, no AU Post shipping option offered.
- Mixed cart -> rates use the shippable items only; non-shippable items are excluded from weight and packing.
- Placed order carries exactly one AU Post shipping line - no spurious $0.00 Standard line.
- Checkout never blocks, errors or stalls when rates are suppressed for a digital-only group.
- Same behaviour on eParcel, MyPost Business and StarTrack, domestic and international.
- Only items Shopify flags as non-shippable are skipped. A physical product with 0 weight is still shippable and is still rated.

---

## AI-036 - Country-wise HS Codes for Products

**Ticket**: - &nbsp;|&nbsp; **Type**: New feature &nbsp;|&nbsp; **Account type**: HS Codes should be supported for both Australia Post eParcel and MyPost Business.  
**Trello**: https://trello.com/c/lBaBSl2D

### Brief Description

The correct HS (tariff) code often differs by destination country, but the app previously stored one global HS code per variant and sent it on every international customs declaration. The app now mirrors Shopify's country-specific HS codes read-only, and at label time picks the code matching the shipment's destination country. If no country-specific code exists, the global HS code is used. Shipped behind a PluginHive feature toggle.

### At a Glance

- Country HS codes are **read-only** in the app - merchants keep editing them in Shopify.
- Toggle-gated (**country.specific.hs.codes**) - with the toggle off, behaviour is identical to today.

### Where to Find It

- Shopify admin -> Products -> open the variant -> **Customs information** - this is where HS codes and Country of Manufacture are entered.
- AU Post app sidebar -> **Products** (/apps/aupost-qa/products) -> click the product row -> product summary shows a read-only **HS codes by country/region** grid.
- The global HS code field in the app stays editable and is used as the fallback.

### Walkthrough

1. Shopify admin -> Products -> open a variant -> **Customs information** -> set a default HS code and Country of Manufacture, then add one or more country-specific HS codes.
2. AU Post app -> **Products** -> search the product -> open it -> confirm the **HS codes by country/region** grid shows the codes synced from Shopify.
3. Place an international order to a country that has a country-specific code.
4. Shopify admin -> Orders -> open the order -> **More Actions** -> **AU Post Generate Label** -> Generate Packages -> Get Shipping Rates -> select a service -> **Generate Label**.
5. Order Summary -> **More Actions** -> **Download Documents** -> open the request JSON and confirm the tariff code is the country-specific one; check the label, commercial invoice and packing slip show the same code.
6. Repeat for a destination with no country-specific code -> confirm the global HS code is used instead.

### Expected Behaviour

- Adding or updating an HS code and Country of Manufacture in Shopify appears in the app product summary after webhook sync.
- International label to a country **with** a specific code -> that code is sent as the tariff code and printed on the label, commercial invoice and packing slip.
- No country-specific code -> the global HS code is used. Neither configured -> the order still processes normally.
- Domestic orders and toggle-off behave exactly as before the release. Works for products created before and after the release.

