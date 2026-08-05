from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

import config
from pipeline.trello_client import TrelloCard, TrelloClient

logger = logging.getLogger(__name__)


@dataclass
class ReleaseCard:
    index: int
    card_id: str
    code: str
    ticket: str
    title: str
    card_name: str
    card_url: str
    desc: str
    comments: list[str]
    status: str
    confidence: str
    risk: str
    root_cause: str
    solution: str


@dataclass
class SupportSection:
    feature_summary: str
    release_details: list[str]
    where_to_find: list[str]
    walkthrough: list[str]
    expected_behaviour: list[str]
    troubleshooting: list[dict[str, str]]
    account_coverage: str = ""
    doc_type: str = ""
    known_limitations: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.known_limitations is None:
            self.known_limitations = []


def _extract_field(text: str, label: str) -> str:
    match = re.search(rf"\*\*{re.escape(label)}\*\*:\s*(.+)", text)
    return match.group(1).strip() if match else ""


def _extract_qa_comment(comments: list[str]) -> str:
    for comment in comments:
        if "QA Test Cases" in comment:
            return comment
    return comments[0] if comments else ""


def _extract_impl_comment(comments: list[str]) -> str:
    for comment in reversed(comments):
        if "Implementation committed" in comment or "PR opened" in comment or "Partial implementation" in comment:
            return comment
    return comments[-1] if comments else ""


_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF⬀-⯿️]+"
)


def _strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", text)


def _clean_inline(text: str) -> str:
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    text = text.replace("`", "")
    text = text.replace("•", "-")
    text = _strip_emoji(text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _parse_card(card: TrelloCard, index: int) -> ReleaseCard:
    raw_name = card.name.strip()
    code_match = re.search(r"(AI-\d+|C-\d+)", raw_name)
    ticket_match = re.search(r"(\#\d+(?:,\s*\#\d+)*)", raw_name)

    title = raw_name
    title = re.sub(r"^From SL:\s*", "", title)
    title = _strip_emoji(title).strip()
    title = re.sub(r"^(AI-\d+|C-\d+)\s*[—\-\|:]\s*", "", title).strip()
    title = re.sub(r"\s*\[[^\]]+\]\s*$", "", title).strip()

    desc = card.desc or ""
    short = _card_ref(card.url or "")
    return ReleaseCard(
        index=index,
        card_id=card.id,
        code=(code_match.group(1) if code_match else f"CARD-{index}"),
        ticket=(ticket_match.group(1) if ticket_match else ""),
        title=title,
        card_name=raw_name,
        card_url=(f"https://trello.com/c/{short}" if short else (card.url or "")),
        desc=desc,
        comments=card.comments or [],
        status=_clean_inline(_extract_field(desc, "Status")) or "In progress",
        confidence=_clean_inline(_extract_field(desc, "Confidence")) or "Not stated",
        risk=_clean_inline(_extract_field(desc, "Risk Level")) or "Not stated",
        root_cause=_clean_inline(_extract_field(desc, "Root Cause")) or _clean_inline(_extract_field(desc, "Root Cause / Gap")),
        solution=_clean_inline(_extract_field(desc, "Solution")) or _clean_inline(_extract_field(desc, "Suggested Approach")),
    )


def _llm() -> ChatAnthropic:
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return ChatAnthropic(
        model=config.CLAUDE_HAIKU_MODEL,
        api_key=config.ANTHROPIC_API_KEY,
        temperature=0.2,
        max_tokens=2200,
    )


def _build_prompt(card: ReleaseCard) -> str:
    return f"""You are preparing an internal support guide for the PluginHive Australia Post Shopify App.

Write JSON only. No markdown fences. Be CRISP — this is a one-page-per-card quick reference,
not a design document. Short sentences. No filler. No restating the same point twice.

Return this exact schema:
{{
  "feature_summary": "50-80 words max — what changed and why support cares",
  "doc_type": "Bug fix | New feature | Enhancement",
  "account_coverage": "one short line: eParcel / MyPost Business / StarTrack / Both, and domestic vs international",
  "release_details": ["3-4 very short bullets"],
  "where_to_find": ["2-3 short bullets"],
  "walkthrough": ["4-6 short steps without the numbers"],
  "expected_behaviour": ["3-4 short bullets"]
}}

Rules:
- Use facts from the card content and comments only. Do not invent UI, toggles, or ownership.
- If a QA scenario is marked "fail", say so plainly in expected_behaviour.
- Mention partial implementation if the comments say it is partial.
- "where_to_find" must use AU Post app navigation language and exact route names.
- "walkthrough" should be practical for support or QA demo use.
- Avoid code jargon, file paths, and internal class names unless essential for support.

CARD NAME:
{card.card_name}

CARD URL:
{card.card_url}

STATUS:
{card.status}

CONFIDENCE:
{card.confidence}

RISK:
{card.risk}

ROOT CAUSE:
{card.root_cause}

SOLUTION / APPROACH:
{card.solution}

CARD DESCRIPTION:
{card.desc[:9000]}

QA COMMENT:
{_extract_qa_comment(card.comments)[:7000]}

IMPLEMENTATION COMMENT:
{_extract_impl_comment(card.comments)[:3000]}
"""


def _fallback_section(card: ReleaseCard) -> SupportSection:
    qa_comment = _clean_inline(_extract_qa_comment(card.comments))
    impl_comment = _clean_inline(_extract_impl_comment(card.comments))
    where = ["Use the card title and QA notes to navigate to the affected AU Post app area."]
    if "sample label" in card.title.lower():
        where = [
            "Navigate Home -> App Guide -> Label Generation Guide.",
            "Select the carrier account to test, then use Generate Label from that guide flow.",
            "Use a MyPost or eParcel test account with valid credentials before retrying.",
        ]
    elif "unmanifested" in card.title.lower():
        where = [
            "Open Shipping in the AU Post app.",
            "Open the Label Generated view to review orders that already have labels but are still waiting for manifesting.",
        ]
    elif "boxes" in card.title.lower():
        where = [
            "Open Settings in the AU Post app.",
            "Go to Packaging Configuration where carrier boxes are managed.",
        ]
    elif "weight" in card.title.lower():
        where = [
            "Open Products in the AU Post app.",
            "Search for the product and open its configuration panel.",
        ]
    elif "tls" in card.title.lower():
        where = [
            "This is a backend reliability change with no direct UI switch.",
            "Verify the change through rate, label, tracking, and validation flows.",
        ]
    elif "ccs" in card.title.lower():
        where = [
            "Open the AU Post app home page or dashboard after store load.",
            "Look for the carrier-calculated-shipping banner state.",
        ]

    release_details = [
        f"Status: {card.status}",
        f"Risk: {card.risk}",
        f"Confidence from analysis: {card.confidence}",
    ]
    if card.root_cause:
        release_details.append(f"Root cause: {card.root_cause[:180]}")
    if card.solution:
        release_details.append(f"Fix direction: {card.solution[:180]}")

    if "unmanifested" in card.title.lower():
        return SupportSection(
            feature_summary=(
                "A simpler order view is being added so support and merchants can quickly identify orders "
                "that already have labels generated but are still waiting to be manifested."
            ),
            release_details=[
                f"Status: {card.status}",
                "Purpose: make it easier to find label-generated orders that still need manifesting.",
                "Support impact: reduces the effort needed to review unlodged shipments in bulk.",
            ],
            where_to_find=[
                "Open Shipping in the AU Post app.",
                "Go to the Label Generated area to review orders that are manifest pending.",
            ],
            walkthrough=[
                "Open Shipping in the AU Post app.",
                "Go to the Label Generated view.",
                "Review orders that already have labels but are still waiting for manifest.",
                "Use that view to confirm which orders are ready for the next manifest action.",
            ],
            expected_behaviour=[
                "Label-generated orders that are still manifest pending should be easy to identify in one place.",
                "Support should be able to review these orders without manually checking each shipment one by one.",
                "The view should help separate already-manifested orders from ones still waiting for manifest.",
            ],
            troubleshooting=[
                {"question": "What should support look for first?", "answer": "Confirm the order already has a generated label and then check whether it is still waiting for manifest."},
                {"question": "Why would a merchant use this view?", "answer": "It helps them quickly find shipments that are ready for the next manifest step."},
                {"question": "When should this be escalated?", "answer": "Escalate if label-generated orders are missing from the view or if already-manifested orders are mixed into the pending list."},
            ],
        )

    if "pre-defined au post boxes deleted" in card.title.lower() or "restore option" in card.title.lower():
        return SupportSection(
            feature_summary=(
                "A Restore AU Post Defaults button is added in Box Packaging Settings. "
                "When this button is clicked, all AU Post boxes are restored."
            ),
            release_details=[
                f"Status: {card.status}",
                "Purpose: make it easy to bring back deleted AU Post default boxes.",
                "Support impact: gives merchants a quick recovery option in packaging settings.",
            ],
            where_to_find=[
                "Open Settings in the AU Post app.",
                "Go to Box Packaging Settings.",
                "Look for the Restore AU Post Defaults button.",
            ],
            walkthrough=[
                "Open Settings in the AU Post app.",
                "Go to Box Packaging Settings.",
                "Click the Restore AU Post Defaults button.",
                "Confirm that the AU Post boxes appear again in the packaging list.",
            ],
            expected_behaviour=[
                "Clicking Restore AU Post Defaults should restore all AU Post boxes.",
                "Merchants should be able to see the restored AU Post boxes again in packaging settings.",
                "This should make it easier to recover default boxes without manual re-entry.",
            ],
            troubleshooting=[
                {"question": "Where can support find this option?", "answer": "In Box Packaging Settings inside the AU Post app."},
                {"question": "What should happen after clicking the button?", "answer": "The AU Post default boxes should be restored and shown again in the packaging list."},
                {"question": "When should this be escalated?", "answer": "Escalate if the button is missing or if the AU Post boxes do not return after using it."},
            ],
        )

    if "weight field greyed out" in card.title.lower() or "non-editable on product" in card.title.lower():
        return SupportSection(
            feature_summary=(
                "Earlier, the product weight was fully controlled by Shopify, so the field was greyed out and any updates made "
                "in the app could get overwritten. If Shopify sent a weight of 0, it could also lead to label failures. "
                "With the latest fix, the system now correctly uses a valid weight from the synced Shopify value, a configured "
                "default weight, or a manually overridden value."
            ),
            release_details=[
                f"Status: {card.status}",
                "Purpose: prevent label failures caused by missing, zero, or overwritten product weight.",
                "Support impact: ensures the system can use a valid weight even when the Shopify value is not usable.",
            ],
            where_to_find=[
                "Open Products in the AU Post app.",
                "Search for the product and open its product settings page.",
                "Review the product weight shown in the app and compare it with the Shopify product weight if needed.",
            ],
            walkthrough=[
                "Open the product in Shopify and check the product or variant weight there first.",
                "Open the same product in the AU Post app.",
                "Confirm whether the Shopify weight is valid, missing, or set to 0.",
                "Verify that label generation now uses a valid weight from the synced Shopify weight, a configured default weight, or a manual override.",
            ],
            expected_behaviour=[
                "The system should no longer rely only on an unusable Shopify weight when generating labels.",
                "If Shopify sends a missing or 0 weight, the system should use a valid default or overridden weight where available.",
                "Label generation should work properly even when the original Shopify weight is missing or 0.",
            ],
            troubleshooting=[
                {"question": "Why is the weight field greyed out?", "answer": "Because Shopify still controls the main synced product weight shown in the app."},
                {"question": "What changed with this fix?", "answer": "The system can now use the synced Shopify weight, a configured default weight, or a manually overridden value to keep label generation working."},
                {"question": "What should support check if a merchant still reports weight-related label issues?", "answer": "Check the Shopify weight first, then confirm whether a valid default or overridden weight is available for the product."},
            ],
        )

    return SupportSection(
        feature_summary=(card.root_cause or card.title)[:420],
        release_details=release_details[:5],
        where_to_find=where[:4],
        walkthrough=[
            "Confirm the store and account setup referenced in the Trello card.",
            "Navigate to the affected AU Post app area.",
            "Repeat the QA scenario captured on the card.",
            "Compare the observed result against the expected fixed behaviour.",
        ],
        expected_behaviour=[
            "The issue should reproduce on older logic and stop reproducing after the release fix.",
            "Support should see the outcome described in the approved QA scenario.",
            "If the old behaviour remains, capture store, order, and timing details before escalation.",
        ],
        troubleshooting=[
            {"question": "What should support check first?", "answer": "Confirm the store is on the intended release and the scenario matches the card prerequisites."},
            {"question": "When should this be escalated?", "answer": "Escalate if the old behaviour is still visible after prerequisites are met and the release is confirmed."},
            {"question": "What evidence helps most?", "answer": "Collect the merchant store, exact steps taken, screenshots, and any order or request identifiers."},
        ],
    )


def _manual_override_section(card: ReleaseCard) -> SupportSection | None:
    title = card.title.lower()
    if card.code == "AI-021" or "display rates request/response on slgp" in title:
        return SupportSection(
            feature_summary=(
                "The original SLGP or customer-account frontend rate-log view is no longer applicable because that "
                "frontend implementation has been removed. Rate logs are no longer shown in SLGP or in the customer-facing "
                "frontend view. The supported location for this information is now the dedicated Rates Log section, where "
                "new entries appear after the merchant fetches rates or refreshes rates."
            ),
            release_details=[
                f"Status: {card.status}",
                "Support impact: rate logs should now be checked only in Rates Log.",
                "Note: old SLGP or frontend rate-log expectations should not be used for validation.",
            ],
            where_to_find=[
                "Open the Rates Log section in the AU Post app.",
                "Use a flow that fetches rates or refreshes rates to create a new log entry.",
                "Review the latest request and response details from that Rates Log area.",
            ],
            walkthrough=[
                "Open the AU Post app and go to the Rates Log section.",
                "Run a flow that fetches rates or refreshes rates.",
                "Return to Rates Log and look for the newly created log entry.",
                "Open the entry and review the request and response details there.",
            ],
            expected_behaviour=[
                "Rate log should not be expected in the original SLGP view.",
                "Rate log should not be expected in the customer account frontend view.",
                "A new log entry should appear in Rates Log after fetching or refreshing rates.",
                "Support should use Rates Log as the single supported place to inspect rate request and response details.",
            ],
            troubleshooting=[
                {"question": "Why is the rate log missing from SLGP?", "answer": "That frontend implementation has been removed, so SLGP is no longer the supported place for rate logs."},
                {"question": "Where should support check rate request and response details now?", "answer": "Use the Rates Log section in the AU Post app."},
                {"question": "When should a new rate log entry appear?", "answer": "After the merchant fetches rates or refreshes rates."},
            ],
        )
    return None


def _generate_section(card: ReleaseCard) -> SupportSection:
    manual = _manual_override_section(card)
    if manual:
        return manual
    if os.getenv("SUPPORT_GUIDE_NO_LLM", "").lower() in {"1", "true", "yes"}:
        return _fallback_section(card)
    try:
        raw = _llm().invoke([HumanMessage(content=_build_prompt(card))]).content
        if not isinstance(raw, str):
            raw = str(raw)
        raw = raw.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        return _section_from_dict(data)
    except Exception as exc:
        logger.warning("Section generation fell back for %s: %s", card.code, exc)
        return _fallback_section(card)


def _section_from_dict(data: dict) -> SupportSection:
    """Build a SupportSection from a raw dict (LLM output or a curated JSON file)."""
    return SupportSection(
        feature_summary=_clean_inline(data["feature_summary"]),
        account_coverage=_clean_inline(data.get("account_coverage", "")),
        doc_type=_clean_inline(data.get("doc_type", "")),
        release_details=[_clean_inline(x) for x in data.get("release_details", [])][:5],
        where_to_find=[_clean_inline(x) for x in data.get("where_to_find", [])][:4],
        walkthrough=[_clean_inline(x) for x in data.get("walkthrough", [])][:6],
        expected_behaviour=[_clean_inline(x) for x in data.get("expected_behaviour", [])][:6],
        known_limitations=[_clean_inline(x) for x in data.get("known_limitations", [])][:4],
        troubleshooting=[
            {
                "question": _clean_inline(item.get("question", "")),
                "answer": _clean_inline(item.get("answer", "")),
            }
            for item in data.get("troubleshooting", [])[:3]
        ],
    )


def _build_release_cards(list_name: str) -> list[ReleaseCard]:
    trello = TrelloClient()
    lst = trello.get_list_by_name(list_name)
    if not lst:
        raise ValueError(f"Trello list not found: {list_name}")
    cards = trello.get_cards_in_list(lst.id)
    return [_parse_card(card, idx) for idx, card in enumerate(cards, start=1)]


def _card_ref(url_or_id: str) -> str:
    """Accept a full Trello URL or a bare short link / card id."""
    match = re.search(r"trello\.com/c/([A-Za-z0-9]+)", url_or_id)
    return match.group(1) if match else url_or_id.strip()


def _build_cards_from_refs(refs: list[str]) -> list[ReleaseCard]:
    trello = TrelloClient()
    out = []
    for idx, ref in enumerate(refs, start=1):
        card = trello.get_card(_card_ref(ref))
        out.append(_parse_card(card, idx))
    return out


def _pdf_deps():
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        return colors, A4, ParagraphStyle, getSampleStyleSheet, cm, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ModuleNotFoundError as exc:
        raise RuntimeError("reportlab is required. Install it in the project venv before running this generator.") from exc


def _resolve_sections(
    release_cards: list[ReleaseCard],
    sections_json: str | Path | None,
) -> list[tuple[ReleaseCard, SupportSection]]:
    curated: dict = {}
    if sections_json:
        curated = json.loads(Path(sections_json).expanduser().read_text(encoding="utf-8"))

    out = []
    for card in release_cards:
        raw = (
            curated.get(card.code)
            or curated.get(card.card_url)
            or curated.get(_card_ref(card.card_url))
        )
        out.append((card, _section_from_dict(raw) if raw else _generate_section(card)))
    return out


def generate_release_support_guide(
    *,
    list_name: str,
    output_path: str | Path,
    card_refs: list[str] | None = None,
    sections_json: str | Path | None = None,
) -> str:
    colors, A4, ParagraphStyle, getSampleStyleSheet, cm, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle = _pdf_deps()

    if card_refs:
        release_cards = _build_cards_from_refs(card_refs)
    else:
        release_cards = _build_release_cards(list_name)
    sections = _resolve_sections(release_cards, sections_json)

    out_path = Path(output_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()

    def _ps(name: str, **kw):
        parent = kw.pop("parent", styles["Normal"])
        return ParagraphStyle(name=name, parent=parent, **kw)

    BRAND_RED = colors.HexColor("#2563A8")
    DEEP_RED = colors.HexColor("#1B2D4F")
    GOLD = colors.HexColor("#5B8CC9")
    SOFT_BG = colors.HexColor("#EEF3FA")
    BORDER = colors.HexColor("#C8D6EA")
    BODY = colors.HexColor("#2C3E50")
    MUTED = colors.HexColor("#6B7E99")
    WHITE = colors.white

    title_style = _ps("Title", fontName="Helvetica-Bold", fontSize=28, leading=32, textColor=WHITE, alignment=1)
    sub_style = _ps("Sub", fontName="Helvetica", fontSize=12, leading=16, textColor=colors.HexColor("#F8EAE6"), alignment=1)
    cover_card_style = _ps("CoverCard", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=BODY)
    cover_desc_style = _ps("CoverDesc", fontName="Helvetica", fontSize=10, leading=13, textColor=MUTED)
    toc_head = _ps("TocHead", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=DEEP_RED)
    toc_body = _ps("TocBody", fontName="Helvetica", fontSize=10, leading=13, textColor=BODY)
    card_kicker = _ps("CardKicker", fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=BRAND_RED)
    card_title = _ps("CardTitle", fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=DEEP_RED)
    meta_label = _ps("MetaLabel", fontName="Helvetica-Bold", fontSize=8.5, leading=10, textColor=MUTED)
    meta_value = _ps("MetaValue", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=BODY)
    section_head = _ps("SectionHead", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=DEEP_RED, spaceAfter=4)
    body_style = _ps("Body", fontName="Helvetica", fontSize=9.4, leading=13, textColor=BODY, spaceAfter=4)
    bullet_style = _ps("Bullet", parent=body_style, leftIndent=14, bulletIndent=0, spaceAfter=3)
    qa_q_style = _ps("QaQ", fontName="Helvetica-Bold", fontSize=9.2, leading=12, textColor=DEEP_RED, spaceAfter=2)
    qa_a_style = _ps("QaA", fontName="Helvetica", fontSize=9, leading=12.5, textColor=BODY, spaceAfter=4)
    footer_style = _ps("Footer", fontName="Helvetica", fontSize=8, leading=10, textColor=MUTED, alignment=1)
    ref_style = _ps("Ref", fontName="Helvetica", fontSize=8.2, leading=11, textColor=MUTED, spaceAfter=2)

    release_name = list_name.replace(": Iteration backlog", "")
    today = dt.datetime.now().strftime("%B %d, %Y")

    from reportlab.platypus import Flowable, KeepTogether

    page_map: dict[str, int] = {}

    class PageMarker(Flowable):
        """Zero-height flowable that records which page a card section starts on."""

        def __init__(self, key: str):
            super().__init__()
            self.key = key
            self.width = 0
            self.height = 0

        def draw(self):
            page_map[self.key] = self.canv.getPageNumber()

    def _build_story(page_lookup: dict[str, int]) -> list:
        story = []

        cover = Table(
            [
                [Paragraph("PLUGINHIVE", sub_style)],
                [Paragraph("Australia Post Shopify App", sub_style)],
                [Paragraph("SUPPORT GUIDE", title_style)],
                [Paragraph(f"{release_name}<br/>Story Card Package<br/>{today}", sub_style)],
            ],
            colWidths=[17 * cm],
        )
        cover.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_RED),
            ("BOX", (0, 0), (-1, -1), 0, BRAND_RED),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(Spacer(1, 4.0 * cm))
        story.append(cover)

        # ---- Index page --------------------------------------------------
        story.append(PageBreak())
        story.append(Paragraph("Index", card_title))
        story.append(Paragraph(f"{release_name} &middot; {len(sections)} story cards &middot; {today}", body_style))
        story.append(Spacer(1, 0.35 * cm))

        index_rows = [[
            Paragraph("STORY CARD", toc_head),
            Paragraph("TICKET", toc_head),
            Paragraph("TITLE", toc_head),
            Paragraph("PAGE", toc_head),
        ]]
        for card, _section in sections:
            index_rows.append([
                Paragraph(card.code, toc_body),
                Paragraph(card.ticket or "-", toc_body),
                Paragraph(_clean_inline(card.title), toc_body),
                Paragraph(str(page_lookup.get(card.code, "")), toc_body),
            ])
        index_table = Table(index_rows, colWidths=[2.4 * cm, 2.4 * cm, 10.4 * cm, 1.8 * cm], repeatRows=1)
        index_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SOFT_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), DEEP_RED),
            ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(index_table)

        # ---- One crisp section per card ----------------------------------
        for card, section in sections:
            story.append(PageBreak())
            story.append(PageMarker(card.code))
            story.append(Paragraph("SUPPORT GUIDE", card_kicker))
            story.append(Spacer(1, 0.1 * cm))
            story.append(Paragraph(card.code, card_title))
            story.append(Paragraph(f"<b>{_clean_inline(card.title)}</b>", body_style))
            story.append(Paragraph(f"Trello: {card.card_url}", ref_style))
            story.append(Spacer(1, 0.15 * cm))

            meta_rows = [
                [
                    Paragraph("TICKET", meta_label),
                    Paragraph("RELEASE", meta_label),
                    Paragraph("TYPE", meta_label),
                    Paragraph("ACCOUNT TYPE", meta_label),
                ],
                [
                    Paragraph(card.ticket or "-", meta_value),
                    Paragraph(release_name, meta_value),
                    Paragraph(section.doc_type or "-", meta_value),
                    Paragraph(section.account_coverage or "See below", meta_value),
                ],
            ]
            meta = Table(meta_rows, colWidths=[2.6 * cm, 4.0 * cm, 3.2 * cm, 7.2 * cm])
            meta.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), SOFT_BG),
                ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(meta)
            story.append(Spacer(1, 0.35 * cm))

            story.append(Paragraph("Brief Description", section_head))
            story.append(Paragraph(section.feature_summary, body_style))

            if section.release_details:
                story.append(Paragraph("At a Glance", section_head))
                for item in section.release_details:
                    story.append(Paragraph(item, bullet_style, bulletText="•"))

            def _emit(heading: str, flowables: list) -> None:
                """Glue the heading to its first line, then let the rest flow.

                Keeping the whole block together pushes long sections onto the next
                page and leaves a large gap; this only prevents an orphan heading.
                """
                if not flowables:
                    return
                story.append(KeepTogether([Paragraph(heading, section_head), flowables[0]]))
                story.extend(flowables[1:])

            _emit("Where to Find It", [
                Paragraph(x, bullet_style, bulletText="•") for x in section.where_to_find
            ])

            _emit("Walkthrough", [
                Paragraph(f"{idx}. {item}", body_style)
                for idx, item in enumerate(section.walkthrough, start=1)
            ])

            _emit("Expected Behaviour", [
                Paragraph(x, bullet_style, bulletText="•") for x in section.expected_behaviour
            ])

        return story

    from reportlab.pdfgen import canvas

    class CanvasWithPageNumbers(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_footer(total_pages)
                canvas.Canvas.showPage(self)
            super().save()

        def _draw_footer(self, total_pages: int):
            self.setStrokeColor(BORDER)
            self.line(1.8 * cm, 1.4 * cm, 19.2 * cm, 1.4 * cm)
            self.setFont("Helvetica", 8)
            self.setFillColor(MUTED)
            self.drawString(1.8 * cm, 0.9 * cm, f"PluginHive - Australia Post Shopify App - {today}")
            self.drawRightString(19.2 * cm, 0.9 * cm, f"Page {self._pageNumber} of {total_pages}")

    def _render(path: Path, page_lookup: dict[str, int]) -> None:
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=1.8 * cm,
            rightMargin=1.8 * cm,
            topMargin=1.6 * cm,
            bottomMargin=2.0 * cm,
            title=f"{release_name} Support Guide",
            author="AUPostDomainExpert",
        )
        doc.build(_build_story(page_lookup), canvasmaker=CanvasWithPageNumbers)

    # Pass 1: discover the real starting page of each card section.
    scratch = out_path.with_suffix(".pass1.tmp.pdf")
    _render(scratch, {})
    discovered = dict(page_map)
    scratch.unlink(missing_ok=True)

    # Pass 2: render with accurate index page numbers.
    _render(out_path, discovered)

    md_path = out_path.with_suffix(".md")
    md_path.write_text(_render_markdown(release_name, today, sections), encoding="utf-8")
    logger.info("Wrote %s and %s", out_path, md_path)
    return str(out_path)


def _md_clean(text: str) -> str:
    """Undo the PDF-oriented escaping in _clean_inline for markdown output."""
    text = text.replace("<b>", "**").replace("</b>", "**")
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return text


def _render_markdown(
    release_name: str,
    today: str,
    sections: list[tuple[ReleaseCard, SupportSection]],
) -> str:
    out: list[str] = [
        f"# AU Post App - Support Guide",
        "",
        f"**Release**: {release_name}  ",
        f"**Date**: {today}",
        "",
        "## Index",
        "",
        "| Story Card | Ticket | Title |",
        "|---|---|---|",
    ]
    for card, _section in sections:
        out.append(f"| {card.code} | {card.ticket or '-'} | {_md_clean(card.title)} |")
    out.append("")

    for card, section in sections:
        out += [
            "---",
            "",
            f"## {card.code} - {_md_clean(card.title)}",
            "",
            f"**Ticket**: {card.ticket or '-'} &nbsp;|&nbsp; **Type**: {_md_clean(section.doc_type) or '-'} "
            f"&nbsp;|&nbsp; **Account type**: {_md_clean(section.account_coverage) or 'See below'}  ",
            f"**Trello**: {card.card_url}",
            "",
            "### Brief Description",
            "",
            _md_clean(section.feature_summary),
            "",
        ]
        if section.release_details:
            out.append("### At a Glance")
            out.append("")
            out += [f"- {_md_clean(x)}" for x in section.release_details]
            out.append("")
        out += ["### Where to Find It", ""]
        out += [f"- {_md_clean(x)}" for x in section.where_to_find]
        out += ["", "### Walkthrough", ""]
        out += [f"{i}. {_md_clean(x)}" for i, x in enumerate(section.walkthrough, start=1)]
        out += ["", "### Expected Behaviour", ""]
        out += [f"- {_md_clean(x)}" for x in section.expected_behaviour]
        out.append("")
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a release support guide PDF from a Trello list.")
    parser.add_argument("--list-name", default="SL AuPost v1.0.32: Iteration backlog")
    parser.add_argument(
        "--output",
        default="artifacts/SL_AuPost_v1_0_32_Support_Guide.pdf",
        help="Output PDF path",
    )
    parser.add_argument(
        "--cards",
        nargs="+",
        help="Specific Trello card URLs or short links. Overrides --list-name.",
    )
    parser.add_argument(
        "--sections-json",
        help="Optional JSON file of curated sections keyed by card code / short link / URL.",
    )
    args = parser.parse_args()
    pdf_path = generate_release_support_guide(
        list_name=args.list_name,
        output_path=args.output,
        card_refs=args.cards,
        sections_json=args.sections_json,
    )
    print(pdf_path)


if __name__ == "__main__":
    main()
