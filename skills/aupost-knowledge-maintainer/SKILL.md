---
name: aupost-knowledge-maintainer
description: Use inside AUPostDomainExpert after an AU Post release card cycle is complete, or when QA asks Claude to update old, wrong, missing, or outdated project knowledge. Updates approved-card RAG, QA retrospective feedback, durable CLAUDE.md/skill rules, and replaces obsolete knowledge without duplicating stale instructions.
---

# AU Post Knowledge Maintainer

Use this skill after a card cycle completes to keep project knowledge fresh and accurate.

It updates three layers:
1. **Approved card RAG** — final US/AC, TCs, AI QA evidence, automation file paths
2. **QA retrospective memory** — what was learned (new locators, flow discoveries, account-type edge cases)
3. **Durable local instructions** — CLAUDE.md and skill files when a stable rule truly changed

## First Reads

1. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/CLAUDE.md`
2. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-knowledge-maintainer/references/knowledge_update_flow.md`

## What To Collect

For each completed card:
- Card ID, name, Trello URL
- Final description, US/AC comment, TC comment
- AI QA verdict summary (pass/fail/partial per scenario)
- Automation spec file path(s)
- Bug cards raised (if any)
- Handoff doc paths (if any)
- QA retrospective notes:
  - New locators discovered
  - Flow corrections (e.g. wrong checkbox name → correct name)
  - Account-type edge cases validated
  - RAG gaps found during the run

## What Goes Where

| Knowledge Type | Destination |
|---|---|
| Final US/AC + TCs | RAG via `pipeline/rag_updater.update_rag_from_card(card_id, card_data)` with stable card IDs |
| AI QA evidence summary | RAG via `aupost_knowledge` collection |
| New locator trace | `data/ai_qa_locator_traces/{card_id}.json` |
| QA feedback / learnings | RAG via `aupost_knowledge` with source_type="qa_feedback" |
| Durable rule change | Update CLAUDE.md and/or relevant skill SKILL.md |
| Obsolete rule | Find old statement → replace/narrow — do NOT duplicate stale text |

## Outdated Knowledge Cleanup

When a rule changed (e.g. a checkbox was renamed, a route was fixed):
1. Find old statement in CLAUDE.md / skill files / RAG
2. Decide: fully wrong → replace | too broad → narrow | exception found → add exception
3. Update the file with the correction
4. Search for other places using the old wording
5. Summarize what was replaced

Do NOT add new correct knowledge on top of wrong knowledge — replace it.

## How To Call update_rag_from_card

```python
# In the project root (AUPostDomainExpert):
import sys; sys.path.insert(0, '.')
from pipeline.rag_updater import update_rag_from_card

card_data = {
    "id": "<card_id>",
    "name": "<card name>",
    "desc": "<description / US + AC text>",
    "comments": ["<tc comment text>", "<ai qa summary>"],
    "url": "<trello url>",
    "source_type": "approved_card",   # or "qa_feedback"
}
update_rag_from_card("<card_id>", card_data)
```

Or run directly:
```bash
cd /Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert
PYTHONPATH=. .venv/bin/python -c "
from pipeline.rag_updater import update_rag_from_card
update_rag_from_card('<card_id>', {...})
"
```

## Re-Ingest Decision

Run `aupost-rag-sync` only when a source repo actually changed.
- Added new wiki page → sync wiki
- Merged PR to backend/frontend → sync that repo
- New automation specs added → sync automation
- Full rebuild only when explicitly requested or collection is corrupt

## Maintenance Report

Return:
```
## Knowledge Maintenance Report — <card name>

### RAG Updated
- <what was upserted, with stable ID>

### QA Feedback Saved
- <learnings saved: new locators, flow corrections, edge cases>

### Durable Docs Updated
- <CLAUDE.md section updated — what changed>
- <skill file updated — what changed>

### Outdated Rules Replaced
- <old rule> → <new rule>

### Re-Ingest Needed
- <yes/no — reason>

### QA Confirmation Needed
- <anything QA should verify before closing>
```

## Do Not

- Do not add duplicate knowledge on top of wrong knowledge — replace it
- Do not run full RAG rebuild unless explicitly asked
- Do not update Trello, Slack, or automation repo unless QA asks
