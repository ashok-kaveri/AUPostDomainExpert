# Trello Operations Reference

## Project Client

`pipeline/trello_client.py` — `TrelloClient` class with methods:
- `get_boards()`
- `get_lists(board_id)`
- `get_cards_in_list(list_id)`
- `get_card(card_id)`
- `get_card_members(card_id)`
- `add_comment(card_id, text)`
- `move_card_to_list(card_id, list_id)`
- `create_card(list_id, name, desc)`
- `search_cards_on_board(query)`

## Board

Shared AU Post + FedEx board: `PWKHwiCI` (set as `TRELLO_BOARD_ID` in `.env`)

## Card References

Users may provide:
- Full URL: `https://trello.com/c/{shortId}/...`
- Short URL: `trello.com/c/{shortId}`
- Full ID (24-char hex)
- Short ID (numeric)

Script normalizes all forms. Extract the shortId from URLs.

## Developer Detection

`get_card_devs(card_id)` is defined in **`pipeline/bug_reporter.py`** (NOT in `trello_client.py`):
- Fetches card members via `TrelloClient.get_card_members(card_id)`
- Filters out known QA names (Madan, Ashok, known QA team members)
- Returns remaining members as developers

```python
from pipeline.bug_reporter import get_card_devs
devs = get_card_devs(card_id)  # returns list of member display names
```

Known QA team members (filtered out automatically):
- Madan (QA lead)
- Ashok Kumar N (DevOps/Backend)

## Comment Rules

- US/AC: new comment only, never overwrite description
- TC summary: new comment only
- Bug: use `aupost-bug` skill, not this operator

## Write Boundaries

- US/AC generation: comment only (never `update_card_description`)
- TC summary: comment only
- Bug Backlog: delegate to `aupost-bug`
- Handoff docs: attach/comment when asked
- Do not overwrite descriptions
