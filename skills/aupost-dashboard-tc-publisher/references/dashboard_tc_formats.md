# Dashboard TC Publish Formats

This reference mirrors `pipeline/card_processor.py` and `pipeline/sheets_writer.py` dashboard formats.

## Detailed Test Case Markdown

Block format — one `### TC-n:` block per test case:

```markdown
### TC-n: <Title>
**Type**: Positive | Negative | Edge
**Priority**: High | Medium | Low
**Account Type**: eParcel | MyPost Business | Both
**Execution Flow**: manual | auto | settings | order-grid | product-admin | pickup | return-label | rates-log | none
**Preconditions**:
- Account type: eParcel / MyPost Business configured
- Order state: <unfulfilled / has label / etc.>
- <SideDock state if applicable>
- <product setup if applicable>

**Steps**:
Given <starting state>
When <QA performs action>
And <further action>
Then <expected observable result>
And <further verification if needed>

**Expected Result**: <plain English>
**Preferred Evidence**: Strategy 1 (label badge) | Strategy 2 (Download ZIP JSON) | Strategy 3 (Print Documents PDF)
```

### Validation Rules

Every TC must have:
- **Type** field
- **Priority** field
- **Account Type** field
- **Preconditions** section
- **Steps** section with at least one Then
- **Expected Result**

Do NOT include:
- Unit test / backend-only cases
- Mobile / responsive cases
- Cases that cannot be verified in the live browser

## Compact Trello QA Comment

```
📋 **QA Test Cases — <Feature Name>**

✅ Positive (→ Sheet + Trello)
TC-1: <one-line summary>
TC-2: ...

❌ Negative (→ Trello only)
TC-3: ...

⚠️ Edge (→ Trello only)
TC-4: ...

**Total**: X TCs | ✅ Y Positive → Sheet | ❌ Z Negative | ⚠️ W Edge
```

Summary line: derive from first `Then` step of each TC.

## CSV / Google Sheet Row Format

Target sheet tab: **Ai** (always — override any legacy keyword detection)

Column mapping:
| Column | Source |
|---|---|
| SI No | Auto-increment |
| Epic | Card/feature name |
| Scenarios | TC title |
| Description | TC description or first Then step |
| Comments | Additional notes or evidence strategy |
| Priority | High / Medium / Low |
| Details/Transaction ID | TC ID (TC-1, TC-2, etc.) |
| Pass/Fail [Shopify] | Leave blank |
| Release | From card metadata if known |

### Positive-Only Rule

Only **Positive** TCs produce CSV rows.
Negative and Edge TCs appear in the Trello QA comment only.

## eParcel vs MyPost Business Rows

When feature affects both account types:
- Create separate CSV rows for eParcel version and MyPost Business version
- Label the Scenarios column clearly: "TC-n: <title> (eParcel)" and "TC-n: <title> (MyPost Business)"

## Evidence References In TC

Always specify which evidence strategy applies:
- **Strategy 1**: Check "label generated" status badge in Order Summary
- **Strategy 2**: More Actions → Download Documents → ZIP extracted → verify JSON field:
  - `options.signature_on_delivery` = true/false
  - `options.authority_to_leave` = true/false
  - `options.extra_cover.amount` = <AUD value>
  - `items[0].product_id` = 'T28' | 'E86J' | 'PLT'
  - `items[0].contains_dangerous_goods` = true
  - `trackingNumbers[0]` = tracking number
- **Strategy 3**: Print Documents → new tab → document-viewer.pluginhive.io → visual PDF

## Count Summary Format

```
📊 TC Summary: X total | ✅ Y Positive → Sheet | ❌ Z Negative → Trello only | ⚠️ W Edge → Trello only
```
