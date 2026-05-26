---
name: aupost-dashboard-tc-publisher
description: Use when working inside the AUPostDomainExpert project and the user has already generated a User Story plus Acceptance Criteria and now wants dashboard-style QA test cases generated from that US/AC using AU Post project/domain/automation knowledge, with the two dashboard publish formats: compact Trello QA comment and positive-case CSV rows for the Ai sheet tab. This skill is generation-only and must not call Trello, Google Sheets, Slack, Shopify, or project LLM APIs.
---

# AU Post Dashboard TC Publisher

Use this skill to generate dashboard-style test cases and their publish formats for the AU Post Shopify app.

Input: User Story + Acceptance Criteria (eParcel and/or MyPost Business)
Output modes: Detailed TC Markdown, Compact Trello QA Comment, CSV rows for Ai tab, Publish Package

## First Reads

1. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/CLAUDE.md`
2. Read the publish formats reference:
   `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-dashboard-tc-publisher/references/dashboard_tc_formats.md`

## TC Generation Rules

- Generate 4+ TCs minimum (at least 2 Positive, 1 Negative, 1 Edge)
- Cover every AC scenario across TCs
- Only Positive cases go to CSV/Google Sheet rows
- Negative and Edge TCs go to Trello comment only
- Assign correct account type (eParcel / MyPost Business / Both) per TC
- Assign correct execution flow per TC

## Detailed TC Markdown Format

```markdown
### TC-n: <Title>
**Type**: Positive | Negative | Edge
**Priority**: High | Medium | Low
**Account Type**: eParcel | MyPost Business | Both
**Execution Flow**: manual | auto | settings | order-grid | product-admin | pickup | return-label | rates-log | none
**Preconditions**:
- ...

**Steps**:
Given ...
When ...
Then ...

**Expected Result**: ...
**Comments**: <any notes for QA — optional>
```

## Compact Trello QA Comment Format

```
📋 **QA Test Cases — <Feature Name>**

✅ Positive (→ Sheet + Trello)
TC-1: <one-line summary from first Then>
TC-2: ...

❌ Negative (→ Trello only)
TC-3: ...

⚠️ Edge (→ Trello only)
TC-4: ...

**Total**: X TCs | ✅ Y Positive → Sheet | ❌ Z Negative | ⚠️ W Edge
```

## CSV / Google Sheet Rows Format

Target tab: **Ai** (always — no legacy tab mapping needed)

Columns:
| SI No | Epic | Scenarios | Description | Comments | Priority | Details/Transaction ID | Pass/Fail [Shopify] | Release |

Rules:
- Only Positive TCs → CSV rows
- Negative and Edge TCs → Trello comment only
- `Epic` = card/feature name
- `Scenarios` = TC title
- `Description` = TC description / first Then step
- `Comments` = optional QA notes (account type caveat, setup requirement, etc.)
- `Priority` = High / Medium / Low
- `Details/Transaction ID` = blank (filled during testing)
- `Pass/Fail [Shopify]` = blank (filled during testing)
- `Release` = from card if known

**Duplicate-check rule**: Before generating, check if TCs for this card/feature are already in the sheet — do not add duplicate rows. Ask QA if unsure.

## Publish Package

When user asks for the full publish package, return:
1. Detailed TC Markdown
2. Compact Trello QA Comment (paste-ready)
3. CSV rows for Ai tab (paste-ready)
4. Count summary:
   ```
   📊 TC Summary: X total | ✅ Y → Sheet | ❌ Z → Trello only | ⚠️ W → Trello only
   ```

## Account Type TC Rules

eParcel TCs:
- May include international, Dangerous Goods, Extra Cover up to $5,000, T28/E86J service codes

MyPost Business TCs:
- Domestic only, Extra Cover up to $1,000, no Dangerous Goods, no T28/E86J
- Label these clearly: **Account Type: MyPost Business**

## Do Not

- Call Trello, Google Sheets, Slack, or any external API
- Generate mobile/responsive/viewport TCs
- Generate backend-only/unit-test TCs
- Output legacy tab names — always use "Ai"
