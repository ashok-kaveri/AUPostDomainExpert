# AU Post Domain Expert — Onboarding

An AI-powered QA pipeline for the PluginHive **Australia Post Shopify App**. It takes a Trello
release card and carries it to shipped: acceptance criteria, test cases, verification against the
live app, automation, sign-off, and release documents.

This guide gets you productive. [README.md](README.md) is the command reference once you are.

---

## 1. The one-paragraph version

A Trello release card goes in. Claude writes the acceptance criteria and test cases from that card
plus real context — the codebase, AU Post API docs, past approved cards, all indexed into a local
vector store. An agentic browser layer then verifies those test cases against the live AU Post app
inside Shopify admin, and out come automation code, a QA sign-off message, and release documents.

The domain fact that shapes everything: **Australia Post has two account types**, and they are not
interchangeable. Almost every scenario has to say which one it means.

---

## 2. The two account types

This is the first thing to internalise. Getting it wrong invalidates a test.

| | **eParcel** | **MyPost Business** |
|---|---|---|
| Volume | Higher-volume merchants | Smaller businesses |
| Shipping | Domestic **and** international | Domestic only |
| Extra Cover | up to **$5,000 AUD** | up to **$1,000 AUD** |
| Dangerous goods | Supported, domestic only | Not supported |
| Services | Parcel Post, Express Post (+ Signature variants) | Standard, Express |

An international scenario is eParcel by definition. A dangerous-goods scenario is eParcel and
domestic. Never widen a MyPost Business case to international, and never write an Extra Cover
scenario without checking which ceiling applies.

---

## 3. Mental model

```
                     ┌──────────────────────────────┐
                     │   RAG knowledge base         │
                     │   (ChromaDB, local)          │
                     │   docs · AU Post API ·       │
                     │   codebase · approved cards  │
                     └──────────────┬───────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
   ┌─────────────────┐   ┌────────────────────┐   ┌──────────────────┐
   │ Domain Expert   │   │  Pipeline          │   │ Smart AC         │
   │ Chat            │   │  dashboard         │   │ Verifier         │
   │                 │   │  (9 tabs)          │   │                  │
   │ ui/chat_app.py  │   │  ui/pipeline_      │   │ drives the live  │
   │                 │   │  dashboard.py      │   │ app in Shopify   │
   └─────────────────┘   └────────────────────┘   └──────────────────┘
                                    │
                                    ▼
                  automation code · sign-off · release documents
```

### The dashboard tabs

`📝 User Story` · `🔀 Move Cards` · `✅ Validate Acceptance Criteria` · `🧪 Generate TestCases` ·
`🔍 AI QA Verifier` · `✍️ Write Automation Code` · `▶️ Run Automation` · `✅ Sign Off` ·
`📄 Generate Documents`

Note that writing and running automation are **separate tabs** here, unlike the sibling repos where
they are one.

---

## 4. Get it running

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
ollama pull nomic-embed-text        # embeddings run locally
cp .env.example .env                # then fill in keys and local repo paths
```

```bash
PYTHONPATH=. .venv/bin/streamlit run ui/pipeline_dashboard.py   # pipeline
PYTHONPATH=. .venv/bin/streamlit run ui/chat_app.py             # domain expert chat
uvicorn api.server:app --port 8000                              # optional REST API
pytest tests/ -v
```

`PYTHONPATH=.` is not optional — modules import each other as top-level packages.

Build the knowledge base before expecting good AC — see the ingest section in `README.md`. Without
the local repos indexed, AC quality falls off a cliff.

---

## 5. Where things live

```
ui/
  pipeline_dashboard.py     the 9-tab pipeline
  chat_app.py               domain expert chat
pipeline/
  smart_ac_verifier.py            agentic browser verification
  card_processor.py               AC writer + test case generator
  handoff_docs.py                 support guide / business brief + PDF renderer
  generate_release_support_guide.py
  generate_business_pitch.py · generate_detailed_report.py
  automation_writer.py · test_runner.py · test_writer/
  order_creator.py · product_creator.py
  trello_client.py · slack_client.py · sheets_writer.py
  bug_reporter.py · bug_tracker.py · qa_explorer.py · release_analyser.py
rag/          vectorstore.py · chain.py · code_indexer.py · prompts.py
ingest/       knowledge ingestion
api/          server.py — optional FastAPI wrapper
skills/       15 aupost-* Claude Code skills — the CLI half of the product
config.py     settings, env-driven
```

### The skills are half the product

`skills/` holds 15 Claude Code skills that do the same jobs from the terminal: `aupost-domain-core`,
`aupost-ac-writer-reviewer`, `aupost-ai-qa-testcase-prep`, `aupost-ai-qa-browser`,
`aupost-automation-writer`, `aupost-handoff-docs`, `aupost-toggle-enable-list`,
`aupost-signoff-message`, `aupost-bug`, `aupost-trello-operator`, `aupost-slack-operator`,
`aupost-shopify-store-actions`, `aupost-dashboard-tc-publisher`, `aupost-rag-sync`,
`aupost-knowledge-maintainer`.

They encode house rules — read the `SKILL.md` before hand-rolling the same job. `aupost-handoff-docs`
is the most rule-dense.

---

## 6. Things that will bite you

**The iframe selector is not FedEx's.** The AU Post app is embedded in Shopify admin, but it is
matched on `iframe[src*="qa-aupost.pluginhive.io"], iframe[src*="pluginhive.io"], iframe[src*="aupost"]`
— **not** `iframe[name="app-iframe"]`, which is the FedEx app's selector. App navigation (Shipping,
Settings, PickUp, Products, FAQ, Rates Log) is *inside* the iframe; Shopify's own Orders and Products
are *outside*. Search the iframe first for app nav, the full page first for Shopify nav.

**Settings is singular.** The route is `/apps/aupost-qa/setting`, not `/setting**s**`. The other exact
routes: `shopify` (Shipping), `products`, `pickup`, `rateslog`, `faq`, `manifest`, `app-guide`.

**Cubic weight decides the price.** `cubic_weight = L × W × H ÷ 4000` (cm), and AU Post charges the
**higher** of actual and cubic weight. A pricing scenario that ignores cubic weight is wrong for
anything bulky and light.

**Article ID is the tracking number.** AU Post calls it an Article ID — `trackingNumbers[0]`, or
`items[0].article_id` at item level. Don't call it a tracking number in a request-level assertion.

**Manifests are a real stage here.** The Shipping grid has five tabs — All, Pending, Label Generated,
Manifest Completed, Returns — and there's a dedicated `/manifest` route. Manifest completion is part
of the AU Post flow and has no FedEx equivalent, so it's easy to leave out of a test plan.

**Rate logs are JSON, REST API only.** Don't expect the FedEx-style document/ZIP paths.

**The verifier is still called Smart AC Verifier here.** The FedEx sibling renamed the same component
to "AI QA Agent". Same idea, different name — don't get confused reading across the two repos.

---

## 7. Housekeeping worth knowing

- **`CLAUDE.md` and `AGENTS.md` are near-duplicates** — the same project context for Claude and for
  Codex. Update both, or they drift.
- `CLAUDE.md` carries the detailed UI architecture: exact routes, the SideDock, both return-label
  entry points, product config, and the request JSON field paths used for verification. It is the
  reference to reach for when writing a test, not the README.

---

## 8. First week suggestions

1. Read section 2 of this guide again, then `CLAUDE.md`'s account-types section. Everything downstream
   depends on getting eParcel vs MyPost Business right.
2. Open the Domain Expert chat and ask it something you already know the answer to — the cheapest way
   to check your index is actually populated.
3. Walk **Validate Acceptance Criteria → Generate TestCases** on a real past release list, and compare
   the output against the Trello card.
4. Read one skill end to end. `aupost-handoff-docs` is the best single window into the house rules.
5. Only then run the AI QA Verifier on a single test case, reading `pipeline/smart_ac_verifier.py` and
   `CLAUDE.md`'s UI architecture section alongside it.
