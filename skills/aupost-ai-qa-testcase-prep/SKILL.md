---
name: aupost-ai-qa-testcase-prep
description: Use when working inside the AUPostDomainExpert project and the user gives a Trello card link, card id, feature request, AC draft, or story description and wants full detailed browser-testable test cases prepared specifically for AI QA Agent / Chrome verification, using AU Post Domain Expert rules, evidence strategies (Strategy 1/2/3), and automation-flow knowledge. Covers both eParcel and MyPost Business. Do not use for compact Trello comments or CSV rows — use aupost-dashboard-tc-publisher for those.
---

# AU Post AI QA Test Case Prep

Use this skill to create detailed browser-executable test cases for the AU Post Shopify app.

These are richer than compact TC summaries — they include exact preconditions, explicit step sequences, and evidence sources so the AI QA browser agent can verify them without guessing.

## First Reads

1. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/CLAUDE.md`
2. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-domain-core/SKILL.md`
3. If Trello input: use `aupost-trello-operator` to fetch the real card content first. If Trello is unavailable, ask QA to paste the card description and AC text directly.

## TC Output Format

```markdown
### TC-n: <Title>
**Type**: Positive | Negative | Edge
**Priority**: High | Medium | Low
**Account Type**: eParcel | MyPost Business | Both
**Execution Flow**: manual | auto | settings | order-grid | product-admin | pickup | return-label | rates-log | none
**Preconditions**:
- Account type configured: eParcel / MyPost Business
- Order state: unfulfilled / has label / etc.
- Product setup: <if needed>
- SideDock: <if needed>

**Steps**:
Given <starting state>
When <action>
And <further action>
Then <expected result>
And <further verification>

**Expected Result**: <plain English — what the QA agent should see>
**Preferred Evidence**: Strategy 1 (label badge) | Strategy 2 (Download ZIP JSON fields) | Strategy 3 (Print Documents PDF)
**Evidence Details**: <exact JSON field and expected value if Strategy 2>
```

## Evidence Strategy Mapping

| Scenario Type | Evidence Strategy |
|---|---|
| Label is generated / status badge | Strategy 1 |
| Request Signature? | Strategy 2: `options.signature_on_delivery = true` |
| Authority to Leave | Strategy 2: `options.authority_to_leave = true` |
| Insure package (Extra Cover) | Strategy 2: `options.extra_cover.amount = <value>` |
| Dangerous Goods | Strategy 2: `items[0].contains_dangerous_goods = true` |
| Service code (Parcel Post) | Strategy 2: `items[0].product_id = 'T28'` |
| Service code (Express Post) | Strategy 2: `items[0].product_id = 'E86J'` |
| Service code (Intl Economy) | Strategy 2: `items[0].product_id = 'PLT'` |
| Tracking number | Strategy 2: `trackingNumbers[0]` or Strategy 3 |
| Visual label / document present | Strategy 3 (Print Documents PDF) |
| Settings saved | UI persistence check |
| Order grid tab / filter | Order grid observation |

## Minimum TC Set

Generate at least:
- 2 Positive cases (happy path for each scenario)
- 1 Negative case (wrong input / account-type restriction)
- 1 Edge case (boundary: max Extra Cover, Dangerous Goods eParcel-only, etc.)

Cover every AC scenario across TCs.

## Account Type Coverage

For features that differ between account types, create separate TCs:
- TC-n: eParcel version
- TC-n+1: MyPost Business version (with correct limits/restrictions)

MyPost Business TCs must NOT include: international shipping, Dangerous Goods, $5,000 Extra Cover.

## Execution Flow Assignment

Assign the correct execution flow:
- Label generation scenarios → `manual` or `auto`
- Settings scenarios → `settings`
- Order grid / filter / status → `order-grid`
- Product dimensions / signature / DG config → `product-admin`
- Pickup scheduling → `pickup`
- Return label → `return-label`
- Rates log / rate request JSON → `rates-log` (the AU Post rates log is an **in-page JSON dialog**, NOT a ZIP download; it opens via ⋯ → View Logs during manual label flow after Get Shipping Rates)
- Backend-only / no browser → `none`

## Do Not Include

- Mobile / responsive / viewport scenarios
- Unit test / backend-only cases
- Cases requiring mock data injection
