---
name: aupost-handoff-docs
description: Use when working inside the AUPostDomainExpert project after cards are approved and the user wants professional release handoff documents: Support Guide, Business Brief, or both. Generated from approved US/AC, TCs, AI QA evidence, release/card metadata, and member ownership. Covers both eParcel and MyPost Business where relevant.
---

# AU Post Handoff Docs

Use this skill to generate professional release handoff documents for AU Post Shopify app cards.

## First Reads (REQUIRED — do not skip)

1. Read the handoff doc formats reference — it contains the complete app navigation map, exact button names, step-by-step templates, and document formats:
   `/Users/madan/Documents/AU_Post_DomainExpert/AUPostDomainExpert/skills/aupost-handoff-docs/references/handoff_doc_formats.md`
2. Use `aupost-trello-operator` to fetch approved card content (US/AC, TCs, comments) if a card ID/URL is provided.

**CRITICAL RULE**: For the "Where to Find" and "Walkthrough" sections, use ONLY the exact routes, button names, and step sequences from the `APP NAVIGATION MAP` and `NAVIGATION STEP TEMPLATES` in the reference file. Do NOT infer navigation paths from AC text — the AC rarely describes exact UI paths.

## Document Selection

Generate based on user request:
- "support guide", "support doc", "demo doc" → Support Guide only
- "business brief", "business doc", "stakeholder doc" → Business Brief only
- "handoff docs", "both docs" → both documents
- If unclear, ask: Support Guide, Business Brief, or both?

## Document Types

| Document | Audience | When To Generate |
|---|---|---|
| Support Guide | Support team, demo team, PluginHive internal | After card approved + QA signed off |
| Business Brief | Non-technical stakeholders, business owners | When requested |
| Both | All stakeholders | When user asks for full package |

## Input Needed

- Approved card(s): title, description, US/AC comment, TC comment, AI QA evidence
- Account type(s) covered: eParcel / MyPost Business / Both
- Release version/name (from Trello list name or card)
- Developer name(s) and QA name(s) from card members
- AI QA verdict summary

If some inputs are missing, generate a useful draft but mark unknown fields clearly. Do not invent ownership, release numbers, or unsupported limitations.

## Support Guide Sections

1. **Release Details** — Feature Reference, Trello card URL, Release, Approved, Developed by, Tested by
2. **Feature Summary** — What changed / what was added (plain English)
3. **Account Type Coverage** — eParcel / MyPost Business / Both — always be explicit
4. **Toggles & Prerequisites** — whether any toggle is needed; "None required" if not
5. **Where to Find** — exact app path from the navigation map in the reference file
6. **Walkthrough** — step-by-step guide using exact button/link names from the reference file
7. **Expected Behaviour** — what support should observe (status badge, JSON field, UI change)
8. **Business-Safe Explanation** — plain English for merchant-facing communication
9. **Q&A** — common questions support may face
10. **Known Limitations** — eParcel vs MyPost Business differences, any known gaps
11. **References** — Trello card URL, PluginHive docs links

## Business Brief Sections

1. **Feature Headline** — one-line feature name
2. **The Problem** — 2-3 sentences on what was broken/missing
3. **What's New** — 3-5 bullet points (action verbs, no jargon)
4. **Who Benefits** — 2-3 merchant scenarios
5. **Why It Matters** — 2-3 sentences on business value
6. **Availability** — which account type + whether setup is needed

## Business Brief Rules

- Max ~400 words total
- Plain English only — no API, JSON, iframe, regex, backend, frontend
- No developer/tester attribution
- No QA notes, no test counts
- Highlight eParcel-only vs MyPost Business-only vs both
- No toggle detail unless merchant must act

## Account Type — Key Limits to Always State Correctly

- Extra Cover (Insurance): eParcel max **$5,000 AUD** | MyPost Business max **$1,000 AUD**
- International shipping: **eParcel only** (MyPost Business is domestic only)
- Dangerous Goods: **eParcel domestic only** (not MyPost Business, not international)

## PDF Rendering

Use `pipeline.handoff_docs.render_pdf_bytes` if PDF export is requested.

## Final Response

Return:
- Support Guide (markdown)
- Business Brief (markdown, if requested)
- PDF export note if requested
- Which account types are covered
- Any fields left as "Unknown" due to missing input
