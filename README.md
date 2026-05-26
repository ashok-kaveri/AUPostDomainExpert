# AU Post Domain Expert

An AI-powered QA pipeline for the PluginHive **Australia Post Shopify App**.

Covers two account types: **eParcel** and **MyPost Business**.

## Capabilities

| Capability | Description |
|---|---|
| **Domain Expert Chat** | RAG-backed chatbot — answers questions about the AU Post app, API, test cases, and features |
| **Smart AC Verifier** | Agentic browser verification — navigates the live AU Post app, executes test scenarios, returns pass/fail evidence |
| **Pipeline Dashboard** | Streamlit UI — Trello cards → AC generation → AI QA verification → TC publishing → handoff docs |

---

## Models Required

### Claude (via Anthropic API)

| Model | Purpose |
|---|---|
| `claude-sonnet-4-6` | AC generation, AI QA verification, domain reasoning |
| `claude-haiku-4-5-20251001` | Fast tasks (search, classification) |

Set `ANTHROPIC_API_KEY` in `.env`.

### Ollama (local embeddings only)

```bash
ollama pull nomic-embed-text
```

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate

# Recommended: exact pinned versions
pip install -r requirements-lock.txt

# Or: minimum version bounds
# pip install -r requirements.txt

# Install Playwright browsers (required for AI QA browser verification)
.venv/bin/playwright install chromium
```

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Key `.env` variables:

```
ANTHROPIC_API_KEY=sk-ant-...
AUTOMATION_CODEBASE_PATH=/path/to/aupost-test-automation
BACKEND_CODE_PATH=/path/to/shopify-australia-post-app
FRONTEND_CODE_PATH=/path/to/shopify-au-post-web-client
SHOPIFY_ACTIONS_PATH="/path/to/shopify-actions "   # trailing space is intentional
TRELLO_API_KEY=...
TRELLO_TOKEN=...
TRELLO_BOARD_ID=PWKHwiCI
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL=C09F65XF4ER
EPARCEL_SHEETS_ID=...
MYPOST_SHEETS_ID=...
GOOGLE_CREDENTIALS_PATH=./credentials.json
```

---

## Ingest Knowledge Base

Run once before first use, and after documentation or codebase updates:

```bash
# Full rebuild (all sources)
python -m ingest.run_ingest

# Partial — specific sources only (additive, no clear)
python -m ingest.run_ingest --sources pluginhive_docs
python -m ingest.run_ingest --sources pluginhive_seeds
python -m ingest.run_ingest --sources sheets
python -m ingest.run_ingest --sources codebase
python -m ingest.run_ingest --sources wiki
python -m ingest.run_ingest --sources app
python -m ingest.run_ingest --sources aupost_api
python -m ingest.run_ingest --sources shopify_actions
```

### Knowledge Sources

| Source key | What it indexes |
|---|---|
| `pluginhive_docs` | Official PluginHive AU Post app documentation |
| `pluginhive_seeds` | PluginHive knowledge base and guide pages (web scrape) |
| `sheets` | eParcel + MyPost Business test cases from Google Sheets |
| `codebase` | Playwright TypeScript automation POM + specs + backend/frontend code |
| `wiki` | Internal AU Post wiki |
| `app` | Live AU Post app UI knowledge |
| `aupost_api` | Australia Post REST API — service codes, request/response fields, errors |
| `shopify_actions` | Shopify Admin API bulk order/product creation tool |

### ChromaDB Collections

| Collection | Content |
|---|---|
| `aupost_knowledge` | Domain docs, API docs, test cases, wiki, app knowledge |
| `aupost_code_knowledge` | Automation POM + specs, backend code, frontend code |

---

## Run Pipeline Dashboard

```bash
streamlit run ui/pipeline_dashboard.py
```

Open **http://localhost:8501** in your browser.

The dashboard provides tabs for:
- Validate AC (generate + review User Story + Acceptance Criteria)
- AI QA Verifier (browser-based scenario verification)
- TC Publisher (Trello comment + Google Sheets CSV)
- Bug Reporter
- Handoff Docs (Support Guide + Business Brief)
- QA Sign-Off

## Run Domain Expert Chat

```bash
streamlit run ui/chat_app.py
```

## Run API Server

```bash
uvicorn api.server:app --port 8000
```

API docs: **http://localhost:8000/docs**

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How does label generation work in eParcel?"}'
```

---

## Run Tests

```bash
# All tests (no Ollama required)
pytest tests/ --ignore=tests/test_vectorstore.py -v

# With Ollama running (includes vector store tests)
pytest tests/ -v
```

---

## Project Structure

```
AUPostDomainExpert/
├── ingest/                    # Knowledge base loaders
│   ├── run_ingest.py          # Master ingestion runner
│   ├── web_scraper.py         # PluginHive docs web scrape
│   ├── codebase_loader.py     # Automation + backend/frontend code
│   ├── sheets_loader.py       # Google Sheets test cases (eParcel + MyPost)
│   ├── aupost_api.py          # AU Post REST API knowledge
│   ├── pluginhive_app_docs.py # PluginHive official docs
│   ├── app_navigator.py       # Live app UI knowledge capture
│   ├── wiki_loader.py         # Internal wiki loader
│   └── pdf_loader.py          # PDF test case loader
├── pipeline/                  # QA pipeline modules
│   ├── smart_ac_verifier.py   # Agentic AI QA browser verifier
│   ├── card_processor.py      # AC/TC generation (LLM prompts + review)
│   ├── handoff_docs.py        # Support guide + business brief generator
│   ├── trello_client.py       # Trello REST API wrapper
│   ├── slack_client.py        # Slack messaging helpers
│   ├── bug_tracker.py         # Bug draft + Trello Backlog creation
│   ├── order_creator.py       # Shopify order creation for test data
│   ├── automation_writer.py   # Playwright automation code generation
│   ├── sheets_writer.py       # Google Sheets TC publishing
│   └── rag_updater.py         # ChromaDB upsert for approved cards
├── rag/                       # RAG pipeline
│   ├── vectorstore.py         # ChromaDB operations
│   ├── code_indexer.py        # Code knowledge indexing + stats
│   ├── prompts.py             # Domain expert persona prompts
│   └── chain.py               # Conversational RAG chain
├── skills/                    # Claude Code / Claude app skills (14 total)
│   ├── aupost-domain-core/
│   ├── aupost-ac-writer-reviewer/
│   ├── aupost-ai-qa-browser/
│   ├── aupost-ai-qa-testcase-prep/
│   ├── aupost-dashboard-tc-publisher/
│   ├── aupost-automation-writer/
│   ├── aupost-bug/
│   ├── aupost-handoff-docs/
│   ├── aupost-knowledge-maintainer/
│   ├── aupost-rag-sync/
│   ├── aupost-shopify-store-actions/
│   ├── aupost-signoff-message/
│   ├── aupost-slack-operator/
│   └── aupost-trello-operator/
├── ui/
│   ├── pipeline_dashboard.py  # Main Streamlit pipeline dashboard
│   └── chat_app.py            # Domain expert chat UI
├── api/
│   └── server.py              # FastAPI REST API
├── tests/                     # Pytest test suite
├── data/
│   ├── chroma_db/             # Persisted vector store (gitignored)
│   ├── handoff_docs/          # Generated support guides + business briefs
│   └── ai_qa_locator_traces/  # AI QA browser locator evidence per card
├── config.py                  # All env-driven settings
├── CLAUDE.md                  # Session context for Claude Code
└── requirements.txt           # Python dependencies
```

---

## Skills (Claude Code / Claude App)

Use these skills via the `Skill` tool in Claude Code or the Claude app.
All 14 skills are in `skills/` and auto-discovered by Claude Code.

| Skill | When to Use |
|---|---|
| `aupost-domain-core` | Any AU Post question — domain context, exact locators, app routes |
| `aupost-ac-writer-reviewer` | Write or review Acceptance Criteria for a Trello card |
| `aupost-trello-operator` | Read/update Trello cards, move cards between lists |
| `aupost-ai-qa-browser` | Run AI QA browser verification against the live app |
| `aupost-ai-qa-testcase-prep` | Generate detailed browser-executable test cases |
| `aupost-dashboard-tc-publisher` | Generate Trello QA comment + Google Sheets CSV rows |
| `aupost-automation-writer` | Write Playwright TypeScript specs for AU Post / MyPost |
| `aupost-bug` | Log a bug with severity guide, duplicate check, Backlog creation |
| `aupost-handoff-docs` | Generate Support Guide or Business Brief for a feature |
| `aupost-knowledge-maintainer` | Update ChromaDB knowledge after a card cycle |
| `aupost-rag-sync` | Re-ingest RAG sources — partial or full rebuild |
| `aupost-signoff-message` | Compose and send QA sign-off messages |
| `aupost-slack-operator` | Send Slack messages, post reports, DM teammates |
| `aupost-shopify-store-actions` | Create/update/delete Shopify products and orders via Admin API |

---

## Account Types

| Feature | eParcel | MyPost Business |
|---|---|---|
| Domestic shipping | ✅ | ✅ |
| International shipping | ✅ | ❌ |
| Extra Cover max | $5,000 AUD | $1,000 AUD |
| Dangerous Goods | ✅ (domestic only) | ❌ |
| Service codes | T28 (Parcel Post), E86J (Express Post) | Standard, Express |
