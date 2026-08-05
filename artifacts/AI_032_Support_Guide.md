# AU Post App — Support Guide

**Feature**: AI-032 — Signature + Date and QTY × SKU on AU Post Labels [#394693]
**Release**: SL AuPost v1.0.37
**Date**: 2026-07-23
**Trello**: https://trello.com/c/06hQ2JhH
**Developed by**: athiramohan (card member — confirm role)
**Tested by**: arshiya
**Account Type(s)**: eParcel (SKU with Quantity is eParcel-only; sender name + date applies to all non-return shipments)
**QA Status**: QA_VERIFIED

---

## Feature Summary

This release adds two label enhancements:

**1. Product SKU with Quantity on the label (customer_reference_2).**
A new reference option, **"Product SKU with Quantity (e.g. 2X,1G)"**, can be selected in Settings so labels print each product's SKU prefixed by its quantity. This is gated behind a per-shop feature toggle and is only available for eParcel accounts.

**2. Sender Name + Date in the label signature section.**
The app now sends `international_parcel_sender_name` on every item for all non-return shipments (domestic + international). Australia Post uses this field to print the sender name and the label creation date in the signature section — visible on international CN22/CN23 customs documents. No setup is required; it works automatically.

## Account Type Coverage

- **eParcel**: Both features apply. SKU with Quantity option appears in Settings when the toggle is enabled; sender name + date prints on international CN22/CN23 documents.
- **MyPost Business**: The **Product SKU with Quantity option is NOT available** for MyPost Business accounts. MyPost Business is domestic-only, and QA observed the signature/date is not printed on domestic labels, so no merchant-visible change.
- **StarTrack**: The SKU with Quantity option is NOT available for StarTrack accounts.

## Toggles & Prerequisites

**Feature 1 — Product SKU with Quantity (toggle required, PluginHive internal):**
1. Add `"<shopname>.myshopify.com.sku.with.quantity.on.label.enabled": true` to `featureToggles.json` (requires a dev/ops change — support cannot do this from the app UI).
2. In the app: Settings → Labels section → enable **"Show References On Labels"**.
3. A new dropdown option **"Product SKU with Quantity (e.g. 2X,1G)"** appears — select it and Save.

**Toggle OFF behaviour**: the dropdown option disappears; the select falls back to **Product Names**; labels print Product Names. The saved DB value is preserved — re-enabling the toggle restores the merchant's previous selection.

**Feature 2 — Sender Name + Date**: No toggle required — available automatically for all non-return shipments. The printed name comes from the ship-from address **person name**, falling back to the **company name** when no person name is set.

## Where to Find This in the App

- Reference option: AU Post app sidebar → **Settings** (`/apps/aupost-qa/setting`) → Documents/Labels section → **"Show References On Labels"** → reference dropdown
- Label generation: Shopify admin → **Orders** → click order → **More Actions** → **"AU Post Generate Label"**
- Verification JSON: Order Summary → **More Actions** → **Download Documents** (ZIP with label PDF + request/response JSON)

## Step-by-Step Walkthrough (Support / Demo)

### Scenario A — SKU with Quantity on the label (eParcel)

1. Confirm the shop's feature toggle is enabled in `featureToggles.json` (internal).
2. AU Post app sidebar → **Settings** (`/apps/aupost-qa/setting`) → Documents/Labels section.
3. Enable **"Show References On Labels"**, select **"Product SKU with Quantity (e.g. 2X,1G)"**, Save.
4. Shopify admin → **Orders** → click an order row → **More Actions** → **"AU Post Generate Label"**.
5. In the app label page: **"Generate Packages"** → **"Get Shipping Rates"** → select a rate radio → **"Generate Label"**.
6. On the Order Summary page: **More Actions** → **Download Documents** → open the createShipment request JSON.
7. Verify `customer_reference_2` follows the format, e.g. `3 ABC,DEFGHIJ,2 XYZ,-`.

### Scenario B — Sender Name + Date on CN22/CN23 (international, eParcel)

1. Generate a label for an **international** order (same manual flow as above).
2. Order Summary → **More Actions** → **Download Documents**.
3. In the request JSON verify `items[0].international_parcel_sender_name` = ship-from person name (or company name when no person name is set).
4. Open the label PDF → the CN22/CN23 signature section shows the **sender name + label creation date**.
5. Generate a **return label** (Order Summary → "Return packages" tab → "Return Packages" → "Refresh Rates" → "Generate Return Label") → verify `international_parcel_sender_name` is **not** sent for return labels.

## Expected Behaviour — What Support Should Observe

**SKU with Quantity string rules (`customer_reference_2`):**
- Each SKU trimmed to **10 characters**
- Quantity > 1 → prefixed with quantity + space: `3 MYSKU`
- Quantity = 1 → no prefix: `MYSKU`
- Product without SKU → `-`
- All items comma-separated; whole string capped at **50 characters** (AU Post API limit)
- Example: `3 ABC,DEFGHIJ,2 XYZ,-`

**Sender name + date:**
- `international_parcel_sender_name` present on every item for non-return shipments
- Printed date matches the label generation date
- Field skipped on return labels
- Existing customs information (values, descriptions) unchanged

**Toggle interplay:** turning the toggle off after a merchant saved "SKU with Quantity" → labels print Product Names (server fallback); re-enabling restores the saved selection.

## References

- [Trello card](https://trello.com/c/06hQ2JhH)
- [PluginHive AU Post app docs](https://www.pluginhive.com/knowledge-base/australia-post-shopify-shipping-app-rates-label-tracking/)
- [eParcel label printing guide](https://www.pluginhive.com/knowledge-base/australia-post-eparcel-label-printing-in-shopify/)
- [International shipping guide](https://www.pluginhive.com/knowledge-base/australia-post-international-shipping-shopify/)
