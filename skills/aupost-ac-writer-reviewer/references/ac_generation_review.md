# AC Generation And Review Rules

This reference mirrors the dashboard flow in `pipeline/card_processor.py` and `pipeline/domain_validator.py`.

Codex/Claude publishing rule:
- Generated User Story + Acceptance Criteria are for Trello comment posting only.
- Do not update the Trello card description.

## Generation Intent

Act as a senior QA engineer and product owner for the AU Post Shopify App built by PluginHive.

Work research-first. Ground the final card in:
- card type and account type (eParcel / MyPost Business / both)
- linked references
- customer issue / Zendesk signals
- known prerequisites and risks
- AU Post API / PluginHive / Shopify behavior facts

## Required Markdown Structure

```markdown
## User Story
As a [type of user], I want [goal], so that [benefit].

## Domain Rules / AU Post Constraints
Concrete AU Post, PluginHive, Shopify, API, or app limitations.

## Acceptance Criteria
Scenario 1: <short title>
Given ...
When ...
Then ...

## Priority
High / Medium / Low - justify in one sentence.

## Scenario Source Attribution
- Scenario 1 -> Card request; wiki; Related card; AU Post API docs

## Test Scope
List app sections and automation areas needing coverage.

## Out of Scope
- Mobile / responsive / viewport testing (we test web/desktop only).

## References
- [label](URL)
```

## Account Type Constraint Rules

eParcel constraints to capture:
- Supports international shipping
- Extra Cover up to $5,000 AUD
- Dangerous Goods available for domestic only
- Service codes: T28 (Parcel Post), E86J (Express Post), PLT (Intl Economy)

MyPost Business constraints to capture:
- Domestic only — no international
- Extra Cover up to $1,000 AUD — NOT $5,000
- NO Dangerous Goods
- Services: Standard, Express (no T28/E86J codes)

Always add account type in Domain Rules when the behavior differs between accounts.

## Test Scope Areas

- Label Generation (Manual / Auto)
- Shipping Grid (All / Pending / Label Generated / Manifest Completed / Returns tabs)
- Order Summary (Print Documents, Download Documents ZIP, Cancel Label, Return Label)
- SideDock (Request Signature?, Authority to Leave, Insure package, Safe Drop, Dangerous Goods)
- Settings (/setting route): Account, Packaging, Rates, Documents/Labels, Additional, International, Pickup
- Product Config (/products): dimensions, Is Signature Needed dropdown, Declared Value, Is Dangerous Goods
- Return Labels (Way A: app Order Summary | Way B: Shopify More Actions)
- Pickup Scheduling
- Rates Log (/rateslog): View dialog with Request/Response JSON
- Manifest (/manifest)
- eParcel vs MyPost Business account type differences

## AC Rules

Cover:
- happy path
- edge cases (e.g. Extra Cover at max limit, domestic address only for Dangerous Goods)
- error states
- account-type limitation cases (e.g. "MyPost Business cannot generate international label")
- regression scenarios for bug/customer issue cards

State exact prerequisites for:
- account type (eParcel vs MyPost Business)
- order state (unfulfilled / has label / etc.)
- SideDock configuration
- product settings

Do NOT write AC for:
- mobile viewports
- responsive breakpoints
- unit tests
- backend function calls

## Review Criteria

Before finalizing:
- duplicate or overlapping scenarios
- vague expected results
- missing account-type prerequisites
- unsupported claims
- missing customer-impact/regression coverage
- wrong SideDock checkbox names (must be: "Request Signature?", "Authority to Leave", "Insure package")
- wrong Shopify More Actions names (must be: "AU Post Generate Label", "Au Post Return Label")

## Domain Validation Style

For validating an existing draft:
- overall status: PASS / NEEDS_REVIEW / FAIL
- summary
- requirement gaps
- AC gaps
- accuracy issues (especially account-type mix-ups)
- suggestions
- rewrite instructions
