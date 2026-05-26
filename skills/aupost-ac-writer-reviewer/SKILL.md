---
name: aupost-ac-writer-reviewer
description: Use when working inside the AUPostDomainExpert project and the user gives a Trello card, feature request, bug/customer issue, PR note, or rough requirement and wants dashboard-style User Story plus Acceptance Criteria markdown generated, reviewed, rewritten, and prepared for Trello comment posting only. Covers both eParcel and MyPost Business account types.
---

# AU Post AC Writer Reviewer

Use this skill to create the dashboard-style User Story and Acceptance Criteria output for the PluginHive AU Post Shopify app.

This is the Codex/Claude equivalent of the dashboard `Validate AC` generation and review flow, with one publishing rule:

- Generated User Story + AC must be posted to Trello comments only.
- Do not update, overwrite, or merge into the Trello card description.

1. Understand the card/request.
2. Gather relevant project/domain context — especially which account type (eParcel / MyPost Business / both).
3. Generate story + AC markdown in the same structure as `pipeline/card_processor.py`.
4. Review the AC for gaps, unsupported claims, duplicate scenarios, and missing account-type prerequisites.
5. Rewrite once if review findings require it.

## Trello Publishing Rule

When the user asks to add/save/post the generated US + AC to Trello:

- add it as a new Trello comment only
- do not call `update_card_description`
- do not replace the card description

Use `aupost-trello-operator` for actual Trello reads/writes. If unavailable, return a paste-ready Trello comment.

## First Reads

Before writing:

1. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/CLAUDE.md`
2. Use the AU Post domain core research workflow when needed:
   - `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-domain-core/SKILL.md`
3. Read the exact generation/review rules:
   - `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-ac-writer-reviewer/references/ac_generation_review.md`
4. Inspect relevant project files:
   - `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/pipeline/card_processor.py`
   - `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/pipeline/domain_validator.py`
   - `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/pipeline/requirement_research.py`

## Account Type Rules

Always identify which account type the scenario applies to:

| Feature | eParcel | MyPost Business |
|---|---|---|
| Domestic shipping | ✅ | ✅ |
| International shipping | ✅ | ❌ |
| Extra Cover max | $5,000 AUD | $1,000 AUD |
| Dangerous Goods | ✅ (domestic only) | ❌ |
| Parcel Post (T28) | ✅ | ❌ |
| Express Post (E86J) | ✅ | ❌ |

If the card does not specify, cover both account types or flag this as an open question.

## Output Structure

```markdown
## User Story
As a [type of user], I want [goal], so that [benefit].

## Domain Rules / AU Post Constraints
...

## Acceptance Criteria
Scenario 1: <short scenario name>
Given ...
When ...
Then ...

## Priority
High / Medium / Low - <one sentence justification>

## Scenario Source Attribution
- Scenario 1 -> Card request; wiki; Related card; AU Post API docs; PluginHive/app behaviour

## Test Scope
...

## Out of Scope
- Mobile / responsive / viewport testing (we test web/desktop only).
- MyPost Business does not support international / Dangerous Goods (exclude for MyPost scenarios).

## References
- [label](URL)
```

## AC Requirements

Acceptance Criteria must:
- use Given / When / Then
- cover happy path, edge cases, error states, and regression/customer-impact cases
- state exact account type prerequisite (eParcel / MyPost Business) when behavior differs
- state exact SideDock checkbox names: "Request Signature?", "Authority to Leave", "Insure package"
- avoid mobile/responsive/viewport AC
- avoid unit-test/backend-only AC
- include concrete expected outcomes testable in the live app browser

## Review Pass

Before finalizing, self-review for:
- duplicate or overlapping scenarios
- vague expected results
- missing account-type prerequisites
- unsupported claims
- missing customer-impact/regression coverage for bug cards
- wrong SideDock checkbox names
- wrong Shopify More Actions link names

## Final Response

Return:
- final story + AC markdown
- review notes if useful
- Trello target: comment only, not description
