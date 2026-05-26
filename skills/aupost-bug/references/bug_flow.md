# AU Post Bug Flow Reference

This reference mirrors `pipeline/bug_tracker.py` and the dashboard Bug Reporter tab.

## Dashboard Flow

```
QA describes bug (plain English)
  → Format as Jira-style bug draft
  → Check Trello Backlog for duplicates (aupost-trello-operator)
  → Show duplicate card OR formatted draft to QA
  → QA approves
  → Create Backlog card
  → Comment on release card (if applicable)
```

## Bug Draft Fields

Required:
- `title`: "Bug: <concise description>"
- `severity`: P1 | P2 | P3 | P4
- `account_type`: eParcel | MyPost Business | Both
- `feature_area`: Shipping / Label Generation / SideDock / Settings / Products / Pickup / Return Label / Rates Log / Manifest / Order Summary
- `steps_to_reproduce`: numbered list
- `expected_behavior`: what should happen
- `actual_behavior`: what actually happened
- `labels`: ["QA Reported", "AUPOST-APP", "P<N>"]

## Severity Reference

| Severity | Example |
|---|---|
| P1 | Label generation crashes; orders grid won't load |
| P2 | Request Signature? not applying to shipment JSON; wrong service code in T28 request |
| P3 | Insurance amount off by $1; wrong label layout displayed |
| P4 | Typo in Settings page heading; misaligned UI element |

## Account Type On Bug

Always note account type when the bug only affects one:
- eParcel-only: e.g. Dangerous Goods checkbox missing
- MyPost Business-only: e.g. Extra Cover cap showing $5,000 instead of $1,000
- Both: e.g. Download Documents ZIP empty

## Duplicate Rules

Same bug = same broken behavior + same feature area or likely same root cause
Different bug = different feature, different page, different trigger, different account type

When duplicate found:
- Show existing card URL to QA
- Ask if they want to add a comment to the existing card instead

## Developer Detection

To find the developer assigned to a release card (for notifying them of the bug):
```python
# get_card_devs is in pipeline/bug_reporter.py (NOT trello_client.py)
from pipeline.bug_reporter import get_card_devs
devs = get_card_devs(release_card_id)
```

## Backlog Target

List name: "Backlog" (on TRELLO_BOARD_ID: `PWKHwiCI`)
Label names: QA Reported, AUPOST-APP, P1/P2/P3/P4

**Label caveat**: Trello labels must already exist on the board before they can be applied. If a label name is not found, create it via `TrelloClient` or ask QA to create it in the Trello UI first.

## Linked Release Card Comment

When the bug was found while testing a specific release card:
```
Bug raised to Backlog: [<title>](<url>)
Severity: P<N>
Account Type: eParcel / MyPost Business / Both
Release: <release name if known>
```
