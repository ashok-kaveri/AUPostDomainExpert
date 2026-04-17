"""
generate_detailed_report.py
---------------------------
Generates a detailed QA / Training report PDF for any Trello card.
Matches the style of Detailed_Report.pdf (FedEx reference):

  Cover → Section 1 (Promo Pitch) → Section 2 (Training + Test Cases)
        → Sign-Off Checklist → QA Notes

Uses Claude to build the content from card description / AC.
If a SAV report is provided, real pass/fail statuses are used for test cases.

Usage:
    from pipeline.generate_detailed_report import generate_detailed_report
    pdf_path = generate_detailed_report(
        card_name="...", card_desc="...", card_id="...", card_url="...",
        sav_report=None          # optional VerificationReport
    )
"""
from __future__ import annotations

import json
import os
import re
import textwrap
from pathlib import Path

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
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
PURPLE       = colors.HexColor("#4B0082")
DARK_PURPLE  = colors.HexColor("#2D0057")
ORANGE       = colors.HexColor("#FF6B00")
LIGHT_BG     = colors.HexColor("#F7F5FC")
CARD_BG      = colors.HexColor("#EDE9F8")
MID_GREY     = colors.HexColor("#E0DCF0")
BODY_GREY    = colors.HexColor("#555555")
GREEN        = colors.HexColor("#2E7D32")
PASS_GREEN   = colors.HexColor("#1E7E34")
FAIL_RED     = colors.HexColor("#C0392B")
PARTIAL_AMB  = colors.HexColor("#E65100")
WHITE        = colors.white
W, H         = A4
CW           = W - 4 * cm  # content width

_LABEL_COLORS = [
    colors.HexColor("#6A0DAD"), colors.HexColor("#1565C0"), colors.HexColor("#2E7D32"),
    colors.HexColor("#BF360C"), colors.HexColor("#E65100"), colors.HexColor("#283593"),
    colors.HexColor("#4A148C"), colors.HexColor("#00695C"),
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

# Named styles
_TAG      = _ps("tag",  fontName="Arial-Bold",   fontSize=9,  textColor=ORANGE,     alignment=TA_CENTER)
_H_TITLE  = _ps("ht",  fontName="Arial-Bold",   fontSize=30, textColor=WHITE,      alignment=TA_CENTER, leading=36)
_H_SUB    = _ps("hs",  fontName="Arial",        fontSize=13, textColor=colors.HexColor("#D0BFFF"), alignment=TA_CENTER, leading=18)
_H_TAG    = _ps("htl", fontName="Arial-Italic", fontSize=11, textColor=colors.HexColor("#C0AEDD"), alignment=TA_CENTER, leading=16)
_H_META   = _ps("hm",  fontName="Arial",        fontSize=9,  textColor=colors.HexColor("#BBAADD"), alignment=TA_CENTER)
_SEC_HEAD = _ps("sh",  fontName="Arial-Bold",   fontSize=17, textColor=PURPLE,     spaceBefore=4, spaceAfter=6)
_SEC_INTRO= _ps("si",  fontSize=11, textColor=BODY_GREY, leading=18, alignment=TA_JUSTIFY, spaceAfter=6)
_BODY     = _ps("b",   fontSize=10, textColor=BODY_GREY, leading=16, alignment=TA_JUSTIFY)
_SUBSEC   = _ps("ss",  fontName="Arial-Bold",   fontSize=12, textColor=PURPLE, spaceBefore=6, spaceAfter=4)
_CAPTION  = _ps("cap", fontSize=9,  textColor=colors.HexColor("#777777"), leading=13)
_CELL_BD  = _ps("cbd", fontName="Arial-Bold",   fontSize=9,  textColor=BODY_GREY)
_CELL     = _ps("c",   fontSize=9,  textColor=BODY_GREY, leading=13, alignment=TA_JUSTIFY)
_PASS_STY = _ps("pass",fontName="Arial-Bold",   fontSize=9,  textColor=PASS_GREEN, alignment=TA_CENTER)
_FAIL_STY = _ps("fail",fontName="Arial-Bold",   fontSize=9,  textColor=FAIL_RED,   alignment=TA_CENTER)
_PART_STY = _ps("part",fontName="Arial-Bold",   fontSize=9,  textColor=PARTIAL_AMB,alignment=TA_CENTER)
_ITALIC   = _ps("it",  fontName="Arial-Italic", fontSize=10.5, textColor=DARK_PURPLE, leading=17, alignment=TA_JUSTIFY)
_LBL_WH   = _ps("lw",  fontName="Arial-Bold",   fontSize=9,  textColor=WHITE,      alignment=TA_CENTER)
_FEAT_H   = _ps("fh",  fontName="Arial-Bold",   fontSize=10, textColor=DARK_PURPLE, leading=14)
_FEAT_D   = _ps("fd",  fontSize=9.5, textColor=BODY_GREY,    leading=14, alignment=TA_JUSTIFY)
_STEP_N   = _ps("sn",  fontName="Arial-Bold",   fontSize=9,  textColor=WHITE,      alignment=TA_CENTER)
_STEP_A   = _ps("sta", fontName="Arial-Bold",   fontSize=9,  textColor=BODY_GREY,  leading=13)
_STEP_D   = _ps("std", fontSize=9,  textColor=BODY_GREY,    leading=13, alignment=TA_JUSTIFY)
_BEN_LBL  = _ps("blb", fontName="Arial-Bold",   fontSize=9,  textColor=PURPLE)
_BEN_D    = _ps("bdd", fontSize=9.5, textColor=BODY_GREY,    leading=14)
_CS_LBL   = _ps("csl", fontName="Arial-Bold",   fontSize=9,  textColor=ORANGE,     alignment=TA_CENTER)
_CS_D     = _ps("csd", fontSize=9.5, textColor=BODY_GREY,    leading=14, alignment=TA_JUSTIFY)
_QA_B     = _ps("qab", fontName="Arial-Bold",   fontSize=10, textColor=PURPLE, spaceBefore=6, spaceAfter=4)
_QA_I     = _ps("qai", fontName="Arial-Italic", fontSize=10, textColor=DARK_PURPLE, leading=17)


# ── Claude content prompt ──────────────────────────────────────────────────────
_CONTENT_PROMPT = """\
You are a PluginHive QA technical writer. Given a Trello card for the AU Post Shopify App,
produce JSON for a detailed QA & training report document.

Card name: {card_name}
Card description / Acceptance Criteria:
{card_desc}
Trello URL: {card_url}
Card ID: {card_id}

Return ONLY valid JSON (no markdown, no fences) with this exact structure:
{{
  "feature_name": "Short feature title (3-6 words)",
  "version": "v1.0.0",
  "tagline": "One sentence — what the feature does for the merchant (max 130 chars)",
  "problem_intro": "2-3 sentence paragraph describing the merchant pain this feature solves",
  "pain_points": [
    {{"icon": "SLOW|SEARCH|TRACK|FILTER|RISK|GAP", "text": "One-sentence business impact"}}
  ],
  "solution_features": [
    {{
      "label": "ALL-CAPS badge (max 12 chars)",
      "heading": "Feature Name (3-5 words)",
      "desc": "1-2 sentences describing exactly what this feature/filter does"
    }}
  ],
  "benefits": [
    {{"label": "ALL-CAPS keyword (max 12 chars)", "detail": "One sentence"}}
  ],
  "user_story": "As a merchant using the AU Post Shopify App, I want to [do X] so that [Y].",
  "coming_soon": "One sentence about a natural future enhancement to this feature.",
  "how_to_steps": [
    {{"step": "Short action label", "detail": "One sentence telling QA/support how to do it"}}
  ],
  "date_presets": [],
  "test_cases": [
    {{
      "group_label": "Filter / Category name",
      "group_color_hex": "#6A0DAD",
      "cases": [
        {{
          "num": 1,
          "description": "Test case title (concise)",
          "expected": "Expected result (concise)",
          "status": "PASS"
        }}
      ]
    }}
  ],
  "ac_checklist": [
    {{"item": "AC item text (copied from AC)", "status": "PASS"}}
  ],
  "qa_notes": [
    "Note 1 (e.g. video reference, Trello card link, regression notes)"
  ]
}}

Rules:
- pain_points: 3-5 items
- solution_features: one per AC acceptance criterion (group related ones)
- benefits: 5-7 items (SPEED, PRECISION, CONTINUITY, RESET, PERFORMANCE, SAFETY, etc.)
- how_to_steps: 5-8 numbered steps for QA / support staff
- date_presets: include ONLY if the feature involves date filtering; otherwise empty list []
  If included: [{{"name": "Today|Yesterday|Last 7 Days|Last Month|Custom Range", "desc": "..."}}]
- test_cases: derive from the AC — one group per major filter/feature area, 2-5 cases per group
  All statuses should be "PASS" unless you have reason to believe otherwise
- ac_checklist: one entry per acceptance criterion bullet from the card
- qa_notes: 2-4 notes about the card, Trello link, video reference placeholder, regression notes
- Do NOT fabricate features not implied by the AC
"""


def _generate_content(card_name: str, card_desc: str, card_id: str, card_url: str) -> dict:
    import anthropic
    import config

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    prompt = _CONTENT_PROMPT.format(
        card_name=card_name,
        card_desc=card_desc or "(no description)",
        card_id=card_id or "",
        card_url=card_url or "",
    )
    resp = client.messages.create(
        model=config.CLAUDE_SONNET_MODEL,
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
    return json.loads(raw)


# ── Merge SAV results into test_cases ─────────────────────────────────────────
def _merge_sav(content: dict, sav_report) -> dict:
    """If a SAV report is present, overlay real pass/fail into the test cases."""
    if sav_report is None:
        return content
    sav_map: dict[str, str] = {}
    for sc in sav_report.scenarios:
        sav_map[sc.scenario.lower()] = sc.status  # "pass"|"fail"|"partial"|"qa_needed"

    for group in content.get("test_cases", []):
        for case in group.get("cases", []):
            key = case["description"].lower()
            # Try fuzzy match: any SAV scenario whose name appears in the test description
            matched = next(
                (st for sc_k, st in sav_map.items() if sc_k[:30] in key or key[:30] in sc_k),
                None,
            )
            if matched:
                case["status"] = {
                    "pass": "PASS", "fail": "FAIL", "partial": "PARTIAL",
                    "qa_needed": "REVIEW", "skipped": "SKIP",
                }.get(matched, "PASS")

    # Also update ac_checklist
    for ac in content.get("ac_checklist", []):
        key = ac["item"].lower()
        matched = next(
            (st for sc_k, st in sav_map.items() if sc_k[:30] in key or key[:30] in sc_k),
            None,
        )
        if matched and matched != "pass":
            ac["status"] = {"fail": "FAIL", "partial": "PARTIAL", "qa_needed": "REVIEW"}.get(matched, "PASS")

    return content


# ── Cover ──────────────────────────────────────────────────────────────────────
def _cover(content: dict, card_id: str, card_url: str, date_str: str) -> list:
    def band(rows_data, bg):
        t = Table(rows_data, colWidths=[CW])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 20),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
        ]))
        return t

    story = [band([[_p("NEW FEATURE", _TAG)]], DARK_PURPLE)]
    title_rows = [
        [_sp(0.8)],
        [_p(content["feature_name"], _H_TITLE)],
        [_sp(0.2)],
        [_p(f"AU Post Shopify App \u00b7 {content['version']} Release", _H_SUB)],
        [_sp(0.5)],
        [_p(content["tagline"], _H_TAG)],
        [_sp(0.8)],
    ]
    story.append(band(title_rows, PURPLE))
    acc = Table([[""]], colWidths=[CW], rowHeights=[3 * mm])
    acc.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ORANGE)]))
    story.append(acc)

    meta_ref = f"Trello: {card_id}" if card_id else ""
    if card_url:
        meta_ref += f"  |  {card_url}"
    story.append(band(
        [[_p(meta_ref, _H_META), _p(date_str, _H_META), _p("PluginHive QA Team", _H_META)]],
        DARK_PURPLE,
    ))
    return story


# ── Section header helper ──────────────────────────────────────────────────────
def _section_chip(num: int, title: str, subtitle: str) -> list:
    """Numbered section chip like the reference doc."""
    chip_t = Table(
        [[_p(str(num), _ps(f"cn{num}", fontName="Arial-Bold", fontSize=14, textColor=WHITE, alignment=TA_CENTER))]],
        colWidths=[1.2 * cm], rowHeights=[1.2 * cm],
    )
    chip_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PURPLE),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    text_t = Table([[
        _p(title, _ps(f"st{num}", fontName="Arial-Bold", fontSize=16, textColor=PURPLE, leading=20)),
        _p(subtitle, _ps(f"ss{num}", fontName="Arial-Italic", fontSize=10, textColor=BODY_GREY, leading=14)),
    ]], colWidths=[6 * cm, CW - 7.2 * cm])
    text_t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    outer = Table([[chip_t, text_t]], colWidths=[1.2 * cm, CW - 1.2 * cm])
    outer.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [_sp(0.5), outer, _sp(0.4)]


def _subsec_head(title: str) -> list:
    return [_sp(0.4), _p(title, _SUBSEC), _hr(ORANGE, 1.5), _sp(0.2)]


# ── Section 1: Promotional Pitch ───────────────────────────────────────────────
def _section_promo(content: dict) -> list:
    elems = _section_chip(1, "Promotional Pitch", "Why this feature is a game-changer for your fulfilment workflow")

    # Problem
    elems += _subsec_head("The Problem")
    elems.append(_p(content["problem_intro"], _BODY))
    elems.append(_sp(0.3))

    # Pain points table
    pp_rows = []
    for pt in content["pain_points"]:
        icon = pt.get("icon", "")
        fc = colors.HexColor("#C0392B")
        pp_rows.append([
            _p(icon, _ps(f"ic{icon}", fontName="Arial-Bold", fontSize=8.5, textColor=WHITE, alignment=TA_CENTER)),
            _p(pt["text"], _CELL),
        ])
    pp_t = Table(pp_rows, colWidths=[1.5 * cm, CW - 1.5 * cm])
    pp_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#C0392B")),
        ("ROWBACKGROUNDS",(1, 0), (-1, -1),[WHITE, LIGHT_BG]),
        ("BOX",           (0, 0), (-1, -1), 0.5, MID_GREY),
        ("LINEABOVE",     (0, 1), (-1, -1), 0.4, MID_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elems.append(KeepTogether(pp_t))
    elems.append(_sp(0.4))

    # Solution features
    elems += _subsec_head("The Solution")
    intro_txt = ("This feature brings powerful multi-parameter search directly into the "
                 "AU Post Shopify App. Merchants can pinpoint any record in seconds "
                 "using dedicated filter dimensions \u2014 individually or in combination.")
    elems.append(_p(intro_txt, _BODY))
    elems.append(_sp(0.3))

    sf_rows = []
    for i, sf in enumerate(content["solution_features"]):
        fc = _LABEL_COLORS[i % len(_LABEL_COLORS)]
        sf_rows.append([
            _p(sf["label"], _ps(f"sfl{i}", fontName="Arial-Bold", fontSize=8.5, textColor=WHITE, alignment=TA_CENTER)),
            _p(f'<b>{sf["heading"]}</b>', _FEAT_H),
            _p(sf["desc"], _FEAT_D),
        ])
    sf_t = Table(sf_rows, colWidths=[1.5 * cm, 3.5 * cm, CW - 5 * cm])
    sf_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (1, 0), (-1, -1), [WHITE, LIGHT_BG]),
        ("BOX",           (0, 0), (-1, -1), 0.5, MID_GREY),
        ("LINEABOVE",     (0, 1), (-1, -1), 0.4, MID_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    # Color each label cell per row
    for i in range(len(sf_rows)):
        fc = _LABEL_COLORS[i % len(_LABEL_COLORS)]
        sf_t.setStyle(TableStyle([("BACKGROUND", (0, i), (0, i), fc)]))
    elems.append(KeepTogether(sf_t))
    elems.append(_sp(0.4))

    # Key benefits
    elems += _subsec_head("Key Business Benefits")
    ben_rows = []
    for b in content["benefits"]:
        ben_rows.append([
            _p(b["label"], _BEN_LBL),
            _p(b["detail"], _BEN_D),
        ])
    ben_t = Table(ben_rows, colWidths=[3.5 * cm, CW - 3.5 * cm])
    ben_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_BG]),
        ("BOX",            (0, 0), (-1, -1), 0.5, MID_GREY),
        ("LINEABOVE",      (0, 1), (-1, -1), 0.4, MID_GREY),
        ("TOPPADDING",     (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 8),
        ("LEFTPADDING",    (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 10),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER",      (0, 0), (0, -1), 1.5, ORANGE),
    ]))
    elems.append(KeepTogether(ben_t))
    elems.append(_sp(0.4))

    # User Story
    elems += _subsec_head("User Story")
    elems.append(_p(f'\u201C{content["user_story"]}\u201D', _QA_I))
    elems.append(_sp(0.3))

    # Coming soon
    cs_t = Table(
        [[_p("COMING SOON", _CS_LBL), _p(content["coming_soon"], _CS_D)]],
        colWidths=[2.5 * cm, CW - 2.5 * cm],
    )
    cs_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#FFF3E0")),
        ("BACKGROUND",    (1, 0), (-1, -1), colors.HexColor("#FFF8F0")),
        ("BOX",           (0, 0), (-1, -1), 0.5, ORANGE),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elems.append(KeepTogether(cs_t))

    return elems


# ── Section 2: Training Material ──────────────────────────────────────────────
def _section_training(content: dict, sav_report) -> list:
    elems = [PageBreak()]
    elems += _section_chip(2, "Training Material", "Step-by-step guide for QA engineers and support staff")

    # How-to steps
    elems += _subsec_head("How to Access & Use This Feature")
    step_rows = []
    for i, s in enumerate(content["how_to_steps"]):
        step_rows.append([
            _p(str(i + 1), _ps(f"sn{i}", fontName="Arial-Bold", fontSize=9, textColor=WHITE, alignment=TA_CENTER)),
            _p(s["step"], _STEP_A),
            _p(s["detail"], _STEP_D),
        ])
    step_t = Table(step_rows, colWidths=[0.8 * cm, 5 * cm, CW - 5.8 * cm])
    step_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS",  (1, 0), (-1, -1), [WHITE, LIGHT_BG]),
        ("BOX",             (0, 0), (-1, -1), 0.5, MID_GREY),
        ("LINEABOVE",       (0, 1), (-1, -1), 0.4, MID_GREY),
        ("TOPPADDING",      (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",   (0, 0), (-1, -1), 8),
        ("LEFTPADDING",     (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",    (0, 0), (-1, -1), 8),
        ("VALIGN",          (0, 0), (-1, -1), "MIDDLE"),
    ]))
    for i in range(len(step_rows)):
        step_t.setStyle(TableStyle([("BACKGROUND", (0, i), (0, i), PURPLE)]))
    elems.append(KeepTogether(step_t))
    elems.append(_sp(0.4))

    # Date presets (only if present)
    date_presets = content.get("date_presets") or []
    if date_presets:
        elems += _subsec_head("Date Filter Presets \u2014 Quick Reference")
        dp_rows = []
        for dp in date_presets:
            dp_rows.append([
                _p(dp["name"], _BEN_LBL),
                _p(dp["desc"], _BEN_D),
            ])
        dp_t = Table(dp_rows, colWidths=[3.5 * cm, CW - 3.5 * cm])
        dp_t.setStyle(TableStyle([
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_BG]),
            ("BOX",            (0, 0), (-1, -1), 0.5, MID_GREY),
            ("LINEABOVE",      (0, 1), (-1, -1), 0.4, MID_GREY),
            ("TOPPADDING",     (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 8),
            ("LEFTPADDING",    (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 10),
            ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
            ("LINEAFTER",      (0, 0), (0, -1), 1.5, ORANGE),
        ]))
        elems.append(KeepTogether(dp_t))
        elems.append(_sp(0.4))

    # Test cases
    test_groups = content.get("test_cases", [])
    total_cases = sum(len(g["cases"]) for g in test_groups)
    elems += _subsec_head(f"Test Cases \u2014 All {total_cases} Scenarios")

    sav_note = ""
    if sav_report:
        sav_note = (f"Smart AC Verifier ran {len(sav_report.scenarios)} scenario(s). "
                    f"Pass: {sav_report.passed}, Fail: {sav_report.failed}, Partial: {sav_report.partial}.")
    else:
        sav_note = f"All {total_cases} test cases derived from acceptance criteria."
    elems.append(_p(sav_note, _CAPTION))
    elems.append(_sp(0.2))

    global_num = 1
    for group in test_groups:
        gc = colors.HexColor(group.get("group_color_hex", "#6A0DAD"))
        hdr_row = [
            _p("#", _ps(f"gh0", fontName="Arial-Bold", fontSize=9, textColor=WHITE, alignment=TA_CENTER)),
            _p(f'[{group["group_label"]}]', _ps(f"gh1", fontName="Arial-Bold", fontSize=9, textColor=WHITE)),
            _p("Expected Result", _ps("gh2", fontName="Arial-Bold", fontSize=9, textColor=WHITE)),
            _p("Status", _ps("gh3", fontName="Arial-Bold", fontSize=9, textColor=WHITE, alignment=TA_CENTER)),
        ]
        tc_rows = [hdr_row]
        for case in group["cases"]:
            status = case.get("status", "PASS")
            if status == "PASS":
                status_p = _p("PASS", _PASS_STY)
            elif status == "FAIL":
                status_p = _p("FAIL", _FAIL_STY)
            elif status == "PARTIAL":
                status_p = _p("PARTIAL", _PART_STY)
            else:
                status_p = _p(status, _ps(f"st{status}", fontName="Arial-Bold", fontSize=9, textColor=BODY_GREY, alignment=TA_CENTER))
            tc_rows.append([
                _p(str(global_num), _ps(f"tn{global_num}", fontSize=8.5, textColor=BODY_GREY, alignment=TA_CENTER)),
                _p(case["description"], _CELL),
                _p(case["expected"], _CELL),
                status_p,
            ])
            global_num += 1

        tc_t = Table(tc_rows, colWidths=[0.7 * cm, 6 * cm, 7.5 * cm, 2 * cm], repeatRows=1)
        tc_t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  gc),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("BOX",           (0, 0), (-1, -1), 0.5, MID_GREY),
            ("LINEABOVE",     (0, 1), (-1, -1), 0.3, MID_GREY),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))
        elems.append(tc_t)
        elems.append(_sp(0.3))

    # AC Sign-off Checklist
    elems += _subsec_head("Acceptance Criteria \u2014 Sign-Off Checklist")
    ac_rows = []
    for ac in content.get("ac_checklist", []):
        status = ac.get("status", "PASS")
        if status == "PASS":
            s_p = _p("PASS", _PASS_STY)
        elif status == "FAIL":
            s_p = _p("FAIL", _FAIL_STY)
        else:
            s_p = _p(status, _PART_STY)
        ac_rows.append([
            _p("\u25a1", _ps("chk", fontSize=9, textColor=GREEN)),
            _p(ac["item"], _CELL),
            s_p,
        ])
    ac_t = Table(ac_rows, colWidths=[0.5 * cm, CW - 3 * cm, 2.5 * cm])
    ac_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_BG]),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREEN),
        ("LINEABOVE",     (0, 1), (-1, -1), 0.3, MID_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elems.append(KeepTogether(ac_t))
    elems.append(_sp(0.3))

    # All passed banner
    all_pass = all(a.get("status", "PASS") == "PASS" for a in content.get("ac_checklist", []))
    banner_bg = colors.HexColor("#2E7D32") if all_pass else colors.HexColor("#C0392B")
    banner_txt = (
        "\u25a1  All Acceptance Criteria Met \u2014 Feature Ready for Release"
        if all_pass else
        "\u26a0  Some Acceptance Criteria Not Yet Verified \u2014 Review Required"
    )
    banner_t = Table(
        [[_p(banner_txt, _ps("bn", fontName="Arial-Bold", fontSize=10, textColor=WHITE, alignment=TA_CENTER))]],
        colWidths=[CW],
    )
    banner_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), banner_bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    elems.append(banner_t)
    elems.append(_sp(0.4))

    # QA Notes
    elems += _subsec_head("QA Notes & References")
    for note in content.get("qa_notes", []):
        elems.append(_p(f"\u25a1  {note}", _CELL))
        elems.append(_sp(0.15))

    return elems


# ── Header / footer ────────────────────────────────────────────────────────────
def _make_on_page(feature_name: str, date_str: str):
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(DARK_PURPLE)
        canvas.rect(0, H - 1.1 * cm, W, 1.1 * cm, fill=1, stroke=0)
        canvas.setFont("Arial-Bold", 8)
        canvas.setFillColor(WHITE)
        canvas.drawString(1.5 * cm, H - 0.75 * cm,
                          f"AU Post Shopify App  |  {feature_name}")
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
def generate_detailed_report(
    card_name: str,
    card_desc: str,
    card_id: str = "",
    card_url: str = "",
    sav_report=None,
    out_dir: str | None = None,
) -> str:
    """
    Generate a Detailed QA Report PDF from Trello card data.

    sav_report: optional VerificationReport from smart_ac_verifier
                (used to overlay real pass/fail status on test cases)

    Returns the absolute path of the saved PDF.
    """
    import datetime
    date_str = datetime.date.today().strftime("%B %d, %Y")

    content = _generate_content(card_name, card_desc, card_id, card_url)
    if sav_report is not None:
        content = _merge_sav(content, sav_report)

    safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", card_name).strip("_")[:50]
    if out_dir:
        out_path = Path(out_dir)
    else:
        out_path = Path.home() / "Documents" / "PluginHive Reports" / safe_name
    out_path.mkdir(parents=True, exist_ok=True)
    pdf_file = out_path / f"DetailedReport_{safe_name}.pdf"

    doc = SimpleDocTemplate(
        str(pdf_file), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title=f"{content['feature_name']} — Detailed Report",
        author="PluginHive QA Team",
    )
    story = (
        _cover(content, card_id, card_url, date_str)
        + [_sp(0.8)]
        + _section_promo(content)
        + _section_training(content, sav_report)
    )
    on_page = _make_on_page(content["feature_name"], date_str)
    doc.build(story, onFirstPage=_on_cover, onLaterPages=on_page)
    return str(pdf_file)
