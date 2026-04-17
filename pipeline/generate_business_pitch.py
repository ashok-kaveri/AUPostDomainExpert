"""
generate_business_pitch.py
--------------------------
Generates a merchant-facing Business Pitch PDF for any Trello card.
Uses Claude to produce the content (problem, merchant scenarios, key benefits)
from the card name, description and acceptance criteria, then renders it
with ReportLab in the same style as the Order Grid Filtering pitch.

Usage:
    from pipeline.generate_business_pitch import generate_business_pitch
    pdf_path = generate_business_pitch(
        card_name="...", card_desc="...", card_id="...", card_url="..."
    )
"""
from __future__ import annotations

import json
import os
import re
import textwrap
from pathlib import Path

# ── ReportLab ─────────────────────────────────────────────────────────────────
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Font registration ──────────────────────────────────────────────────────────
_FONT_DIR = Path("/System/Library/Fonts/Supplemental")
for _name, _fname in [
    ("Arial", "Arial.ttf"),
    ("Arial-Bold", "Arial Bold.ttf"),
    ("Arial-Italic", "Arial Italic.ttf"),
    ("ArialUni", "Arial Unicode.ttf"),
]:
    _fp = _FONT_DIR / _fname
    if _fp.exists():
        try:
            pdfmetrics.registerFont(TTFont(_name, str(_fp)))
        except Exception:
            pass

# ── Palette ────────────────────────────────────────────────────────────────────
PURPLE      = colors.HexColor("#4B0082")
DARK_PURPLE = colors.HexColor("#2D0057")
ORANGE      = colors.HexColor("#FF6B00")
LIGHT_BG    = colors.HexColor("#F7F5FC")
CARD_BG     = colors.HexColor("#EDE9F8")
MID_GREY    = colors.HexColor("#E0DCF0")
BODY_GREY   = colors.HexColor("#555555")
WHITE       = colors.white
W, H        = A4
CW          = W - 4 * cm  # content width

_FILTER_POOL = [
    colors.HexColor("#6A0DAD"),
    colors.HexColor("#1565C0"),
    colors.HexColor("#2E7D32"),
    colors.HexColor("#BF360C"),
    colors.HexColor("#E65100"),
    colors.HexColor("#283593"),
    colors.HexColor("#4A148C"),
    colors.HexColor("#00695C"),
]
_DOT_POOL = [
    colors.HexColor("#C0392B"),
    colors.HexColor("#E65100"),
    colors.HexColor("#6A0DAD"),
    colors.HexColor("#1565C0"),
    colors.HexColor("#2E7D32"),
    colors.HexColor("#00695C"),
]


# ── Style helpers ──────────────────────────────────────────────────────────────
def _ps(name: str, **kw) -> ParagraphStyle:
    d = dict(fontName="Arial", fontSize=10, leading=15, textColor=BODY_GREY)
    d.update(kw)
    return ParagraphStyle(name, **d)


def _p(text: str, sty: ParagraphStyle) -> Paragraph:
    return Paragraph(text, sty)


def _sp(h: float = 0.3) -> Spacer:
    return Spacer(1, h * cm)


def _hr(c=MID_GREY, t: int = 1) -> HRFlowable:
    return HRFlowable(width="100%", thickness=t, color=c, spaceBefore=3, spaceAfter=5)


# ── Named styles ───────────────────────────────────────────────────────────────
_TAG      = _ps("tag",  fontName="Arial-Bold",   fontSize=9,  textColor=ORANGE,     alignment=TA_CENTER)
_H_TITLE  = _ps("ht",  fontName="Arial-Bold",   fontSize=30, textColor=WHITE,      alignment=TA_CENTER, leading=36)
_H_SUB    = _ps("hs",  fontName="Arial",        fontSize=13, textColor=colors.HexColor("#D0BFFF"), alignment=TA_CENTER, leading=18)
_H_TAG    = _ps("htl", fontName="Arial-Italic", fontSize=11, textColor=colors.HexColor("#C0AEDD"), alignment=TA_CENTER, leading=16)
_H_META   = _ps("hm",  fontName="Arial",        fontSize=10, textColor=colors.HexColor("#BBAADD"), alignment=TA_CENTER)
_SEC_HEAD = _ps("sh",  fontName="Arial-Bold",   fontSize=17, textColor=PURPLE,     spaceBefore=4, spaceAfter=6)
_SEC_INTRO= _ps("si",  fontSize=11, textColor=BODY_GREY, leading=18, alignment=TA_JUSTIFY, spaceAfter=6)
_PAIN_DESC= _ps("pad", fontSize=9.5, textColor=BODY_GREY, leading=14, alignment=TA_JUSTIFY)
_SCN_QUOT = _ps("sq",  fontName="Arial-Italic", fontSize=10.5, textColor=DARK_PURPLE, leading=16)
_SCN_ACT  = _ps("sa",  fontSize=9.5, textColor=BODY_GREY,    leading=14, alignment=TA_JUSTIFY)
_SCN_RES  = _ps("sr",  fontSize=9.5, textColor=colors.HexColor("#1E7E34"), leading=14, alignment=TA_JUSTIFY)
_SCN_LABEL= _ps("sl",  fontName="Arial-Bold", fontSize=9, textColor=WHITE, alignment=TA_CENTER)
_BEN_DESC = _ps("bd",  fontSize=9.5, textColor=BODY_GREY, leading=14, alignment=TA_JUSTIFY)


# ── Claude content generation ─────────────────────────────────────────────────
_CONTENT_PROMPT = """\
You are a PluginHive product writer. Given a Trello card for the AU Post Shopify App,
produce a JSON object for a merchant-facing Business Pitch document.

Card name: {card_name}
Card description / Acceptance Criteria:
{card_desc}
Trello URL: {card_url}

Return ONLY valid JSON (no markdown fences) with this exact schema:
{{
  "feature_name": "Short feature title (3-6 words)",
  "tagline": "One punchy line — what it does for the merchant (max 120 chars)",
  "problem_intro": "2-3 sentence paragraph describing the merchant pain before this feature",
  "pain_points": [
    {{"title": "...", "desc": "One sentence business impact"}}
  ],
  "scenarios": [
    {{
      "label": "FILTER/KEYWORD (ALL CAPS, max 12 chars)",
      "situation": "Merchant's real-world situation as a first-person statement (30-70 words)",
      "action": "What the merchant does with this feature (1 sentence)",
      "outcome": "Concrete business result (1 sentence, start with merchant benefit)"
    }}
  ],
  "benefits": [
    {{"label": "Short benefit title", "detail": "One sentence explanation"}}
  ]
}}

Rules:
- pain_points: 3-5 items, each grounded in real AU Post merchant operations
- scenarios: 5-8 items, each covering a different filter or use-case dimension from the AC
- benefits: 5-7 items covering speed, accuracy, UX, workflow, safety
- Keep language concrete and merchant-friendly — no technical jargon
- Do NOT invent features not implied by the AC; derive from it faithfully
"""


def _generate_content(card_name: str, card_desc: str, card_url: str) -> dict:
    import anthropic
    import config

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    prompt = _CONTENT_PROMPT.format(
        card_name=card_name,
        card_desc=card_desc or "(no description)",
        card_url=card_url or "",
    )
    resp = client.messages.create(
        model=config.CLAUDE_HAIKU_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    # Strip any accidental markdown fences
    raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
    return json.loads(raw)


# ── Cover ──────────────────────────────────────────────────────────────────────
def _cover(content: dict, card_id: str, card_url: str, date_str: str) -> list:
    def band(rows_data, bg):
        t = Table(rows_data, colWidths=[CW])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 20),
            ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ]))
        return t

    story = [band([[_p("BUSINESS PITCH  \u2022  NEW FEATURE", _TAG)]], DARK_PURPLE)]
    title_rows = [
        [_sp(0.8)],
        [_p(content["feature_name"], _H_TITLE)],
        [_sp(0.2)],
        [_p("AU Post Shopify App", _H_SUB)],
        [_sp(0.5)],
        [_p(content["tagline"], _H_TAG)],
        [_sp(0.8)],
    ]
    story.append(band(title_rows, PURPLE))
    acc = Table([[""]], colWidths=[CW], rowHeights=[3 * mm])
    acc.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ORANGE)]))
    story.append(acc)

    card_ref = f"Trello: {card_id or ''}"
    if card_url:
        card_ref += f"  |  {card_url}"
    story.append(band(
        [[_p(card_ref, _H_META), _p(date_str, _H_META), _p("PluginHive Product Team", _H_META)]],
        DARK_PURPLE,
    ))
    return story


# ── Section helper ─────────────────────────────────────────────────────────────
def _sec(title: str, intro: str = "") -> list:
    inner = [_p(title, _SEC_HEAD), _hr(ORANGE, 2)]
    if intro:
        inner.append(_p(intro, _SEC_INTRO))
    return [_sp(0.5), KeepTogether(inner)]


# ── Problem section ────────────────────────────────────────────────────────────
def _problem(content: dict) -> list:
    elems = _sec("The Problem", content["problem_intro"])

    rows = [[
        _p("Pain Point", _ps("th2", fontName="Arial-Bold", fontSize=9, textColor=WHITE, alignment=TA_CENTER)),
        _p("Business Impact", _ps("th2b", fontName="Arial-Bold", fontSize=9, textColor=WHITE, alignment=TA_CENTER)),
    ]]
    for i, pt in enumerate(content["pain_points"]):
        dc = _DOT_POOL[i % len(_DOT_POOL)]
        rows.append([
            _p(f'<font color="{dc.hexval()}"><b>{pt["title"]}</b></font>',
               _ps(f"ph{i}", fontName="Arial-Bold", fontSize=10, textColor=dc, leading=14)),
            _p(pt["desc"], _PAIN_DESC),
        ])
    t = Table(rows, colWidths=[4.5 * cm, 12.5 * cm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  PURPLE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("BOX",            (0, 0), (-1, -1), 1, MID_GREY),
        ("LINEABOVE",      (0, 1), (-1, -1), 0.4, MID_GREY),
        ("TOPPADDING",     (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 9),
        ("LEFTPADDING",    (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 10),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    elems.append(KeepTogether(t))
    return elems


# ── Scenario block ─────────────────────────────────────────────────────────────
def _scenario_block(label: str, situation: str, action: str, outcome: str, idx: int) -> list:
    fc = _FILTER_POOL[idx % len(_FILTER_POOL)]
    label_t = Table([[_p(label, _SCN_LABEL)]], colWidths=[CW])
    label_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), fc),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))
    content_rows = [
        [_p(f"\u201C{situation}\u201D", _SCN_QUOT)],
        [_sp(0.1)],
        [_p(f"<b>What they do:</b>  {action}", _SCN_ACT)],
        [_p(f'<font color="#1E7E34"><b>Result:</b></font>  {outcome}', _SCN_RES)],
        [_sp(0.1)],
    ]
    content_t = Table(content_rows, colWidths=[CW])
    content_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CARD_BG),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BOX",           (0, 0), (-1, -1), 1, MID_GREY),
    ]))
    return [KeepTogether([label_t, content_t]), _sp(0.3)]


# ── Scenarios section ──────────────────────────────────────────────────────────
def _scenarios(content: dict) -> list:
    elems = _sec(
        "Real-World Business Scenarios",
        "Here is how AU Post merchants will use this feature in their day-to-day operations.",
    )
    for i, sc in enumerate(content["scenarios"]):
        elems += _scenario_block(sc["label"], sc["situation"], sc["action"], sc["outcome"], i)
    return elems


# ── Benefits section ───────────────────────────────────────────────────────────
def _benefits(content: dict) -> list:
    rows = [[
        _p("Benefit", _ps("th3", fontName="Arial-Bold", fontSize=9, textColor=WHITE, alignment=TA_CENTER)),
        _p("Detail",  _ps("th3b", fontName="Arial-Bold", fontSize=9, textColor=WHITE, alignment=TA_CENTER)),
    ]]
    for i, b in enumerate(content["benefits"]):
        dc = _FILTER_POOL[i % len(_FILTER_POOL)]
        rows.append([
            _p(f'<font color="{dc.hexval()}"><b>{b["label"]}</b></font>',
               _ps(f"bl{i}", fontName="Arial-Bold", fontSize=10, textColor=dc, leading=14)),
            _p(b["detail"], _BEN_DESC),
        ])
    t = Table(rows, colWidths=[4 * cm, 13 * cm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  PURPLE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("BOX",            (0, 0), (-1, -1), 1, MID_GREY),
        ("LINEABOVE",      (0, 1), (-1, -1), 0.4, MID_GREY),
        ("TOPPADDING",     (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 9),
        ("LEFTPADDING",    (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 10),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return [_sp(0.5), KeepTogether([_p("Key Benefits", _SEC_HEAD), _hr(ORANGE, 2), t])]


# ── Header / footer callbacks ──────────────────────────────────────────────────
def _make_on_page(feature_name: str, date_str: str):
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(DARK_PURPLE)
        canvas.rect(0, H - 1.1 * cm, W, 1.1 * cm, fill=1, stroke=0)
        canvas.setFont("Arial-Bold", 8)
        canvas.setFillColor(WHITE)
        canvas.drawString(1.5 * cm, H - 0.75 * cm,
                          f"AU Post Shopify App  \u2022  {feature_name}")
        canvas.setFont("Arial", 8)
        canvas.drawRightString(W - 1.5 * cm, H - 0.75 * cm, "Confidential \u2014 PluginHive")
        canvas.setFillColor(LIGHT_BG)
        canvas.rect(0, 0, W, 0.9 * cm, fill=1, stroke=0)
        canvas.setFont("Arial", 7.5)
        canvas.setFillColor(colors.HexColor("#999999"))
        canvas.drawString(1.5 * cm, 0.32 * cm, f"Generated {date_str}")
        canvas.drawCentredString(W / 2, 0.32 * cm, f"Page {doc.page}")
        canvas.drawRightString(W - 1.5 * cm, 0.32 * cm, "pluginhive.com")
        canvas.restoreState()
    return on_page


def _on_cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(ORANGE)
    canvas.rect(0, 0, W, 3 * mm, fill=1, stroke=0)
    canvas.restoreState()


# ── Public entry point ─────────────────────────────────────────────────────────
def generate_business_pitch(
    card_name: str,
    card_desc: str,
    card_id: str = "",
    card_url: str = "",
    out_dir: str | None = None,
) -> str:
    """
    Generate a Business Pitch PDF from Trello card data.

    Returns the absolute path of the saved PDF file.
    """
    import datetime

    date_str = datetime.date.today().strftime("%B %Y")

    # ── Generate content with Claude ──────────────────────────────────────────
    content = _generate_content(card_name, card_desc, card_url)

    # ── Output path ───────────────────────────────────────────────────────────
    safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", card_name).strip("_")[:50]
    if out_dir:
        out_path = Path(out_dir)
    else:
        out_path = Path.home() / "Documents" / "PluginHive Reports" / safe_name
    out_path.mkdir(parents=True, exist_ok=True)
    pdf_file = out_path / f"BusinessPitch_{safe_name}.pdf"

    # ── Build story ────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        str(pdf_file), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title=f"{content['feature_name']} — Business Pitch",
        author="PluginHive Product Team",
    )
    story = (
        _cover(content, card_id, card_url, date_str)
        + [_sp(0.8)]
        + _problem(content)
        + [_sp(0.4)]
        + _scenarios(content)
        + [_sp(0.4)]
        + _benefits(content)
    )

    on_page = _make_on_page(content["feature_name"], date_str)
    doc.build(story, onFirstPage=_on_cover, onLaterPages=on_page)

    return str(pdf_file)
