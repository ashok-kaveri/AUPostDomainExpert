"""
Australia Post REST API Knowledge Ingest
=========================================
Embeds comprehensive, structured knowledge about the Australia Post Shipping API
into the RAG knowledge base.

Coverage:
  • Authentication (API key)
  • Postage / Rates API — how rate requests are built, request/response schema
  • Shipment / Label API — createShipment request structure, tracking numbers, label data
  • Special services — Signature on Delivery, Authority to Leave, Extra Cover, Safe Drop, Dangerous Goods
  • International shipping — PLT service, customs, international restrictions
  • Account types — eParcel vs MyPost Business differences
  • Service codes — T28 (Parcel Post), E86J (Express Post), PLT (International Economy)
  • Request/response JSON field paths — as used in the PluginHive AU Post Shopify App
  • Pickup API — schedule Australia Post pickup
  • Tracking API — article tracking events
  • Error handling — common errors and fixes
  • App-specific conventions (how the AU Post Shopify App uses the API)
"""
from __future__ import annotations

import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config

logger = logging.getLogger(__name__)

_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=config.CHUNK_SIZE,
    chunk_overlap=config.CHUNK_OVERLAP,
)

# ---------------------------------------------------------------------------
# Knowledge articles
# ---------------------------------------------------------------------------

_ARTICLES: list[dict] = [

    # ------------------------------------------------------------------
    {
        "title": "Australia Post API — Overview and Authentication",
        "content": """
Australia Post Shipping API — Overview and Authentication
=========================================================

The AU Post Shopify App uses the Australia Post eParcel REST API and MyPost Business API
for label generation, rate calculation, and tracking.

Base URL:
  Production: https://digitalapi.auspost.com.au

Authentication:
  All API calls require an API key passed as a request header.
  Header: Authorization: Basic <base64(api_key:api_password)>
  or: AP-Merchant-Credentials: <encoded credentials>
  The API key and password are configured in the app's Settings → Account section.

Two account types are supported:
  1. eParcel — business parcel service for higher-volume merchants
     • Domestic + international shipping
     • Extra Cover up to $5,000 AUD
     • Dangerous goods support (domestic only)
     • Services: Parcel Post (T28), Express Post (E86J), International (PLT)
  2. MyPost Business — for smaller-volume businesses
     • Domestic shipping only
     • Extra Cover up to $1,000 AUD
     • No dangerous goods support
     • Services: Standard, Express

Key endpoints:
  POST /shipping/v1/shipments          — Create shipment / generate label
  POST /postage/v2/rates               — Get shipping rates
  GET  /shipping/v1/shipments/{id}     — Get shipment details
  DELETE /shipping/v1/shipments/{id}   — Cancel label
  GET  /track/v2/summary               — Track parcels
  POST /shipping/v1/pickups            — Schedule pickup
""",
        "source_url": "https://developers.auspost.com.au/apis/shipping-and-tracking/reference",
        "source_type": "aupost_rest",
        "category": "Authentication",
    },

    # ------------------------------------------------------------------
    {
        "title": "Australia Post API — Create Shipment Request Structure",
        "content": """
Australia Post — createShipment Request JSON Structure
======================================================

The createShipment endpoint creates a label and returns a tracking number.
Endpoint: POST /shipping/v1/shipments

Full request body structure:
{
  "shipments": [
    {
      "from": {
        "name": "Sender Name",
        "lines": ["123 Sender Street"],
        "suburb": "SYDNEY",
        "state": "NSW",
        "postcode": "2000",   // 4-digit Australian postcode
        "country": "AU",
        "phone": "0400000000",
        "email": "sender@example.com"
      },
      "to": {
        "name": "Recipient Name",
        "lines": ["456 Recipient Street"],
        "suburb": "MELBOURNE",
        "state": "VIC",
        "postcode": "3000",   // 4-digit Australian postcode (domestic)
        "country": "AU",      // or e.g. "NZ", "US" for international
        "phone": "0411000000",
        "email": "recipient@example.com"
      },
      "items": [
        {
          "product_id": "T28",     // Service code: T28=Parcel Post, E86J=Express Post, PLT=Intl Economy
          "length": 20,            // cm
          "width": 15,             // cm
          "height": 10,            // cm
          "weight": 0.5,           // kg
          "cubic_weight": 0.75,    // AUTO: L*W*H/4000 (AU Post charges the higher of actual vs cubic)
          "description": "Product description"
        }
      ],
      "options": {
        "signature_on_delivery": false,    // true = recipient must sign
        "authority_to_leave": false,       // true = parcel left without signature (mutually exclusive with signature)
        "allow_partial_delivery": false,
        "extra_cover": {
          "amount": 0,     // declared value AUD (max 5000 for eParcel, 1000 for MyPost Business)
          "cover_on_return": false
        },
        "safe_drop_enabled": false,        // true = leave in safe location
        "contains_dangerous_goods": false  // eParcel domestic only
      }
    }
  ]
}

Response structure (success):
{
  "shipments": [
    {
      "shipment_id": "...",
      "order_id": "...",
      "shipment_summary": {
        "total_cost": 12.50,
        "tracking_summary": {
          "Delivered": 0,
          "In Transit": 0,
          "Pending": 1
        }
      },
      "items": [
        {
          "item_id": "...",
          "article_id": "ABC123456789",   // tracking number
          "product_id": "T28",
          "item_reference": "...",
          "tracking_details": {
            "article_id": "ABC123456789",
            "event_datetime": "...",
            "description": "Shipping label created"
          }
        }
      ],
      "labels": {
        "label": "<base64 encoded PDF>",
        "type": "PDF"
      }
    }
  ]
}
""",
        "source_url": "https://developers.auspost.com.au/apis/shipping-and-tracking/reference/create-shipment",
        "source_type": "aupost_rest",
        "category": "Label Generation",
    },

    # ------------------------------------------------------------------
    {
        "title": "Australia Post API — Service Codes and Product IDs",
        "content": """
Australia Post — Service Codes (product_id field)
=================================================

items[0].product_id determines the shipping service. Key codes:

DOMESTIC SERVICES (eParcel):
  T28   — Parcel Post (standard domestic)
           Typical transit: 2-6 business days
           Max weight: 22 kg per item
  E86J  — Express Post (priority domestic)
           Typical transit: next business day (capital cities)
           Max weight: 22 kg per item

INTERNATIONAL SERVICES (eParcel only):
  PLT   — International Economy (most countries)
           Registered post, tracking available
           Uses customs declaration / commercial invoice
  3J55  — International Express
           Faster delivery, tracking, signature
  OXI   — International Express Courier

MYPOST BUSINESS SERVICES:
  My Post Business uses different product codes managed by the account.
  Domestic only. Standard and Express options available.
  MyPost Business does NOT support international services.
  MyPost Business does NOT support dangerous goods.

CUBIC WEIGHT CALCULATION:
  AU Post charges the higher of actual weight vs cubic weight.
  cubic_weight (kg) = Length (cm) × Width (cm) × Height (cm) ÷ 4000
  If cubic_weight > actual_weight, AU Post uses cubic_weight for pricing.
  Example: 30cm × 20cm × 15cm = 9000 cm³ ÷ 4000 = 2.25 kg cubic weight

SERVICE SELECTION IN THE APP:
  Manual label: user clicks "Get Shipping Rates" then selects a radio button service
  Auto label: app automatically selects cheapest/configured service
  The app displays service name (e.g. "Parcel Post") but sends the code (e.g. "T28")
""",
        "source_url": "https://developers.auspost.com.au/apis/shipping-and-tracking",
        "source_type": "aupost_rest",
        "category": "Services",
    },

    # ------------------------------------------------------------------
    {
        "title": "Australia Post API — Special Services",
        "content": """
Australia Post — Special Services and How They Map to Request Fields
====================================================================

1. SIGNATURE ON DELIVERY
   Request field: options.signature_on_delivery = true
   Effect: Recipient must sign to receive the parcel.
   Cannot be combined with Authority to Leave (mutually exclusive).
   Available for both eParcel and MyPost Business domestic.
   SideDock checkbox in manual label generation.
   Product field on AU Post App Products page.

2. AUTHORITY TO LEAVE (ATL)
   Request field: options.authority_to_leave = true
   Effect: Postie leaves parcel without signature.
   Cannot be combined with Signature on Delivery (mutually exclusive).
   Available for both eParcel and MyPost Business domestic.
   SideDock checkbox in manual label generation.
   Product field on AU Post App Products page.

3. EXTRA COVER (Parcel Insurance)
   Request field: options.extra_cover.amount = <declared value AUD>
   Effect: Adds insurance cover up to the declared value.
   eParcel: maximum $5,000 AUD
   MyPost Business: maximum $1,000 AUD
   If declared value exceeds the maximum, the API will reject the request.
   SideDock checkbox + value input in manual label generation.
   Product field on AU Post App Products page.

4. SAFE DROP
   Request field: options.safe_drop_enabled = true
   Effect: Postie leaves parcel in a safe location nominated by recipient.
   Available for domestic services only.
   SideDock checkbox in manual label generation.
   Product field on AU Post App Products page.

5. DANGEROUS GOODS
   Request field: options.contains_dangerous_goods = true
   Effect: Parcel contains declared dangerous goods.
   eParcel DOMESTIC ONLY — not available for international.
   NOT available for MyPost Business.
   SideDock checkbox in manual label generation.
   Product field on AU Post App Products page.
   Requires special handling by Australia Post.

MUTUALLY EXCLUSIVE RULES:
  - Signature on Delivery AND Authority to Leave CANNOT both be true.
  - If both are checked, the app should show a validation error.
  - In request JSON, only one of these should be true at a time.

SPECIAL SERVICES IN JSON VERIFICATION:
  When verifying via Download Documents:
  - options.signature_on_delivery: true   → Signature is on
  - options.authority_to_leave: true      → ATL is on
  - options.extra_cover.amount: 500       → Extra cover $500 AUD declared
  - options.contains_dangerous_goods: true → DG is on
  - options.safe_drop_enabled: true       → Safe drop is on
""",
        "source_url": "https://developers.auspost.com.au/apis/shipping-and-tracking/reference",
        "source_type": "aupost_rest",
        "category": "Special Services",
    },

    # ------------------------------------------------------------------
    {
        "title": "Australia Post API — Rate Request and Response",
        "content": """
Australia Post — Rate (Postage) API Request and Response
========================================================

Endpoint: POST /postage/v2/rates/domestic (or /international)
Used to get shipping rates before label generation.
The app uses this during "Get Shipping Rates" step in manual label flow.

Domestic rate request body:
{
  "from_postcode": "2000",     // 4-digit AU postcode
  "to_postcode": "3000",       // 4-digit AU postcode
  "length": 20,                // cm
  "width": 15,                 // cm
  "height": 10,                // cm
  "weight": 0.5,               // kg
  "service_code": ""           // blank = get all available services
}

Rate response:
{
  "services": {
    "service": [
      {
        "code": "T28",
        "name": "Parcel Post",
        "price": "9.85",
        "max_extra_cover": 5000,
        "options": {
          "option": [
            {"code": "SIGNAT", "name": "Signature on Delivery"},
            {"code": "EXCOVER", "name": "Extra Cover"}
          ]
        }
      },
      {
        "code": "E86J",
        "name": "Express Post",
        "price": "12.95",
        "max_extra_cover": 5000
      }
    ]
  }
}

RATE LOG IN THE APP:
  After "Get Shipping Rates" → click the ⋯ (three dots) menu → "View Logs"
  A dialog shows the rate request JSON (left) and response JSON (right) IN THE PAGE.
  This is NOT a downloadable ZIP — the JSON is visible directly in the dialog.
  Rate logs are also saved in the app's Rates Log page (app sidebar → Rates Log).

CUBIC WEIGHT AND PRICING:
  AU Post charges the higher of actual weight vs cubic weight.
  The app automatically calculates cubic weight and sends the higher value.
  cubic_weight = L × W × H ÷ 4000 (all in cm, result in kg)
""",
        "source_url": "https://developers.auspost.com.au/apis/shipping-and-tracking/reference/rates",
        "source_type": "aupost_rest",
        "category": "Rates",
    },

    # ------------------------------------------------------------------
    {
        "title": "Australia Post API — International Shipping",
        "content": """
Australia Post — International Shipping (eParcel only)
======================================================

International shipping is ONLY available for eParcel accounts.
MyPost Business does NOT support international shipping.

International services:
  PLT  — International Economy (most destinations)
  3J55 — International Express
  OXI  — International Express Courier

Request differences for international:
  - to.country must be a valid 2-letter ISO country code (e.g. "NZ", "US", "GB")
  - to.postcode format varies by country
  - items must include product_id = "PLT" (or other international code)
  - Customs/commercial invoice data may be required for some destinations

International restrictions:
  - Dangerous goods are NOT allowed internationally
  - Extra Cover limits may differ by destination country
  - Some destinations have prohibited items (check AU Post dangerous goods list)
  - Weight and dimension limits vary by service and destination

INTERNATIONAL LABEL VERIFICATION:
  - items[0].product_id should be "PLT" for International Economy
  - to.country should match the order destination country code
  - The label PDF will include customs declaration information
  - For commercial invoice documents, use Download Documents from Order Summary

NEW ZEALAND SHIPPING:
  New Zealand is a common international destination.
  Uses PLT service code.
  to.country = "NZ"
  Standard AU Post international tracking applies.
""",
        "source_url": "https://developers.auspost.com.au/apis/shipping-and-tracking/reference/international",
        "source_type": "aupost_rest",
        "category": "International",
    },

    # ------------------------------------------------------------------
    {
        "title": "Australia Post API — Tracking",
        "content": """
Australia Post — Tracking API
=============================

Endpoint: GET /track/v2/summary?q={article_ids}
Used to get tracking status for one or more articles (parcels).

Article ID (tracking number) is returned in the createShipment response:
  response.shipments[0].items[0].article_id   → the tracking number
  response.shipments[0].items[0].tracking_details.article_id → same value

Tracking request:
  GET /track/v2/summary?q=ABC123456789,DEF987654321

Tracking response:
{
  "tracking_results": [
    {
      "tracking_id": "ABC123456789",
      "status": "Delivered",
      "trackable_items": [
        {
          "article_id": "ABC123456789",
          "product": "Parcel Post",
          "events": [
            {
              "location": "SYDNEY NSW",
              "description": "Delivered",
              "date": "2024-01-15",
              "time": "14:30:00"
            }
          ]
        }
      ]
    }
  ]
}

TRACKING IN THE AU POST SHOPIFY APP:
  The app automatically fetches tracking status and displays in the Shipping grid:
  - Order row shows current tracking status
  - Clicking an order shows full tracking history on Order Summary page
  - Tracking is triggered automatically after label generation

TRACKING STATUS VALUES:
  "Delivered"       → parcel delivered to recipient
  "In Transit"      → parcel in AU Post network
  "Pending"         → label created, not yet scanned
  "Attempted"       → delivery attempted, card left
  "Held by AU Post" → held at post office for pickup
""",
        "source_url": "https://developers.auspost.com.au/apis/shipping-and-tracking/reference/track",
        "source_type": "aupost_rest",
        "category": "Tracking",
    },

    # ------------------------------------------------------------------
    {
        "title": "Australia Post API — Cancel Label",
        "content": """
Australia Post — Cancel Label / Delete Shipment
===============================================

Endpoint: DELETE /shipping/v1/shipments/{shipment_id}
Used to cancel a generated label before it is lodged with AU Post.

Request:
  DELETE /shipping/v1/shipments/{shipment_id}
  Authorization: Basic <credentials>

Response (success):
  HTTP 200 OK
  {}  (empty body)

Response (error):
  HTTP 400 or 404
  {"errors": [{"code": "...", "message": "..."}]}

CANCEL LABEL IN THE APP:
  Order Summary → More Actions dropdown → "Cancel Label"
  After cancellation, the label status changes to "label cancelled" in the grid.
  After cancellation, a new label can be generated for the same order.
  Cannot cancel a label that has already been lodged/scanned by AU Post.

CANCEL LABEL CONDITIONS:
  - Can only cancel if the label has not been scanned by AU Post
  - Once a parcel is in transit, cancellation must be done directly with AU Post
  - The app will show an error if cancellation is not possible
""",
        "source_url": "https://developers.auspost.com.au/apis/shipping-and-tracking/reference/cancel-shipment",
        "source_type": "aupost_rest",
        "category": "Label Management",
    },

    # ------------------------------------------------------------------
    {
        "title": "Australia Post API — Return Labels",
        "content": """
Australia Post — Return Labels
==============================

Return labels allow customers to send items back to the merchant.
Return labels use the same createShipment API with from/to reversed.

Return label generation in the AU Post Shopify App — TWO WAYS:

WAY A — From Order Summary (recommended):
  1. Open Order Summary (click order in Shipping grid)
  2. Click "Return packages" tab (second tab on Order Summary)
  3. Click "Return Packages" button
  4. Enter return quantity
  5. Click "Refresh Rates" to get available return services
  6. Select a service radio button
  7. Click "Generate Return Label"
  Verify: "SUCCESS" badge appears + "Download Label" link is visible

WAY B — From Shopify admin order:
  1. Shopify Orders → click an order
  2. Click "More Actions" dropdown
  3. Click "Generate Return Label" (NOT "Create return label" — that is Shopify-native)
  The app handles return label creation via its own flow.

Return label request differences:
  - from address = original delivery address (customer)
  - to address = merchant/warehouse address
  - Same product_id/service codes apply
  - Return tracking number is separate from the original shipment tracking number

RETURN LABEL VERIFICATION:
  After generating a return label:
  - Status shows "SUCCESS" badge on the Return packages tab
  - "Download Label" link appears to download the return label PDF
  - Return label has its own article_id (tracking number)
  - Original order label remains unchanged
""",
        "source_url": "https://developers.auspost.com.au/apis/shipping-and-tracking/reference/returns",
        "source_type": "aupost_rest",
        "category": "Return Labels",
    },

    # ------------------------------------------------------------------
    {
        "title": "Australia Post API — Pickup Scheduling",
        "content": """
Australia Post — Pickup Scheduling API
=======================================

The pickup feature lets merchants schedule AU Post to collect parcels.
Accessible from the app's PickUp page (app sidebar → PickUp).

Pickup endpoint: POST /shipping/v1/pickups

Pickup request:
{
  "pickup": {
    "pickup_date": "2024-01-15",      // ISO date YYYY-MM-DD
    "start_time": "09:00:00",          // pickup window start
    "end_time": "17:00:00",            // pickup window end
    "location": "Front Door",
    "comments": "Leave with reception if not home",
    "contact": {
      "name": "Contact Name",
      "phone": "0400000000"
    },
    "shipments": [
      {"shipment_id": "..."}           // shipments to be collected
    ]
  }
}

PICKUP IN THE APP:
  App sidebar → PickUp
  Shows scheduled and completed pickups
  "Schedule Pickup" button → date/time selection → confirm
  Pickup can only be scheduled for future dates
  Minimum notice period applies (typically same-day if before cutoff time)

PICKUP RESTRICTIONS:
  - Available for eParcel and MyPost Business
  - Residential and business addresses supported
  - Some remote areas may not support pickup (check coverage)
  - Pickup confirmation number is returned on success
""",
        "source_url": "https://developers.auspost.com.au/apis/shipping-and-tracking/reference/pickup",
        "source_type": "aupost_rest",
        "category": "Pickup",
    },

    # ------------------------------------------------------------------
    {
        "title": "Australia Post API — JSON Field Paths for Verification",
        "content": """
Australia Post — JSON Field Paths for QA Verification
======================================================

When verifying createShipment request JSON (from Download Documents ZIP):

PACKAGE-LEVEL FIELDS:
  items[0].product_id          → service code
    "T28"  = Parcel Post (domestic standard)
    "E86J" = Express Post (domestic express)
    "PLT"  = International Economy
  items[0].length              → package length in cm
  items[0].width               → package width in cm
  items[0].height              → package height in cm
  items[0].weight              → package actual weight in kg
  items[0].cubic_weight        → calculated cubic weight (L*W*H/4000)

SHIPMENT OPTIONS:
  options.signature_on_delivery          → true/false
  options.authority_to_leave             → true/false
  options.extra_cover.amount             → declared value in AUD (number)
  options.extra_cover.cover_on_return    → true/false
  options.safe_drop_enabled              → true/false
  options.contains_dangerous_goods       → true/false (eParcel domestic only)

SENDER/RECEIVER:
  from.postcode                → sender postcode (4 digits, Australian)
  from.state                   → sender state (e.g. "NSW", "VIC")
  to.postcode                  → receiver postcode (4 digits domestic, varies international)
  to.country                   → "AU" for domestic, ISO code for international

RESPONSE FIELDS:
  shipments[0].items[0].article_id          → tracking number (Article ID)
  shipments[0].shipment_summary.total_cost  → shipping cost charged
  shipments[0].labels.label                 → base64 encoded PDF

CUBIC WEIGHT FORMULA:
  cubic_weight_kg = length_cm × width_cm × height_cm ÷ 4000
  AU Post charges the higher of actual weight vs cubic weight.
  Example: 30×20×10 cm, 0.3 kg actual → cubic = 1.5 kg → AU Post charges 1.5 kg rate

ZIP FILE CONTENTS (Download Documents):
  The ZIP downloaded from Order Summary → More Actions → Download Documents contains:
  1. label.pdf              → the shipping label PDF
  2. request.json           → the createShipment API request body
  3. response.json          → the createShipment API response body
  Use request.json to verify fields sent to AU Post.
  Use response.json to verify article_id (tracking number) and cost.
""",
        "source_url": "https://developers.auspost.com.au/apis/shipping-and-tracking",
        "source_type": "aupost_rest",
        "category": "Verification",
    },

    # ------------------------------------------------------------------
    {
        "title": "Australia Post API — Common Errors and Fixes",
        "content": """
Australia Post — Common API Errors and How to Fix Them
======================================================

HTTP 400 — Bad Request:
  Cause: Invalid request body, missing required fields, or constraint violation.
  Common specific errors:
  - "Invalid postcode" → postcode must be exactly 4 digits (Australian format)
  - "Weight exceeds maximum" → parcel weight > 22 kg limit
  - "Dimensions exceed maximum" → check max L+W+H girth for the service
  - "Extra cover amount exceeds maximum" → eParcel max $5,000, MyPost max $1,000
  - "Signature and authority to leave cannot both be true" → mutually exclusive options
  - "Dangerous goods not permitted" → DG not allowed for international or MyPost Business

HTTP 401 — Unauthorized:
  Cause: Invalid or expired API credentials.
  Fix: Check API key and password in Settings → Account. Regenerate if necessary.

HTTP 403 — Forbidden:
  Cause: Account not permitted for this service or feature.
  Common: Trying to use eParcel features with a MyPost Business account.
  Fix: Verify account type in Settings. International shipping requires eParcel.

HTTP 404 — Not Found:
  Cause: Shipment ID not found (for cancel or get shipment operations).
  Fix: Check the shipment ID is correct and was created with the same account.

HTTP 429 — Rate Limited:
  Cause: Too many API requests in a short period.
  Fix: Add delays between bulk operations. AU Post has per-minute rate limits.

HTTP 500 — Internal Server Error:
  Cause: AU Post API server error (rare).
  Fix: Retry after a short delay. If persistent, check AU Post API status page.

LABEL STATUS ERRORS IN THE APP:
  "failed"        → API returned an error; check the error message in the order row
  "inprogress"    → label generation pending (should resolve in seconds)
  "auto cancelled" → label was cancelled automatically (e.g. order cancelled in Shopify)

VALIDATION IN THE APP:
  The app validates inputs before sending to AU Post:
  - Extra Cover amount must be a positive number within the account limit
  - Signature and ATL cannot both be selected
  - Dangerous goods only available for eParcel domestic
  - Product dimensions must be positive numbers (cm)
  - Product weight must be a positive number (kg)
""",
        "source_url": "https://developers.auspost.com.au/apis/shipping-and-tracking/reference",
        "source_type": "aupost_rest",
        "category": "Error Handling",
    },

    # ------------------------------------------------------------------
    {
        "title": "AU Post Shopify App — App UI Navigation Guide",
        "content": """
AU Post Shopify App — UI Navigation and Architecture
====================================================

IFRAME STRUCTURE:
  The AU Post app is embedded inside Shopify admin as an iframe.
  iframe selector: iframe[name="app-iframe"]
  App content (sidebar, pages) is INSIDE the iframe.
  Shopify admin content (Orders, left nav) is OUTSIDE the iframe.

APP SIDEBAR (inside iframe):
  Shipping   → app/shopify       — All Orders grid
  PickUp     → app/pickup        — Schedule Australia Post pickup
  Products   → app/products      — Configure product dimensions and special services
  Settings   → app/settings      — Account, services, packages settings
  FAQ        → app/faq           — Help articles
  Rates Log  → app/rateslog      — Historical rate request log

SHOPIFY ADMIN SIDEBAR (outside iframe, left panel):
  Orders     → Shopify orders list (click order → More Actions → Generate Label)
  Products   → Shopify product catalog (add/edit products)

ALL ORDERS GRID (app Shipping page):
  Columns: Order#, Label Date, Customer, Label Status, Shipping Service,
           Subtotal, Shipping Cost, Packages, Products, Weight, Messages
  Tab filters: All | Pending | Label Generated
  Status colors: "label generated" (green), "inprogress" (yellow),
                 "failed" (red), "auto cancelled" (grey), "label cancelled"
  Click a row → opens Order Summary page for that order

ORDER SUMMARY PAGE:
  Buttons: Print Documents | Upload Documents | More Actions ▼
  More Actions dropdown:
    • Download Documents → ZIP with label PDF + request/response JSON
    • Cancel Label
    • Return Label
    • How To → modal with download link
  Two tabs: Packages | Return packages
  Back arrow "← #XXXX" → returns to Shipping grid

MANUAL LABEL GENERATION FLOW:
  Shopify Orders → click order → More Actions → Generate Label
  Opens app in iframe with:
    LEFT panel:
      a. Generate Packages button
      b. Get Shipping Rates button
      c. Select service radio button
      d. Generate Label button
    RIGHT panel (SideDock — ALWAYS VISIBLE):
      ☐ Signature on Delivery
      ☐ Authority to Leave (ATL)
      ☐ Extra Cover + declared value input
      ☐ Safe Drop
      ☐ Dangerous Goods (eParcel domestic only)
  After generation → redirects to Order Summary

RATE LOG (in-page view):
  Manual label → after "Get Shipping Rates" → click ⋯ → "View Logs"
  Dialog shows JSON request (left) and response (right) directly in the page.
  NOT a download — JSON is visible in the dialog.

LABEL LOG (ZIP download):
  Order Summary → More Actions → Download Documents
  Downloads ZIP containing: label.pdf + request.json + response.json
""",
        "source_url": "https://www.pluginhive.com/knowledge-base/australia-post-eparcel-label-printing-in-shopify/",
        "source_type": "aupost_rest",
        "category": "App UI",
    },

]


# ---------------------------------------------------------------------------
# Ingest function
# ---------------------------------------------------------------------------

def load_aupost_api_docs() -> list[Document]:
    """
    Return a list of LangChain Documents containing Australia Post API knowledge.
    Each article is chunked using the configured splitter.
    """
    docs: list[Document] = []
    for article in _ARTICLES:
        raw_text = f"# {article['title']}\n\n{article['content'].strip()}"
        metadata = {
            "source": article.get("source_url", "aupost_api"),
            "source_url": article.get("source_url", ""),
            "source_type": article.get("source_type", "aupost_rest"),
            "category": article.get("category", ""),
            "title": article["title"],
        }
        chunks = _SPLITTER.create_documents([raw_text], metadatas=[metadata])
        docs.extend(chunks)
    logger.info("aupost_api: loaded %d chunks from %d articles", len(docs), len(_ARTICLES))
    return docs
