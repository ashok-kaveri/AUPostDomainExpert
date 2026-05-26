---
name: aupost-domain-core
description: Use when working inside the AUPostDomainExpert project and the user asks anything about the PluginHive Australia Post Shopify app, AU Post QA domain, app flows, eParcel/MyPost Business behavior, AU Post REST API, project architecture, local RAG/code/wiki knowledge, or wants research-backed answers. This is the shared domain/research core for AC, TC, AI QA, automation, handoff, and support tasks.
---

# AU Post Domain Core

Use this skill as the shared knowledge and research layer for the AUPostDomainExpert project.

It should make Codex/Claude behave like the project Domain Expert:

- know the AU Post Shopify app architecture (eParcel + MyPost Business account types)
- understand dashboard pipeline stages
- use local project knowledge before guessing
- browse official/current sources when local knowledge is missing or stale
- cite where facts came from
- feed research-backed conclusions into US/AC, TC, AI QA, automation, and handoff work

## First Reads

Always start with:

1. `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/CLAUDE.md`
2. `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-domain-core/references/research_workflow.md`

Then read only the project files directly relevant to the task.

## Two Account Types — Core Knowledge

### eParcel
- Higher-volume merchants; domestic + international shipping
- Extra Cover (insurance) up to **$5,000 AUD**
- Supports Dangerous Goods (domestic only)
- Services: Parcel Post (T28), Express Post (E86J), International Economy (PLT)

### MyPost Business
- Smaller-volume merchants; **domestic only**
- Extra Cover up to **$1,000 AUD**
- No Dangerous Goods support
- Services: Standard, Express

## What This Skill Covers

Use for questions or tasks about:

- AU Post Shopify app behavior (eParcel and MyPost Business)
- PluginHive app UI flows
- Shopify admin vs app iframe navigation
- Manual label generation (Generate Packages → Get Shipping Rates → Generate Label)
- SideDock options: Request Signature?, Authority to Leave, Insure package, Safe Drop, Dangerous Goods
- Order Summary page: Print Documents, Download Documents ZIP, Cancel Label, Return Label
- AU Post REST API fields: service codes, options.signature_on_delivery, options.authority_to_leave, options.extra_cover.amount, items[0].product_id, trackingNumbers[0]
- Shipping page tabs: All | Pending | Label Generated | Manifest Completed | Returns
- Settings page (/setting route — SINGULAR): Account Settings, Packaging, Rates, Documents/Labels, Additional Settings, International Shipping, Pickup Settings
- Pickup scheduling flow
- Return labels (Way A from app, Way B from Shopify admin)
- Rates Log (/rateslog): View Logs dialog with Request/Response textareas
- Products config (/products): dimensions, Is Signature Needed dropdown, Declared Value, Is Dangerous Goods checkbox
- Manifest flow
- eParcel vs MyPost Business feature differences
- generated AC/TC correctness
- AI QA evidence strategy
- automation/POM/spec patterns
- support/business handoff facts

## App Routes (exact paths)
- Shipping    → /apps/aupost-qa/shopify
- Settings    → /apps/aupost-qa/setting  (SINGULAR — not "settings")
- Products    → /apps/aupost-qa/products
- Pickup      → /apps/aupost-qa/pickup
- Rates Log   → /apps/aupost-qa/rateslog
- FAQ         → /apps/aupost-qa/faq
- Manifest    → /apps/aupost-qa/manifest
- App Guide   → /apps/aupost-qa/app-guide

## Iframe Selector
AU Post app iframe: `iframe[src*="qa-aupost.pluginhive.io"], iframe[src*="pluginhive.io"], iframe[src*="aupost"]`
(NOT iframe[name="app-iframe"] — that is FedEx's selector)

## Shopify More Actions — EXACT link names
- Manual label: "AU Post Generate Label" (role=link on page)
- Return label: "Au Post Return Label" (role=link on page)

## SideDock EXACT Checkbox Names (in iframe)
- Signature: checkbox "Request Signature?"
- ATL: checkbox "Authority to Leave"
- Insurance: checkbox "Insure package" → "Insurance Details" dialog → spinbutton "Declared Value"
- Dangerous Goods: look for dangerous goods related checkbox

## Research Order

1. `CLAUDE.md` and local skills
2. local project files
3. automation repo files under `AUTOMATION_CODEBASE_PATH` (`/Users/madan/Documents/AU_Post/aupost-test-automation`)
4. local wiki (`AUPOST_WIKI`: `/Users/madan/Documents/aupost-wiki`) and Chroma RAG
5. official/current web sources when needed

Browse the web when:
- local knowledge does not answer the question
- AU Post/Shopify/PluginHive rules may have changed
- a linked PR, docs page, or issue is referenced

For web research, prefer:
- Australia Post developer documentation
- PluginHive docs/help pages for AU Post
- Official Shopify docs

## Answer Style

For Q&A:
- answer directly
- cite local/project source and web source when used
- separate known fact from inference

## Relationship To Other Skills

Other AU Post skills use this skill's research posture:

- `aupost-trello-operator`: fetch real card/list/comments/members first
- `aupost-ac-writer-reviewer`: research first, generate/review US + AC, Trello comment only
- `aupost-dashboard-tc-publisher`: generate dashboard TCs, compact Trello comment, positive-only CSV rows for `Ai` tab
- `aupost-ai-qa-testcase-prep`: create detailed AI QA executable TCs for browser verification
- `aupost-ai-qa-browser`: verify TCs in Chrome with evidence, cleanup, locator trace handoff
- `aupost-automation-writer`: use reviewed TCs + AI QA evidence/locator traces to write Playwright automation
- `aupost-bug`: format QA-found bugs, check Backlog duplicates, create Trello Backlog cards
- `aupost-signoff-message`: fetch release/list cards, ask for Backlog links, prepare QA sign-off, send to Slack after QA confirms
- `aupost-handoff-docs`: generate Support Guide and/or Business Brief PDFs from approved cards
- `aupost-slack-operator`: search users/channels, read messages, send DMs/channel posts when asked
- `aupost-rag-sync`: pull latest and safely sync/reindex backend, frontend, automation, wiki knowledge
- `aupost-knowledge-maintainer`: after the card cycle, update approved-card RAG, QA feedback, outdated durable rules

Normal card-cycle order:
```text
Trello card/list/comments
  -> domain research
  -> US + AC comment
  -> dashboard TCs + Trello/CSV publish package
  -> AI QA browser verification + locator trace
  -> bug follow-up if needed
  -> automation writer
  -> sign-off message
  -> handoff docs
  -> RAG sync if source repos/docs changed
  -> knowledge maintainer
```

## Do Not

- Do not invent AU Post API limits or account-type rules.
- Do not assume MyPost Business supports international or Dangerous Goods.
- Do not assume local RAG is complete.
- Do not update Trello, Slack, Sheets, or repo files unless the user asks.
- Do not browse for secrets or private data.
