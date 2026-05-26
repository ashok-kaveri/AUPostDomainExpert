---
name: aupost-shopify-store-actions
description: Use when the user wants to perform any Shopify Admin API action on any store — create/update/archive/delete products (simple, variable, large variant counts), create/cancel/delete/update orders (preset, custom, draft), bulk cleanup by tag, update shipping address, manage customers, update inventory (set or adjust), list fulfillments, carrier services, webhooks, metafields, collections, locations, create refunds — all via natural language. If the store is in the automation .env or env_sample the token is used automatically; otherwise asks the user for a token.
---

# Shopify Store Actions

Use this skill when the user asks to do anything with the Shopify test store via API:

- "create 3 products" / "create a variable product with 5 sizes × 5 colors × 5 fabrics"
- "list all products and give me the IDs"
- "delete the product called Red Shirt"
- "archive that product" / "set product status to draft"
- "update variant weight to 2.5kg"
- "create a domestic order" / "create an order for John Smith at 123 Main St NY"
- "create a draft order and complete it"
- "cancel order #1801" / "delete all qa-test tagged orders"
- "update the shipping address on order #1802"
- "list all unfulfilled orders" / "how many open orders are there?"
- "this product has 0 quantity, set it to 9999" / "add 50 stock to Red Shirt"
- "check if AU Post app is registered as a carrier"
- "show fulfillments for order #1800"
- "list webhooks" / "get metafields on this product"
- "create a customer called Jane Doe" / "find customer by email"
- "list all locations" / "list collections"
- "create a refund on order #1799"
- any CRUD or management action on Shopify Products, Orders, Customers, Inventory, or Store config

---

## Store & Auth Resolution

### Logic (simple — 3 checks in order)

```
1. No store mentioned by user
   → use STORE + SHOPIFY_ACCESS_TOKEN directly from automation .env
   → no questions asked

2. User mentions a store name
   → normalize it (strip .myshopify.com, lowercase, trim spaces)
   → check if it matches STORE in automation .env or env_sample
       match  → use the token from that file
       no match → STOP and say: "I need an access token for store X"

3. User provides an explicit token along with the store name
   → use exactly what they gave, skip env lookup
```

---

### Implementation

```python
import config, requests
from pathlib import Path

def _read_env_file(path: Path) -> dict:
    env = {}
    if path and path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip("'\"")
    return env

# Load automation .env (primary)
_automation_path = (config.AUTOMATION_CODEBASE_PATH or "").strip()
_automation_env  = _read_env_file(Path(_automation_path) / ".env") if _automation_path else {}

# Load shopify-actions env_sample (secondary fallback)
# NOTE: SHOPIFY_ACTIONS_PATH has a trailing space — do NOT strip it
_actions_path = config.SHOPIFY_ACTIONS_PATH  # e.g. "/Users/madan/Documents/shopify-actions "
_actions_env  = _read_env_file(Path(_actions_path) / "env_sample") if _actions_path else {}

def resolve_store(user_store: str = "", user_token: str = "") -> tuple[str, str, str]:
    """
    Returns (STORE, ACCESS_TOKEN, API_VERSION) or raises with a clear message.
    """
    api_version = (
        _automation_env.get("SHOPIFY_API_VERSION")
        or _actions_env.get("SHOPIFY_API_VERSION")
        or "2024-01"
    )

    # Case 1 — user gave explicit token
    if user_token:
        store = _normalize(user_store or _automation_env.get("STORE", ""))
        return store, user_token, api_version

    # Case 2 — no store mentioned → use automation .env directly
    if not user_store:
        store = _automation_env.get("STORE", "").strip()
        token = _automation_env.get("SHOPIFY_ACCESS_TOKEN", "").strip()
        if not store or not token:
            raise ValueError("STORE or SHOPIFY_ACCESS_TOKEN missing in automation .env")
        return store, token, api_version

    # Case 3 — user named a store → check env files
    user_store_norm = _normalize(user_store)

    for env_dict, source in [
        (_automation_env, "automation .env"),
        (_actions_env,    "shopify-actions env_sample"),
    ]:
        env_store = _normalize(env_dict.get("STORE", "") or env_dict.get("SHOPIFY_STORE_NAME", ""))
        env_token = env_dict.get("SHOPIFY_ACCESS_TOKEN", "").strip()

        if env_store and env_token and user_store_norm == env_store:
            print(f"Store '{user_store}' found in {source} — using its token.")
            return env_store, env_token, api_version

    raise ValueError(
        f"Store '{user_store}' is not in the automation .env or env_sample.\n"
        f"I need an access token for this store.\n"
        f"Please provide it: \"use store {user_store} with token shpat_xxx\""
    )

def _normalize(name: str) -> str:
    return name.lower().strip().replace(".myshopify.com", "")
```

**Usage in every action:**
```python
try:
    STORE, ACCESS_TOKEN, API_VERSION = resolve_store(
        user_store="",   # from user message, or "" if not mentioned
        user_token="",   # from user message, or "" if not provided
    )
except ValueError as e:
    print(e)
    # STOP — do not proceed without a valid token

BASE_URL = f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}"
HEADERS  = {"X-Shopify-Access-Token": ACCESS_TOKEN, "Content-Type": "application/json"}
```

---

### Connection check — always run before the first API call

```python
resp = requests.get(f"{BASE_URL}/shop.json", headers=HEADERS)

if resp.status_code == 200:
    shop = resp.json()["shop"]
    print(f"Connected: {shop['name']} ({shop['myshopify_domain']})")

elif resp.status_code == 401:
    print(f"Token rejected on '{STORE}'.")
    print(f"The app may not be installed on this store, or the token may have been revoked.")
    print(f"Provide a valid token: \"use store {STORE} with token shpat_xxx\"")
    # STOP

elif resp.status_code == 404:
    print(f"Store '{STORE}' not found — check the store name.")
    # STOP
```

---

## API Actions

### 1. List Products

```python
resp = requests.get(f"{BASE_URL}/products.json", headers=HEADERS, params={"limit": 250})
products = resp.json().get("products", [])
# Return: id, title, status, variants[].id, variants[].price for each
```

### 2. Create Product

```python
payload = {
    "product": {
        "title": "Test Product",
        "body_html": "<p>Test product for AU Post QA</p>",
        "vendor": STORE,
        "product_type": "Test",
        "status": "active",
        "published_scope": "global",
        "variants": [{
            "price": "10.00",
            "sku": "TEST-001",
            "weight": 1.5,
            "weight_unit": "kg",
            "grams": 1500,
            "requires_shipping": True,
            "inventory_management": None,
        }]
    }
}
resp = requests.post(f"{BASE_URL}/products.json", headers=HEADERS, json=payload)
product = resp.json().get("product", {})
# Return: product id, variant id, title
```

For **dangerous goods** products (eParcel only) set appropriate title/type so the AU Post app can detect them.

### 3. List Orders

```python
params = {"limit": 50, "status": "any"}
resp = requests.get(f"{BASE_URL}/orders.json", headers=HEADERS, params=params)
orders = resp.json().get("orders", [])
# Return: id, name (#1234), fulfillment_status, financial_status, created_at, line_items[].title
```

### 4. Create Order

Use `order_creator.py` from the project — it already handles all product types and address types:

```python
import sys
sys.path.insert(0, "/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert")
import config
from pipeline.order_creator import create_order

# product_type: "simple" | "variable" | "digital" | "dangerous"
# address_type: "default" (AU) | "UK" | "CA" | "US"
order = create_order(product_type="simple", address_type="default")
# Returns: {"order_id": ..., "order_name": "#1234", "order_url": "..."}
```

Keyword → product/address mapping:

| User says | product_type | address_type |
|-----------|-------------|--------------|
| dangerous goods / dry ice | dangerous | default |
| UK / international UK | simple | UK |
| Canada / CA | simple | CA |
| domestic / AU / default | simple | default |
| variable / configurable | variable | default |
| digital / virtual | digital | default |

### 5. Get a Single Product or Order

```python
# Product by ID
resp = requests.get(f"{BASE_URL}/products/{product_id}.json", headers=HEADERS)

# Order by ID
resp = requests.get(f"{BASE_URL}/orders/{order_id}.json", headers=HEADERS)
```

### 6. Delete Product by Name

```python
# Step 1 — find by title (case-insensitive substring match)
resp = requests.get(f"{BASE_URL}/products.json", headers=HEADERS, params={"title": product_name, "limit": 10})
matches = resp.json().get("products", [])

if len(matches) == 0:
    print(f"No product found with name '{product_name}'")
elif len(matches) > 1:
    print(f"Found {len(matches)} products matching '{product_name}':")
    for p in matches:
        print(f"  - ID {p['id']} | {p['title']} | {p['status']}")
    print("Please confirm which one to delete (by ID).")
else:
    product = matches[0]
    resp = requests.delete(f"{BASE_URL}/products/{product['id']}.json", headers=HEADERS)
    if resp.status_code == 200:
        print(f"Deleted: '{product['title']}' (ID {product['id']})")
```

### 7. Create Variable Product

```python
import itertools

sizes  = ["S", "M", "L", "XL"]
colors = ["Red", "Blue"]

variants = [
    {
        "option1": size, "option2": color,
        "price": "15.00",
        "sku": f"{size}-{color[:3].upper()}",
        "grams": 400,
        "weight": 0.4,
        "weight_unit": "kg",
        "requires_shipping": True,
        "inventory_management": "shopify",
        "inventory_quantity": 10,
    }
    for size, color in itertools.product(sizes, colors)
]

payload = {
    "product": {
        "title": "AU Post Test T-Shirt",
        "vendor": STORE,
        "status": "active",
        "published_scope": "global",
        "options": [
            {"name": "Size",  "values": sizes},
            {"name": "Color", "values": colors},
        ],
        "variants": variants,
    }
}
resp = requests.post(f"{BASE_URL}/products.json", headers=HEADERS, json=payload)
```

**Large variant counts** (no hard cap — generate with `itertools.product`):
- Strategy A: single axis — "N variants" → `Variant: 1, 2, ... N`
- Strategy B: 2 axes — "5 sizes × 5 colors" = 25 variants
- Strategy C: 3 axes — "5 sizes × 5 colors × 5 fabrics" = 125 variants (Shopify max is 3 axes)

### 8. Create Custom Order

```python
address = {
    "first_name": "John", "last_name": "Smith",
    "address1": "123 Main St", "city": "Sydney",
    "province": "New South Wales", "province_code": "NSW",
    "zip": "2000", "country": "Australia", "country_code": "AU",
    "phone": "+61412345678"
}

payload = {
    "order": {
        "email": "john.smith@test.com",
        "financial_status": "paid",
        "customer": {"first_name": "John", "last_name": "Smith", "email": "john.smith@test.com"},
        "billing_address": address,
        "shipping_address": address,
        "line_items": [{"variant_id": variant_id, "quantity": 1}],
        "send_receipt": False,
        "send_fulfillment_receipt": False,
    }
}
resp = requests.post(f"{BASE_URL}/orders.json", headers=HEADERS, json=payload)
```

Default AU address: Sydney, NSW 2000, Australia. Use UK/CA addresses when user says international.

### 9. Update Inventory Quantity

```python
# Step 1 — find variant's inventory_item_id
resp = requests.get(f"{BASE_URL}/products.json", headers=HEADERS, params={"title": product_name, "limit": 5})
variant = resp.json()["products"][0]["variants"][0]
inventory_item_id = variant["inventory_item_id"]

# Step 2 — find location
resp = requests.get(f"{BASE_URL}/inventory_levels.json", headers=HEADERS,
                    params={"inventory_item_ids": inventory_item_id})
levels = resp.json().get("inventory_levels", [])
location_id = levels[0]["location_id"] if levels else None
if not location_id:
    location_id = requests.get(f"{BASE_URL}/locations.json", headers=HEADERS).json()["locations"][0]["id"]

# Step 3 — set quantity
payload = {"location_id": location_id, "inventory_item_id": inventory_item_id, "available": 9999}
resp = requests.post(f"{BASE_URL}/inventory_levels/set.json", headers=HEADERS, json=payload)
```

### 10. Cancel an Order

```python
resp = requests.post(
    f"{BASE_URL}/orders/{order_id}/cancel.json",
    headers=HEADERS,
    json={"reason": "other", "email": False}
)
```

### 11. Delete a Test Order

```python
resp = requests.delete(f"{BASE_URL}/orders/{order_id}.json", headers=HEADERS)
```

### 12. Update Order Shipping Address

```python
payload = {
    "order": {
        "shipping_address": {
            "first_name": "Jane", "last_name": "Doe",
            "address1": "456 Collins St", "city": "Melbourne",
            "province": "Victoria", "province_code": "VIC",
            "zip": "3000", "country": "Australia", "country_code": "AU"
        }
    }
}
resp = requests.put(f"{BASE_URL}/orders/{order_id}.json", headers=HEADERS, json=payload)
```

### 13. Bulk Cancel / Delete Orders by Tag

```python
resp = requests.get(f"{BASE_URL}/orders.json", headers=HEADERS,
                    params={"tag": "qa-test", "status": "any", "limit": 250})
orders = resp.json().get("orders", [])

for o in orders:
    oid = o["id"]
    if not o.get("cancelled_at"):
        requests.post(f"{BASE_URL}/orders/{oid}/cancel.json", headers=HEADERS, json={"email": False})
    requests.delete(f"{BASE_URL}/orders/{oid}.json", headers=HEADERS)
    print(f"  Cleaned up order {o['name']} (ID {oid})")
```

**Add `qa-test` tag when creating orders:**
```python
payload["order"]["tags"] = "qa-test"
```

### 14. Archive / Draft a Product

```python
# Archive
resp = requests.put(f"{BASE_URL}/products/{product_id}.json", headers=HEADERS,
                    json={"product": {"status": "archived"}})
# Draft
resp = requests.put(f"{BASE_URL}/products/{product_id}.json", headers=HEADERS,
                    json={"product": {"status": "draft"}})
# Active
resp = requests.put(f"{BASE_URL}/products/{product_id}.json", headers=HEADERS,
                    json={"product": {"status": "active"}})
```

### 15. Update Product Variant (price, weight, SKU)

```python
payload = {"variant": {"price": "25.00", "weight": 2.5, "weight_unit": "kg", "grams": 2500}}
resp = requests.put(f"{BASE_URL}/variants/{variant_id}.json", headers=HEADERS, json=payload)
```

### 16. List Carrier Services

Confirms PluginHive AU Post app is registered as a carrier on the store:

```python
resp = requests.get(f"{BASE_URL}/carrier_services.json", headers=HEADERS)
carriers = resp.json().get("carrier_services", [])
for c in carriers:
    print(f"  - {c['name']} | active: {c['active']} | callback: {c['callback_url']}")
```

Expected: you should see a PluginHive / Australia Post entry with an active callback URL.

### 17. List Fulfillments for an Order

```python
resp = requests.get(f"{BASE_URL}/orders/{order_id}/fulfillments.json", headers=HEADERS)
for f in resp.json().get("fulfillments", []):
    print(f"  Tracking: {f.get('tracking_number')} via {f.get('tracking_company')}")
    print(f"  Service:  {f.get('service')}")
```

### 18. Create Draft Order → Complete It

```python
# Step 1 — create draft
payload = {
    "draft_order": {
        "line_items": [{"variant_id": variant_id, "quantity": 1}],
        "customer": {"first_name": "QA", "last_name": "Test", "email": "qa.draft@pluginhive.com"},
        "shipping_address": {
            "first_name": "QA", "last_name": "Test",
            "address1": "123 Main St", "city": "Sydney",
            "province": "New South Wales", "province_code": "NSW",
            "zip": "2000", "country": "Australia", "country_code": "AU"
        },
        "tags": "qa-draft",
    }
}
resp = requests.post(f"{BASE_URL}/draft_orders.json", headers=HEADERS, json=payload)
draft_id = resp.json()["draft_order"]["id"]

# Step 2 — complete it
resp = requests.put(
    f"{BASE_URL}/draft_orders/{draft_id}/complete.json",
    headers=HEADERS,
    params={"payment_pending": False}
)
print(f"Completed → real order ID: {resp.json()['draft_order'].get('order_id')}")
```

### 19. Get Order Count

```python
for status in ["open", "closed", "cancelled", "any"]:
    resp = requests.get(f"{BASE_URL}/orders/count.json", headers=HEADERS, params={"status": status})
    print(f"  {status}: {resp.json().get('count', 0)} orders")
```

### 20. List Webhooks

```python
resp = requests.get(f"{BASE_URL}/webhooks.json", headers=HEADERS)
for w in resp.json().get("webhooks", []):
    print(f"  [{w['id']}] {w['topic']:40s} → {w['address']}")
```

### 21. Get Metafields on a Product or Order

```python
resp = requests.get(f"{BASE_URL}/orders/{order_id}/metafields.json", headers=HEADERS)
for m in resp.json().get("metafields", []):
    print(f"  {m['namespace']}.{m['key']}: {m['value']}")
```

### 22. Create Customer

```python
payload = {
    "customer": {
        "first_name": "QA", "last_name": "Tester",
        "email": "qa.tester@pluginhive.com",
        "verified_email": True,
        "addresses": [{
            "address1": "123 Main St", "city": "Sydney",
            "province": "New South Wales", "province_code": "NSW",
            "zip": "2000", "country": "Australia", "country_code": "AU",
            "default": True
        }],
        "tags": "qa-customer"
    }
}
resp = requests.post(f"{BASE_URL}/customers.json", headers=HEADERS, json=payload)
```

### 23. Adjust Inventory (relative ±delta)

```python
payload = {
    "location_id": location_id,
    "inventory_item_id": inventory_item_id,
    "available_adjustment": +50  # positive = add, negative = remove
}
resp = requests.post(f"{BASE_URL}/inventory_levels/adjust.json", headers=HEADERS, json=payload)
```

Use `adjust` for "add 50 stock". Use `set` (action 9) for "set stock to 9999".

### 24. List Locations

```python
resp = requests.get(f"{BASE_URL}/locations.json", headers=HEADERS)
for loc in resp.json().get("locations", []):
    print(f"  ID {loc['id']} | {loc['name']} | {loc.get('address1')}, {loc.get('city')}")
```

### 25. Create Refund on an Order

```python
# Step 1 — calculate
calc_resp = requests.post(
    f"{BASE_URL}/orders/{order_id}/refunds/calculate.json",
    headers=HEADERS,
    json={"refund": {"shipping": {"full_refund": True}, "refund_line_items": []}}
)
calc = calc_resp.json().get("refund", {})

# Step 2 — apply
payload = {
    "refund": {
        "notify": False,
        "note": "QA test refund",
        "shipping": {"full_refund": True},
        "refund_line_items": calc.get("refund_line_items", []),
        "transactions": calc.get("transactions", [])
    }
}
resp = requests.post(f"{BASE_URL}/orders/{order_id}/refunds.json", headers=HEADERS, json=payload)
```

---

## Execution Pattern

Always run Python in the project virtualenv:

```bash
cd /Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert
PYTHONPATH=. .venv/bin/python -c "
# paste the action code here
"
```

Or write a temp script:

```bash
PYTHONPATH=. .venv/bin/python /tmp/shopify_action.py
```

---

## Response Format

**For list:**
```
Found 8 products:
- ID 9614590017847 | "Test Product A" | active | variant: 49091417047351 ($10.00)
- ID 9213872439516 | "Test Product B" | active | variant: 47470441201884 ($5.00)
```

**For create:**
```
Created order #1801
- Order ID: 6900000000000
- Product: Test Product A (qty 1)
- Ship to: John Smith, 123 Main St, Sydney NSW 2000, AU
- Financial status: paid
```

**For variable product:**
```
Created variable product "AU Post Test T-Shirt" (ID 9700000000001)
Variants (8 total):
  - S / Red  → variant ID 49100000000001 | $15.00
  - S / Blue → variant ID 49100000000002 | $15.00
  ...
```

**For errors:**
```
API error 422: {"errors": {"line_items": ["is too short (minimum is 1 character)"]}}
```

---

## Important Notes

- This skill uses the **same test store** and **same credentials** as the AI QA Agent browser flows.
- Products created here are real in the store and can immediately be used for AU Post label generation in the dashboard.
- Default address for domestic orders: **Sydney, NSW 2000, Australia**.
- For eParcel international: use UK (London) or CA (Toronto) addresses.
- MyPost Business: domestic Australian addresses only — no international.
- Pagination: Shopify returns max 250 records per page. For full lists use cursor-based pagination via `page_info` in the `Link` response header.
- `SHOPIFY_ACTIONS_PATH` in `.env` has a **trailing space** — `config.py` reads it as-is; never strip it manually.
