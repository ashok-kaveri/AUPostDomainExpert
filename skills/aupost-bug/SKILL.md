---
name: aupost-bug
description: Use when working inside the AUPostDomainExpert project and QA reports a bug during AI QA/browser/manual testing and wants it formatted, checked against existing Trello Backlog cards, and created in the Trello Backlog list. Mirrors the dashboard Bug Reporter flow: plain-English QA issue -> Jira-style bug draft -> duplicate check -> create Backlog card after approval.
---

# AU Post Bug Reporter

Use this skill when QA reports a bug and wants it tracked in Trello.

## Flow

1. QA describes the bug in plain English
2. Format as a structured Jira-style bug draft
3. Check Trello Backlog for duplicates using `aupost-trello-operator`
4. Show duplicate OR formatted draft for QA review
5. Create Trello Backlog card only after QA approves
6. Comment on the release card if the bug was found while testing that card

## First Reads

1. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/CLAUDE.md`
2. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-bug/references/bug_flow.md`
3. Use `aupost-trello-operator` for Trello reads/writes

## Bug Draft Format

```json
{
  "title": "Bug: <concise description>",
  "severity": "P1 | P2 | P3 | P4",
  "account_type": "eParcel | MyPost Business | Both",
  "feature_area": "<Shipping / Label Generation / SideDock / Settings / Products / Pickup / Return Label / Rates Log / Manifest>",
  "steps_to_reproduce": ["1. ...", "2. ...", "3. ..."],
  "expected_behavior": "...",
  "actual_behavior": "...",
  "labels": ["QA Reported", "AUPOST-APP", "P<N>"]
}
```

## Severity Guide

| Severity | When to Use |
|---|---|
| P1 | Crash, data loss, label generation completely broken |
| P2 | Core feature broken — label fails, wrong service code, SideDock not applying |
| P3 | Non-blocking issue — wrong label layout, incorrect field value, UI glitch |
| P4 | Minor UX issue, typo, cosmetic problem |

## Trello Card Description Format

```
**Type**: Bug
**Severity**: P<N>
**Account Type**: eParcel / MyPost Business / Both
**Feature Area**: <area>
**Environment**: QA Store
**Release**: <from card if known>
**Labels**: QA Reported, AUPOST-APP, P<N>

**Steps to Reproduce**:
1. ...
2. ...
3. ...

**Expected Behaviour**: ...

**Actual Behaviour**: ...
```

## Duplicate Check

Same bug = same broken behavior in same feature area or likely same root cause → duplicate
Different = different feature area, different page, different behavior → create new card

## Target List

Backlog list on the shared Trello board (TRELLO_BOARD_ID: `PWKHwiCI`)

## Release Card Comment

If bug found while testing a specific card:
"Bug raised to Backlog: [<title>](<url>) · Severity: P<N> · Account Type: <type>"
