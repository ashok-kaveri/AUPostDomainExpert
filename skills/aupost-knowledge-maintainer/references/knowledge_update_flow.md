# AU Post Knowledge Update Flow

## Goal

Make future Claude runs smarter by updating three knowledge layers after each card cycle:
1. Approved card memory (RAG)
2. QA retrospective memory (RAG + locator traces)
3. Durable local instructions (CLAUDE.md, skill files)

## End-To-End Card Cycle

```
Trello card approved
  → final US/AC Trello comment
  → reviewed TC Trello comment + Ai sheet rows
  → AI QA browser verification + locator trace saved
  → automation spec written + committed
  → bug cards if any
  → handoff docs if requested
  → QA sign-off sent
  → knowledge maintainer runs
```

## RAG Collections

| Collection | Source Types | Use |
|---|---|---|
| `aupost_knowledge` | pluginhive_docs, pluginhive_seeds, sheets, wiki, app, aupost_api, qa_feedback | Domain knowledge |
| `aupost_code_knowledge` | automation, backend, frontend | Code / POM knowledge |

## Upsert IDs

Use stable IDs to avoid duplicate chunks:
- Card artifacts: `card_{card_id}_{artifact_type}` (e.g. `card_abc123_us_ac`)
- QA feedback: `qa_feedback_{card_id}_{slug}`
- Locator trace: stored as JSON file, not in RAG

## What Goes In Each Layer

### RAG — Approved Card Layer
- Final US/AC markdown
- TC summary
- AI QA verdict + key findings
- Automation file paths

### RAG — QA Feedback Layer
source_type="qa_feedback" chunks:
- New SideDock checkbox name discovered/confirmed
- Route correction (e.g. "/setting" not "/settings")
- Account-type edge case validated
- Download Documents ZIP field confirmed
- Any correction to CLAUDE.md that other runs should know about

### Durable Docs Layer
Update only when a **stable rule** changed:
- CLAUDE.md — app architecture, locators, routes, account type rules
- Skill SKILL.md files — workflow rules, locator names, publishing rules
- Do NOT update for one-off card-specific learnings

## Outdated Knowledge Protocol

1. Search CLAUDE.md and skill files for old statement
2. Categorize:
   - **Fully wrong** → replace with correct statement
   - **Too broad** → narrow with exception
   - **Stale** → timestamp it or remove if superseded
3. Update file(s) with correction
4. Log in maintenance report: "old text → new text"

## Re-Ingest Triggers

| What Changed | Action |
|---|---|
| New wiki page added | `python -m ingest.run_ingest --sources wiki` |
| Backend PR merged | `python -m ingest.run_ingest --sources codebase` |
| New automation spec | `python -m ingest.run_ingest --sources codebase` |
| New PluginHive docs page | `python -m ingest.run_ingest --sources pluginhive_docs` |
| New test cases in sheets | `python -m ingest.run_ingest --sources sheets` |
| Full rebuild needed | `python -m ingest.run_ingest` (clears collection) |

## Classifications

| Type | Description |
|---|---|
| `card_artifact` | US/AC, TCs, AI QA evidence for a specific card |
| `qa_feedback` | Process learnings, locator discoveries, flow corrections |
| `domain_rule` | Stable app behavior rule (eParcel vs MyPost Business, API fields) |
| `automation_rule` | POM convention, locator name, spec contract rule |
| `dashboard_format` | TC/AC format, CSV format, Trello comment format |
| `obsolete_rule` | Old rule being replaced — delete or mark superseded |
