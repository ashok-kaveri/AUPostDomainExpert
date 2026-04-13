"""
PluginHive Australia Post Shopify App — Official Documentation Loader

Content based on the official PluginHive Australia Post Shopify App guides.
Reference: https://www.pluginhive.com/product/australia-post-shopify-shipping-app-rates-label-tracking/
"""
from __future__ import annotations
import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config

logger = logging.getLogger(__name__)

_SOURCE_URL = "https://www.pluginhive.com/product/australia-post-shopify-shipping-app-rates-label-tracking/"

_ARTICLES = [
    {
        "title": "Australia Post Shopify App — Installation and Account Setup",
        "section": "setup",
        "content": """
How to Set Up the Australia Post Shopify App (PH Ship, Rate, and Track)

INSTALLATION:
Navigate to Shopify Settings → Apps and sales channels → Shopify App Store.
Search for "Australia Post Shipping" or "PH Ship, Rate and Track" and click Install.
Approve the subscription plan.
Complete app installation: enter email and phone number, click "Get Started".

AUSTRALIA POST ACCOUNT TYPES SUPPORTED:
1. eParcel — Australia Post business account for parcel shipping (domestic + international)
   Requires: eParcel account credentials (Account Number, API key/password)
2. MyPost Business — Australia Post business account for smaller parcels
   Requires: MyPost Business account credentials

ACCOUNT SETUP — eParcel:
Navigate to App Settings → Account Details.
Select account type: eParcel.
Enter your Australia Post eParcel credentials:
- Account Number
- API Key / Password
Click "Save" and "Verify Connection."

ACCOUNT SETUP — MyPost Business:
Navigate to App Settings → Account Details.
Select account type: MyPost Business.
Enter your MyPost Business credentials.
Click "Save" and "Verify Connection."

SHOP CONTACT DETAILS:
Edit in App Settings → Shop Contact Details:
- Sender name, company, phone, email
- Ship-from address (must be a valid Australian address for domestic)

MULTIPLE ACCOUNTS:
Navigate to Settings → Account Details → Add Account.
Assign each account to specific ship-to countries or regions.
""",
    },
    {
        "title": "Australia Post Shopify App — Shipping Rates at Checkout",
        "section": "rates",
        "content": """
Displaying Live Australia Post Shipping Rates on Shopify Checkout

PREREQUISITES:
1. Enable Carrier-Calculated Shipping on your Shopify store (requires Basic plan or higher).
2. Enable "Ship Rate & Track" app in Shopify Shipping Profile.

RATE DISPLAY CONFIGURATION (App Settings → Rate Settings):
- Enable/disable specific Australia Post services
- Add rate adjustments: fixed amount ($) or percentage (%) markup/markdown per service
- Display estimated delivery time for services (if available)
- Add buffer time for estimated delivery (in days)
- Display rates with or without tax
- Configure fallback rates for when Australia Post API is unavailable

SUPPORTED DOMESTIC SERVICES (eParcel):
- Australia Post Parcel Post
- Australia Post Express Post
- Australia Post Parcel Post + Signature
- Australia Post Express Post + Signature

SUPPORTED DOMESTIC SERVICES (MyPost Business):
- MyPost Business Standard
- MyPost Business Express

SUPPORTED INTERNATIONAL SERVICES:
- Australia Post International Economy
- Australia Post International Standard
- Australia Post International Express
- Australia Post Pack & Track International
- Australia Post Express Mail International (EMS)

RATE ADJUSTMENTS:
Add markup or discount per service: App Settings → Rate Settings → per service row.
Options:
- Fixed: add/subtract a fixed dollar amount
- Percentage: add/subtract a percentage of the calculated rate

FALLBACK RATES:
Configure flat rates for when Australia Post API is down:
App Settings → Rate Settings → Fallback Services.
Set separate fallback rates for Domestic and International.

SHIPMENT CUT-OFF TIME:
App Settings → Rate Settings → Shipment Cut Off Time.
Orders placed after this time are processed next business day.
""",
    },
    {
        "title": "Australia Post Shopify App — Label Generation (eParcel)",
        "section": "labels_eparcel",
        "content": """
eParcel Label Generation in the Australia Post Shopify App

ORDER REQUIREMENTS:
Orders must be in "Unfulfilled" status to generate labels.

MANUAL LABEL GENERATION (single order):
1. Go to Shopify Orders → click an order → More Actions → "Generate Label"
2. App opens (inside iframe) with packaging and rate options.
3. LEFT panel: Generate Packages → Get Shipping Rates → select service → Generate Label
4. RIGHT panel (SideDock): configure additional options before generating
   - Signature on Delivery
   - Extra Cover (insurance)
   - Authority to Leave (ATL)

LABEL GENERATION — SideDock Options (eParcel):
- Signature on Delivery: recipient must sign for parcel
- Extra Cover: declare value for insurance (up to $5,000 AUD)
- Authority to Leave: parcel left at door without signature
- Safe Drop: leave parcel in safe location
- Dangerous Goods: declare if shipment contains dangerous goods

AUTO LABEL GENERATION (bulk):
1. Shopify Orders → select multiple orders → More Actions → "Auto-Generate Labels"
2. App generates labels using saved settings.
3. Redirects to Shipping section in app.

ORDER SUMMARY PAGE (after label generation):
- "Print Documents" — opens document viewer in new tab
- "More Actions" dropdown:
  - "Download Documents" → downloads ZIP (label PDF + request/response JSON)
  - "Cancel Label"
  - "Return Label"
- Two tabs: "Packages" | "Return packages"
- Track Shipment link visible once label is generated

LABEL CANCELLATION:
Shipping tab → Label Generated section → click order → More Actions → "Cancel Label"
Note: Some labels may not be cancellable after lodgement.

DOCUMENT FORMATS:
- Label size: A4 or A6 (thermal)
- Includes: shipping label with barcode (AusPost Article ID), sender/receiver details
""",
    },
    {
        "title": "Australia Post Shopify App — Label Generation (MyPost Business)",
        "section": "labels_mypost",
        "content": """
MyPost Business Label Generation in the Australia Post Shopify App

MyPost Business is Australia Post's online shipping solution for smaller businesses.
Labels are generated via MyPost Business account credentials.

LABEL GENERATION:
Same flow as eParcel:
1. Shopify Orders → More Actions → "Generate Label"
2. Select service (Standard or Express)
3. Configure delivery options in SideDock
4. Generate Label

MYPOST BUSINESS DELIVERY OPTIONS (SideDock):
- Signature on Delivery
- Authority to Leave (ATL)
- Extra Cover (insurance up to $1,000 AUD for MyPost Business)

DIFFERENCES FROM eParcel:
- Lower maximum coverage amount ($1,000 vs $5,000 for eParcel)
- Suitable for smaller parcel volumes
- Uses cubic weight calculation for large, lightweight packages
- No dangerous goods support (residential only)

TRACKING:
MyPost Business labels include Australia Post tracking number (Article ID).
Customers can track via auspost.com.au or the app's tracking feature.
""",
    },
    {
        "title": "Australia Post Shopify App — Product Configuration",
        "section": "products",
        "content": """
Product Configuration in the Australia Post Shopify App

WEIGHT AND DIMENSIONS (Required for accurate rates):
Add product weight: Shopify → Products → Shipping tab.
Add dimensions: App's Products section (L × W × H in cm, weight in kg).
Australia Post charges by actual weight OR cubic weight (whichever is greater).

CUBIC WEIGHT CALCULATION:
Formula: Length (cm) × Width (cm) × Height (cm) ÷ 4000
If cubic weight > actual weight, cubic weight is charged.

PACKAGING CONFIGURATION:
Navigate to App Settings → Packaging.
Options:
1. Custom Box Packing: define your own box dimensions
2. Weight-Based Packing: pack by maximum weight per package
3. Pack Items Individually: each item ships in its own package

DEFAULT DIMENSIONS:
Configure in Packaging Settings → More Settings.
Required for products without explicit dimensions.

SIGNATURE ON DELIVERY (per product):
Products settings → click product → set Signature on Delivery option.
Options: None / Required
Global override available in SideDock during label generation.

AUTHORITY TO LEAVE (per product):
Products settings → click product → set Authority to Leave.
Options: None / Allowed
Note: ATL is not available for Signature on Delivery parcels.

EXTRA COVER / INSURANCE (per product):
Set declared value per product: Products → Shipping Details → Declared Value.
Extra Cover is purchased separately during label generation in the SideDock.
Maximum Extra Cover: $5,000 AUD (eParcel) / $1,000 AUD (MyPost Business)
""",
    },
    {
        "title": "Australia Post Shopify App — Return Labels",
        "section": "returns",
        "content": """
Return Label Generation in the Australia Post Shopify App

TWO ENTRY POINTS:

WAY A — From app Order Summary:
Order Summary → "Return packages" tab → "Return Packages" button
→ Enter return quantity → "Refresh Rates" → select service → "Generate Return Label"
→ Verify: "SUCCESS" badge + "Download Label" link visible

WAY B — From Shopify admin order page:
Shopify Orders → click order → More Actions → "Generate Return Label"
(NOT "Create return label" — that is a Shopify-native feature, different thing)

RETURN LABEL OPTIONS:
- Service: Parcel Post Return / Express Post Return
- Sender becomes receiver (return to origin)
- Return label can be emailed to customer

RETURN LABEL SETTINGS:
Configure in App Settings → Return Settings:
- Default return service
- Auto-print return label with forward label
""",
    },
    {
        "title": "Australia Post Shopify App — Tracking and Notifications",
        "section": "tracking",
        "content": """
Shipment Tracking and Notifications in the Australia Post Shopify App

TRACKING:
Once a label is generated, an Australia Post Article ID (tracking number) is assigned.
Track shipments: Shipping → Label Generated → click order → "Track Shipment"

CUSTOMER TRACKING NOTIFICATIONS:
Australia Post automatically notifies customers at key shipment events:
- Shipment accepted
- In transit
- Out for delivery
- Delivered

Enable app notifications: App Settings → Notifications → Enable Notifications.
Configure notification email: sender address and SMTP settings if using custom email.

TRACKING PAGE:
Customers can track via auspost.com.au using the Article ID.
The app can embed tracking information in the Shopify order page.

RATES LOG:
View API request/response logs: Shipping → click order → More Actions → "View Logs"
""",
    },
    {
        "title": "Australia Post Shopify App — International Shipping",
        "section": "international",
        "content": """
International Shipping Configuration in the Australia Post Shopify App

SUPPORTED INTERNATIONAL SERVICES (via eParcel):
- International Economy
- International Standard (with tracking)
- International Express
- Pack & Track International
- Express Mail International (EMS)

CUSTOMS REQUIREMENTS:
All international shipments require:
- HS Tariff Code (set per product in Shopify → Products → Shipping tab)
- Country of Manufacture
- Declared value (minimum $1 AUD per product)

CUSTOMS DOCUMENTS GENERATED:
- Shipping label with customs declaration
- Commercial Invoice (if required)

DANGEROUS GOODS RESTRICTIONS:
Australia Post has strict dangerous goods restrictions for international shipments.
Lithium batteries: only allowed as per IATA regulations.
Aerosols, flammables: NOT accepted via Australia Post international.

PROHIBITED ITEMS:
Australia Post maintains a list of prohibited items for international mail.
Check auspost.com.au/parcels-mail/what-can-you-send for current restrictions.
""",
    },
    {
        "title": "Australia Post Shopify App — FAQ",
        "section": "faq",
        "content": """
Australia Post Shopify App — Complete FAQ

Q: What is the difference between eParcel and MyPost Business?
A: eParcel is Australia Post's business parcel service for higher-volume shippers
   with an established account number. It supports Extra Cover up to $5,000 AUD,
   dangerous goods, and full API integration.
   MyPost Business is suitable for smaller businesses. It supports Extra Cover up
   to $1,000 AUD and is simpler to set up. No dangerous goods support.

Q: How is cubic weight calculated?
A: Cubic weight = L(cm) × W(cm) × H(cm) ÷ 4000. Australia Post charges whichever
   is greater: actual weight or cubic weight.

Q: How do I add insurance to a shipment?
A: During label generation, in the SideDock, check "Extra Cover" and enter the
   declared value. Maximum: $5,000 AUD (eParcel) or $1,000 AUD (MyPost Business).

Q: Can I generate return labels?
A: Yes. From Order Summary → "Return packages" tab → "Return Packages".
   Or from Shopify order page → More Actions → "Generate Return Label".

Q: How do I cancel a label?
A: Shipping tab → Label Generated section → click order → More Actions → "Cancel Label".
   Note: some labels cannot be cancelled after lodgement.

Q: What order statuses support label generation?
A: Only "Unfulfilled" orders. Fulfilled, Draft, or Archived orders cannot have labels generated.

Q: How do I set Authority to Leave?
A: During label generation in the SideDock → check "Authority to Leave".
   Or set it per product in App Products settings.
   Note: ATL cannot be set alongside Signature on Delivery.

Q: How do I view the API request/response logs?
A: Shipping → click order in Label Generated list → More Actions → "View Logs".
   Shows the Australia Post API request and response JSON.

Q: What international services are supported?
A: Economy, Standard (tracked), Express, Pack & Track, and Express Mail International (EMS).
   All via eParcel account. MyPost Business is domestic only.

Q: How do I configure fallback rates if Australia Post API is down?
A: App Settings → Rate Settings → Fallback Services.
   Set flat-rate backups for Domestic and International.

Q: Does the app support dangerous goods?
A: Yes, via eParcel for domestic shipments. Not supported for MyPost Business
   or international shipments.

Q: How do customers track their parcels?
A: Via auspost.com.au with the Article ID (tracking number) on their label.
   Enable notifications in App Settings → Notifications to auto-email customers.
""",
    },
]


def load_pluginhive_app_docs() -> list[Document]:
    """
    Returns chunked Documents from the official PluginHive Australia Post app guides.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )

    all_docs: list[Document] = []

    for article in _ARTICLES:
        chunks = splitter.split_text(article["content"].strip())
        for i, chunk in enumerate(chunks):
            all_docs.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "source": "pluginhive_app_docs",
                        "source_url": _SOURCE_URL,
                        "type": "product_documentation",
                        "title": article["title"],
                        "section": article["section"],
                        "chunk_index": i,
                    },
                )
            )

    logger.info(
        "PluginHive AU Post app docs: %d articles → %d chunks", len(_ARTICLES), len(all_docs)
    )
    return all_docs
