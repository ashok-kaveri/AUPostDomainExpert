---
name: aupost-trello-operator
description: Use inside AUPostDomainExpert when the user asks to work with Trello using project .env credentials: read boards, lists, cards, descriptions, comments, checklists, attachments, fetch all cards from a list, identify the developer assigned to a card, add comments or QA replies, move cards, search cards, or create generic Trello cards. For QA bug Backlog creation, use aupost-bug. Requires explicit user intent before any Trello write.
---

# AU Post Trello Operator

Use this skill for Trello operations inside the AUPostDomainExpert project.

## First Reads

1. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/CLAUDE.md` for project context.
2. Load `.env` from `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/.env`.
3. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-trello-operator/references/trello_ops.md` for Trello operation patterns.

## Credentials

From project `.env`:
- `TRELLO_API_KEY`
- `TRELLO_TOKEN`
- `TRELLO_BOARD_ID` (shared with FedEx board: `PWKHwiCI`)

## Read Tasks (allowed freely)

- Read board lists
- Fetch cards from a list
- Read card description, comments, checklists, attachments
- Identify developer assigned to a card
- Search cards on board

## Write Tasks (require explicit user intent)

- Add a comment to a card (QA reply, US/AC comment, TC summary)
- Move card to a different list
- Create a generic Trello card

## US/AC and TC Publishing Rule

- US/AC: post as Trello comment only — never update card description
- TC summary: post as Trello comment only
- Use `fedex-bug` (or `aupost-bug`) for Backlog bug creation

## Card References

Accept any of:
- Full Trello URL
- Short URL (trello.com/c/...)
- Full card ID
- Short card ID

## Developer Detection

Use `get_card_devs` / member filtering to identify developers.
Filter out known QA names. Remaining members are developers.

## Do Not

- Overwrite card descriptions for US/AC generation
- Create Backlog bug cards — use `aupost-bug` for that
- Send to Slack from this skill — use `aupost-slack-operator`
