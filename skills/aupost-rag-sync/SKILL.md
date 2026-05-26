---
name: aupost-rag-sync
description: Use inside AUPostDomainExpert when QA asks Claude to pull latest and sync/reindex RAG knowledge for codebase (automation), backend, frontend, wiki, PluginHive docs, or full knowledge. Never run full reindex unless explicitly requested. Automation sync is branch-aware — ask QA for branch unless provided.
---

# AU Post RAG Sync

Use this skill to keep the ChromaDB knowledge collections up to date with the latest source repos and docs.

## First Reads

1. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/CLAUDE.md`
2. Read `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-rag-sync/references/rag_sync_flow.md`

## Two Knowledge Collections

| Collection | Content | Ingest Source Key |
|---|---|---|
| `aupost_knowledge` | Domain docs, PluginHive docs, test cases, wiki, app, AU Post API | `pluginhive_docs`, `pluginhive_seeds`, `sheets`, `wiki`, `app`, `aupost_api` |
| `aupost_code_knowledge` | Automation POM + specs, backend code, frontend code | `codebase` (automation), `codebase` (backend/frontend) |

## Ingest Commands

```bash
# Domain knowledge only (pluginhive_docs)
python -m ingest.run_ingest --sources pluginhive_docs

# Seed URL scrape (pluginhive_seeds)
python -m ingest.run_ingest --sources pluginhive_seeds

# Google Sheets test cases (eParcel + MyPost Business)
python -m ingest.run_ingest --sources sheets

# Internal wiki
python -m ingest.run_ingest --sources wiki

# AU Post REST API knowledge
python -m ingest.run_ingest --sources aupost_api

# Live app UI knowledge (scraped from app pages)
python -m ingest.run_ingest --sources app

# Automation codebase (POM + specs)
python -m ingest.run_ingest --sources codebase

# Full default rebuild (ALL sources — clears collection first)
python -m ingest.run_ingest

# Force clear + rebuild specific source (additive by default for partial)
python -m ingest.run_ingest --sources wiki --clear
```

**Important**: Partial `--sources` runs are ADDITIVE (do NOT clear the collection unless `--clear` is passed). Full rebuild with all default sources clears automatically.

## Branch Rules

| Repo | Default Branch | Notes |
|---|---|---|
| Backend (`shopify-australia-post-app`) | `master` | Pull master before sync |
| Frontend (`shopify-au-post-web-client`) | `main` | Pull main before sync |
| Automation (`aupost-test-automation`) | Ask QA | Branch-aware — always ask unless specified |
| Wiki (`aupost-wiki`) | Current branch or main | Source-only (read only) |

## Safe Defaults

- Backend → sync master
- Frontend → sync main
- Wiki → source-only, no push
- Automation → **always ask QA for branch** before pulling
- Full rebuild → never run unless explicitly requested

## Dirty Repo Check

Before pulling any repo:
1. Run `git status` in the repo directory
2. If dirty (uncommitted changes): stop and ask QA how to proceed
3. Never `git stash` or `git reset` without explicit QA instruction

## What To Report

After sync:
```
## RAG Sync Report

### Sources Synced
- <source_type>: <repo/URL> @ <branch/tag> — <chunks added/updated>

### Collections Updated
- aupost_knowledge: <old count> → <new count> chunks
- aupost_code_knowledge: <old count> → <new count> chunks

### Errors / Warnings
- <any errors encountered>

### Recommended Follow-Up
- <if knowledge maintainer update needed>
```

## Do Not

- Do not run full collection rebuild unless explicitly asked
- Do not pull automation repo without branch confirmation
- Do not clear collection on partial `--sources` runs (additive is default)
- Do not push to any remote repo
