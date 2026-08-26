#!/usr/bin/env python3
"""Build the AirShield release, pitch, demo, and technical-authority PDFs."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Flowable,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
PAGE_W, PAGE_H = A4
NAVY = colors.HexColor("#071821")
NAVY_2 = colors.HexColor("#102730")
INK = colors.HexColor("#18343D")
INK_2 = colors.HexColor("#567079")
MUTED = colors.HexColor("#71878E")
LINE = colors.HexColor("#DFE7E9")
PALE = colors.HexColor("#F2F6F6")
TEAL = colors.HexColor("#0BAE97")
TEAL_DARK = colors.HexColor("#087D6F")
MINT = colors.HexColor("#DFF8F1")
BLUE = colors.HexColor("#3974D9")
BLUE_PALE = colors.HexColor("#E9F1FF")
AMBER = colors.HexColor("#EFA821")
AMBER_PALE = colors.HexColor("#FFF1CF")
VIOLET = colors.HexColor("#7757C8")
WHITE = colors.white

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("AirSans", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("AirSans-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("AirMono", str(FONT_DIR / "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily("AirSans", normal="AirSans", bold="AirSans-Bold")


@dataclass(frozen=True)
class DocumentSpec:
    source: Path
    output: Path
    title: str
    subtitle: str
    short_title: str
    strapline: str
    badge: str
    subject: str


SPECS = [
    DocumentSpec(
        source=ROOT / "docs" / "AIRSHIELD_REQUIREMENTS_AND_RUNBOOK.md",
        output=ROOT / "docs" / "AirShield_Requirements_and_Runbook.pdf",
        title="Requirements\nand Runbook",
        subtitle="Implemented scope, exact run steps, verification and production gates",
        short_title="REQUIREMENTS & RUNBOOK",
        strapline="BUILD IT. RUN IT. VERIFY IT. RELEASE IT SAFELY.",
        badge="IMPLEMENTATION  •  OPERATIONS  •  ACCEPTANCE",
        subject="Requirements, setup, demonstration, validation and production release guidance",
    ),
    DocumentSpec(
        source=ROOT / "docs" / "AIRSHIELD_CEO_TECHNICAL_BRIEFING.md",
        output=ROOT / "docs" / "AirShield_CEO_Technical_Briefing.pdf",
        title="CEO Technical\nBriefing",
        subtitle="Architecture, trust boundaries, technology, encryption and voice protection",
        short_title="CEO TECHNICAL BRIEFING",
        strapline="KEEP THE INTELLIGENCE. REMOVE THE IDENTIFIERS.",
        badge="EXECUTIVE  •  ARCHITECTURE  •  SECURITY",
        subject="AirShield architecture, technology, encryption, voice capture and production limitations",
    ),
    DocumentSpec(
        source=ROOT / "docs" / "AIRSHIELD_HACKATHON_PITCH.md",
        output=ROOT / "docs" / "AirShield_Hackathon_Pitch.pdf",
        title="Internal Hackathon\nPitch",
        subtitle="Problem, product differentiation, implemented proof, business value and pilot ask",
        short_title="INTERNAL HACKATHON PITCH",
        strapline="EVERY AI DATA TRANSACTION MUST EARN PERMISSION.",
        badge="PITCH  •  DIFFERENTIATION  •  BUSINESS VALUE",
        subject="AirShield internal hackathon product and business pitch",
    ),
    DocumentSpec(
        source=ROOT / "docs" / "AIRSHIELD_MANAGER_DEMO_PLAYBOOK.md",
        output=ROOT / "docs" / "AirShield_Manager_Demo_Playbook.pdf",
        title="Manager Demo\nPlaybook",
        subtitle="Exact talk track, click path, expected results, questions and fallback plan",
        short_title="MANAGER DEMO PLAYBOOK",
        strapline="SHOW THE CONTROL. PROVE THE FAILURE. EXPLAIN THE BOUNDARY.",
        badge="DEMO  •  TALK TRACK  •  EXPECTED RESULTS",
        subject="AirShield manager demonstration script and operating playbook",
    ),
    DocumentSpec(
        source=ROOT / "docs" / "AIRSHIELD_TECHNICAL_AUTHORITY_DOSSIER.md",
        output=ROOT / "docs" / "AirShield_Technical_Authority_Dossier.pdf",
        title="Technical Authority\nDossier",
        subtitle="Implemented architecture, security controls, cryptography, protocols, evidence and production gates",
        short_title="TECHNICAL AUTHORITY DOSSIER",
        strapline="IMPLEMENTED FACTS. EXPLICIT BOUNDARIES. FAIL-CLOSED GATES.",
        badge="ARCHITECTURE  •  SECURITY  •  ASSURANCE",
        subject="Authoritative AirShield implementation, security-boundary and production-readiness description",
    ),
]


def wrap_words(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def draw_shield(c: Canvas, x: float, y: float, size: float) -> None:
    path = c.beginPath()
    path.moveTo(x + size * 0.5, y + size)
    path.lineTo(x + size * 0.92, y + size * 0.82)
    path.lineTo(x + size * 0.84, y + size * 0.32)
    path.curveTo(x + size * 0.75, y + size * 0.12, x + size * 0.60, y + size * 0.03, x + size * 0.5, y)
    path.curveTo(x + size * 0.40, y + size * 0.03, x + size * 0.25, y + size * 0.12, x + size * 0.16, y + size * 0.32)
    path.lineTo(x + size * 0.08, y + size * 0.82)
    path.close()
    c.setFillColor(colors.HexColor("#0C353B"))
    c.setStrokeColor(TEAL)
    c.setLineWidth(2)
    c.drawPath(path, fill=1, stroke=1)
    c.setStrokeColor(WHITE)
    c.setLineWidth(2)
    c.line(x + size * 0.29, y + size * 0.51, x + size * 0.44, y + size * 0.36)
    c.line(x + size * 0.44, y + size * 0.36, x + size * 0.72, y + size * 0.66)


def arrow(c: Canvas, x1: float, y1: float, x2: float, y2: float, color=TEAL) -> None:
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(1.2)
    c.line(x1, y1, x2, y2)
    if abs(x2 - x1) >= abs(y2 - y1):
        d = 1 if x2 > x1 else -1
        p = c.beginPath()
        p.moveTo(x2, y2)
        p.lineTo(x2 - d * 2.2 * mm, y2 - 1.4 * mm)
        p.lineTo(x2 - d * 2.2 * mm, y2 + 1.4 * mm)
    else:
        d = 1 if y2 > y1 else -1
        p = c.beginPath()
        p.moveTo(x2, y2)
        p.lineTo(x2 - 1.4 * mm, y2 - d * 2.2 * mm)
        p.lineTo(x2 + 1.4 * mm, y2 - d * 2.2 * mm)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


class AirShieldDoc(BaseDocTemplate):
    def __init__(self, filename: str, spec: DocumentSpec, **kwargs):
        super().__init__(filename, **kwargs)
        self.spec = spec
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, 0, 0, 0, 0, id="body")
        self.addPageTemplates(PageTemplate(id="document", frames=[frame], onPage=self.draw_page))

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "Section":
            title = flowable.getPlainText()
            key = "section-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=0, closed=False)
            self.notify("TOCEntry", (0, title, self.page, key))

    def draw_page(self, c: Canvas, doc) -> None:
        c.saveState()
        c.setTitle(self.spec.short_title.title().replace("Ceo", "CEO"))
        c.setAuthor("AirShield")
        c.setSubject(self.spec.subject)
        if doc.page == 1:
            c.setFillColor(NAVY)
            c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#0B2B31"))
            c.circle(PAGE_W + 12 * mm, PAGE_H - 35 * mm, 74 * mm, fill=1, stroke=0)
            c.setStrokeColor(colors.HexColor("#164147"))
            for radius in (37, 53, 69):
                c.circle(PAGE_W - 8 * mm, PAGE_H - 41 * mm, radius * mm, fill=0, stroke=1)
        else:
            c.setFillColor(WHITE)
            c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
            c.setStrokeColor(LINE)
            c.setLineWidth(0.6)
            c.line(doc.leftMargin, PAGE_H - 17 * mm, PAGE_W - doc.rightMargin, PAGE_H - 17 * mm)
            c.setFillColor(TEAL_DARK)
            c.setFont("AirSans-Bold", 7)
            c.drawString(doc.leftMargin, PAGE_H - 12.8 * mm, "AIRSHIELD")
            c.setFillColor(MUTED)
            c.setFont("AirSans", 6.5)
            c.drawRightString(PAGE_W - doc.rightMargin, PAGE_H - 12.8 * mm, self.spec.short_title)
            c.setStrokeColor(LINE)
            c.line(doc.leftMargin, 15 * mm, PAGE_W - doc.rightMargin, 15 * mm)
            c.setFillColor(MUTED)
            c.setFont("AirSans", 6.1)
            c.drawString(doc.leftMargin, 10 * mm, "INTERNAL HACKATHON DOCUMENT  •  Not a certification, legal opinion or production approval")
            c.drawRightString(PAGE_W - doc.rightMargin, 10 * mm, f"PAGE {doc.page - 1}")
        c.restoreState()


class Cover(Flowable):
    def __init__(self, spec: DocumentSpec):
        super().__init__()
        self.spec = spec

    def wrap(self, avail_width, avail_height):
        self.width = avail_width
        self.height = avail_height
        return avail_width, avail_height

    def draw(self):
        c = self.canv
        left = 4 * mm
        top = self.height - 12 * mm
        draw_shield(c, left, top - 18 * mm, 16 * mm)
        c.setFillColor(WHITE)
        c.setFont("AirSans-Bold", 12)
        c.drawString(left + 21 * mm, top - 8 * mm, "AIRSHIELD")
        c.setFillColor(colors.HexColor("#7BA5A7"))
        c.setFont("AirSans-Bold", 6.5)
        c.drawString(left + 21 * mm, top - 12 * mm, "PRIVATE AI CONTROL PLANE")

        badge_y = self.height - 55 * mm
        c.setFillColor(colors.HexColor("#123A40"))
        c.roundRect(left, badge_y, 78 * mm, 8 * mm, 4 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#8EE6D5"))
        c.setFont("AirSans-Bold", 6.3)
        c.drawCentredString(left + 39 * mm, badge_y + 2.7 * mm, self.spec.badge)

        title_y = badge_y - 24 * mm
        c.setFillColor(WHITE)
        c.setFont("AirSans-Bold", 31)
        for idx, line in enumerate(self.spec.title.split("\n")):
            c.drawString(left, title_y - idx * 14 * mm, line)

        subtitle_y = title_y - (len(self.spec.title.split("\n")) * 14 + 4) * mm
        c.setFillColor(colors.HexColor("#9BBABC"))
        c.setFont("AirSans", 10.5)
        for idx, line in enumerate(wrap_words(self.spec.subtitle, 66)):
            c.drawString(left, subtitle_y - idx * 5.5 * mm, line)

        statement_y = 78 * mm
        c.setFillColor(TEAL)
        c.roundRect(left, statement_y, 3 * mm, 28 * mm, 1.5 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("AirSans-Bold", 13)
        for idx, line in enumerate(wrap_words(self.spec.strapline, 38)[:3]):
            c.drawString(left + 9 * mm, statement_y + 18 * mm - idx * 7 * mm, line)

        labels = ["CAPTURE", "PROTECT", "AUTHORIZE", "PROVE"]
        pipe_y = 37 * mm
        for idx, label in enumerate(labels):
            x = left + idx * 41 * mm
            c.setFillColor(colors.HexColor("#123A40"))
            c.roundRect(x, pipe_y, 33 * mm, 13 * mm, 3 * mm, fill=1, stroke=0)
            c.setFillColor(TEAL if idx < 3 else colors.HexColor("#8EE6D5"))
            c.setFont("AirSans-Bold", 6.5)
            c.drawCentredString(x + 16.5 * mm, pipe_y + 5.2 * mm, label)
            if idx < 3:
                c.setStrokeColor(colors.HexColor("#2A5559"))
                c.line(x + 34 * mm, pipe_y + 6.5 * mm, x + 39 * mm, pipe_y + 6.5 * mm)

        c.setFillColor(colors.HexColor("#708F93"))
        c.setFont("AirSans", 7)
        c.drawString(left, 16 * mm, "Document set  •  24 August 2026  •  Internal hackathon build")
        c.drawRightString(self.width - left, 16 * mm, "CONTROLLED DISCUSSION DRAFT")


class Diagram(Flowable):
    def __init__(self, kind: str):
        super().__init__()
        self.kind = kind
        self.height = {"architecture": 99, "voice": 86, "vault": 84, "egress": 92}[kind] * mm

    def wrap(self, avail_width, avail_height):
        self.width = avail_width
        return avail_width, self.height

    def box(self, c, x, y, w, h, title, detail, fill=WHITE, stroke=LINE, accent=TEAL):
        c.setFillColor(fill)
        c.setStrokeColor(stroke)
        c.roundRect(x, y, w, h, 3 * mm, fill=1, stroke=1)
        c.setFillColor(accent)
        c.roundRect(x, y + h - 3 * mm, w, 3 * mm, 1.5 * mm, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("AirSans-Bold", 6.8)
        c.drawString(x + 3.5 * mm, y + h - 8.5 * mm, title)
        c.setFillColor(INK_2)
        c.setFont("AirSans", 5.9)
        chars = max(18, int(w / mm / 1.75))
        for idx, line in enumerate(wrap_words(detail, chars)[:3]):
            c.drawString(x + 3.5 * mm, y + h - 13 * mm - idx * 3.3 * mm, line)

    def draw(self):
        c = self.canv
        c.setFillColor(PALE)
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, self.width, self.height, 4 * mm, fill=1, stroke=1)
        if self.kind == "architecture":
            self.draw_architecture(c)
        elif self.kind == "voice":
            self.draw_voice(c)
        elif self.kind == "egress":
            self.draw_egress(c)
        else:
            self.draw_vault(c)

    def draw_architecture(self, c):
        c.setFillColor(INK)
        c.setFont("AirSans-Bold", 9)
        c.drawString(6 * mm, self.height - 9 * mm, "Logical architecture and controlled egress")
        gap = 4 * mm
        x = 6 * mm
        w = (self.width - 12 * mm - 3 * gap) / 4
        top = self.height - 34 * mm
        entries = [
            ("WEB / MOBILE", "Authenticated host and local raw display"),
            ("CONTACT CENTER", "Approved isolated media channels"),
            ("LEGACY APP", "Reverse proxy, SDK or sidecar"),
            ("EVENT / BATCH", "Restricted adapter and policy context"),
        ]
        for idx, (title, detail) in enumerate(entries):
            self.box(c, x + idx * (w + gap), top, w, 17 * mm, title, detail, WHITE, LINE, BLUE)
        gy = top - 25 * mm
        self.box(c, 18 * mm, gy, self.width - 36 * mm, 17 * mm, "TRUSTED GATEWAY + AIRSHIELD CONTROL", "OIDC, origin, tenant, self-hosted voice, detection, policy, token vault and final receipt", MINT, colors.HexColor("#A7E9DC"), TEAL)
        for idx in range(4):
            arrow(c, x + idx * (w + gap) + w / 2, top, self.width / 2, gy + 17 * mm)
        by = 7 * mm
        bw = (self.width - 20 * mm) / 3
        bottom = [
            ("ENCRYPTED VAULT", "Protected token mappings and retention", VIOLET),
            ("APPROVED AI / RIA", "Protected meaning plus receipt only", TEAL),
            ("ACTION BROKER", "Minimum fields to system of record", AMBER),
        ]
        for idx, (title, detail, accent) in enumerate(bottom):
            bx = 6 * mm + idx * (bw + 4 * mm)
            self.box(c, bx, by, bw, 18 * mm, title, detail, WHITE, LINE, accent)
            arrow(c, self.width / 2, gy, bx + bw / 2, by + 18 * mm, colors.HexColor("#7EA39E"))

    def draw_voice(self, c):
        c.setFillColor(INK)
        c.setFont("AirSans-Bold", 9)
        c.drawString(6 * mm, self.height - 9 * mm, "Voice path: interim is provisional; final allow governs egress")
        entries = [
            ("1  CAPTURE", "getUserMedia + MediaRecorder"),
            ("2  GATEWAY", "OIDC, origin, tenant and limits"),
            ("3  ASR", "Self-hosted English faster-whisper"),
            ("4  SPEAKERS", "Local continuity; identity from host"),
            ("5  PROTECT", "Detect, tokenize, policy and receipt"),
            ("6  FINALIZE", "Full-turn recheck before allow"),
        ]
        gap = 4 * mm
        w = (self.width - 16 * mm - 2 * gap) / 3
        h = 22 * mm
        for idx, (title, detail) in enumerate(entries):
            row, col = divmod(idx, 3)
            x = 6 * mm + col * (w + gap)
            y = self.height - 19 * mm - (row + 1) * h - row * 10 * mm
            self.box(c, x, y, w, h, title, detail, MINT if idx in {4, 5} else WHITE, colors.HexColor("#BFE3DC") if idx in {4, 5} else LINE, TEAL if idx in {4, 5} else BLUE)
            if col < 2:
                arrow(c, x + w, y + h / 2, x + w + gap, y + h / 2)
        arrow(c, self.width - 8 * mm, self.height - 31 * mm, self.width - 8 * mm, 29 * mm)

    def draw_egress(self, c):
        c.setFillColor(INK)
        c.setFont("AirSans-Bold", 9)
        c.drawString(6 * mm, self.height - 9 * mm, "EgressSeal transaction: protect, bind destination, measure context, prove and act")
        gap = 3 * mm
        w = (self.width - 12 * mm - 4 * gap) / 5
        y = self.height - 45 * mm
        entries = [
            ("1  PROTECT", "Mask/tokenize + upstream receipt", BLUE_PALE, BLUE),
            ("2  SWITCH", "Exact destination route is security context", WHITE, TEAL),
            ("3  FENCE", "Cumulative linkage/mosaic risk", AMBER_PALE, AMBER),
            ("4  SEAL", "Signed digest, policy, route, risk and expiry", MINT, TEAL),
            ("5  ACTION", "One token-aware connector operation", WHITE, VIOLET),
        ]
        for idx, (title, detail, fill, accent) in enumerate(entries):
            x = 6 * mm + idx * (w + gap)
            self.box(c, x, y, w, 27 * mm, title, detail, fill, LINE, accent)
            if idx < len(entries) - 1:
                arrow(c, x + w, y + 13.5 * mm, x + w + gap, y + 13.5 * mm)

        bottom_y = 8 * mm
        third = (self.width - 20 * mm) / 3
        bottom = [
            ("ALLOW", "Approved destination + acceptable ContextFence + matching receipt", MINT, TEAL),
            ("REVIEW / BLOCK", "Destination, context, receipt, digest or policy mismatch", AMBER_PALE, AMBER),
            ("SAFEACTION RECEIPT", "Connector-only resolution; raw values never return to model", BLUE_PALE, BLUE),
        ]
        for idx, (title, detail, fill, accent) in enumerate(bottom):
            x = 6 * mm + idx * (third + 4 * mm)
            self.box(c, x, bottom_y, third, 20 * mm, title, detail, fill, LINE, accent)
        arrow(c, 6 * mm + 3 * (w + gap) + w / 2, y, 6 * mm + third / 2, bottom_y + 20 * mm, TEAL)
        arrow(c, 6 * mm + 2 * (w + gap) + w / 2, y, 10 * mm + third + third / 2, bottom_y + 20 * mm, AMBER)
        arrow(c, 6 * mm + 4 * (w + gap) + w / 2, y, 14 * mm + 2 * third + third / 2, bottom_y + 20 * mm, BLUE)

    def draw_vault(self, c):
        c.setFillColor(INK)
        c.setFont("AirSans-Bold", 9)
        c.drawString(6 * mm, self.height - 9 * mm, "Per-record token-vault encryption and controlled resolution")
        top_y = self.height - 39 * mm
        gap = 5 * mm
        w = (self.width - 12 * mm - 3 * gap) / 4
        entries = [
            ("RAW ENTITY", "Inside trusted control plane only", BLUE_PALE, BLUE),
            ("AES-256-GCM", "Fresh 256-bit DEK + 96-bit nonce + AAD", MINT, TEAL),
            ("KEY PROVIDER", "Azure Key Vault or OpenBao wraps DEK", AMBER_PALE, AMBER),
            ("DATABASE", "Ciphertext/tag, nonce, wrapped DEK, metadata", WHITE, VIOLET),
        ]
        for idx, (title, detail, fill, accent) in enumerate(entries):
            x = 6 * mm + idx * (w + gap)
            self.box(c, x, top_y, w, 23 * mm, title, detail, fill, LINE, accent)
            if idx < 3:
                arrow(c, x + w, top_y + 11.5 * mm, x + w + gap, top_y + 11.5 * mm)
        y = 8 * mm
        self.box(c, 24 * mm, y, self.width - 48 * mm, 19 * mm, "CONTROLLED REIDENTIFICATION", "Purpose + ticket → distinct approver → short expiry → original requester → one-time minimum release → evidence", WHITE, colors.HexColor("#C9DDDA"), TEAL)
        arrow(c, self.width - 6 * mm - w / 2, top_y, self.width / 2, y + 19 * mm, colors.HexColor("#7EA39E"))


class Rule(Flowable):
    def __init__(self, color=LINE, thickness=0.7, height=8):
        super().__init__()
        self.color = color
        self.thickness = thickness
        self.height = height

    def wrap(self, avail_width, avail_height):
        self.width = avail_width
        return avail_width, self.height

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.height / 2, self.width, self.height / 2)


def get_styles():
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="AirSans", fontSize=8.2, leading=11.8, textColor=INK, spaceAfter=5.2, allowWidows=0, allowOrphans=0),
        "lead": ParagraphStyle("Lead", parent=base["BodyText"], fontName="AirSans", fontSize=9.7, leading=13.8, textColor=INK, spaceAfter=9),
        "Section": ParagraphStyle("Section", parent=base["Heading1"], fontName="AirSans-Bold", fontSize=16.5, leading=20, textColor=NAVY, spaceBefore=7, spaceAfter=7, keepWithNext=True),
        "H2": ParagraphStyle("H2", parent=base["Heading2"], fontName="AirSans-Bold", fontSize=10.7, leading=13.6, textColor=TEAL_DARK, spaceBefore=7, spaceAfter=4, keepWithNext=True),
        "H3": ParagraphStyle("H3", parent=base["Heading3"], fontName="AirSans-Bold", fontSize=9, leading=11.5, textColor=INK, spaceBefore=6, spaceAfter=3, keepWithNext=True),
        "bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName="AirSans", fontSize=8, leading=11.3, leftIndent=9, textColor=INK, spaceAfter=2.4),
        "quote": ParagraphStyle("Quote", parent=base["BodyText"], fontName="AirSans-Bold", fontSize=9.1, leading=13.1, textColor=TEAL_DARK),
        "table_head": ParagraphStyle("TableHead", parent=base["BodyText"], fontName="AirSans-Bold", fontSize=6.5, leading=8.2, textColor=WHITE),
        "table": ParagraphStyle("TableBody", parent=base["BodyText"], fontName="AirSans", fontSize=6.35, leading=8.45, textColor=INK),
        "code": ParagraphStyle("Code", parent=base["Code"], fontName="AirMono", fontSize=6.5, leading=9, textColor=colors.HexColor("#D9F4EE"), leftIndent=0, rightIndent=0),
        "toc_title": ParagraphStyle("TOCTitle", parent=base["Heading1"], fontName="AirSans-Bold", fontSize=22, leading=26, textColor=NAVY, spaceAfter=8),
        "toc_lead": ParagraphStyle("TOCLead", parent=base["BodyText"], fontName="AirSans", fontSize=9.4, leading=13.2, textColor=INK_2, spaceAfter=8),
    }


def inline_markup(value: str) -> str:
    value = html.escape(value.strip())
    value = re.sub(r"`([^`]+)`", r'<font name="AirMono" color="#087D6F">\1</font>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", value)
    return value


def make_callout(text: str, styles) -> Table:
    table = Table([["", Paragraph(inline_markup(text), styles["quote"])]], colWidths=[3 * mm, 159 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), TEAL),
        ("BACKGROUND", (1, 0), (1, -1), MINT),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B9E6DD")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (1, 0), (1, -1), 10),
        ("RIGHTPADDING", (1, 0), (1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return table


def make_table(rows: list[list[str]], width: float, styles) -> Table:
    cols = max(len(row) for row in rows)
    rows = [row + [""] * (cols - len(row)) for row in rows]
    data = []
    for row_idx, row in enumerate(rows):
        style = styles["table_head"] if row_idx == 0 else styles["table"]
        data.append([Paragraph(inline_markup(cell), style) for cell in row])
    if cols == 2:
        widths = [width * 0.31, width * 0.69]
    elif cols == 3:
        widths = [width * 0.22, width * 0.32, width * 0.46]
    elif cols == 4:
        widths = [width * 0.15, width * 0.23, width * 0.28, width * 0.34]
    else:
        widths = [width / cols] * cols
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_2),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for idx in range(1, len(data)):
        commands.append(("BACKGROUND", (0, idx), (-1, idx), WHITE if idx % 2 else PALE))
    table.setStyle(TableStyle(commands))
    return table


def make_code(text: str, width: float, styles) -> Table:
    pre = Preformatted(text.rstrip(), styles["code"], maxLineLength=100)
    table = Table([[pre]], colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY_2),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#21424B")),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def parse_markdown(markdown: str, doc: AirShieldDoc, styles) -> list[Flowable]:
    story: list[Flowable] = [Cover(doc.spec), PageBreak()]
    story.extend([
        Paragraph("Contents", styles["toc_title"]),
        Paragraph(doc.spec.subtitle, styles["toc_lead"]),
        Rule(TEAL, 1.2, 10),
    ])
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("TOC1", fontName="AirSans", fontSize=8, leading=12.3, textColor=INK, leftIndent=0, firstLineIndent=0)]
    story.extend([toc, PageBreak()])

    lines = markdown.splitlines()
    start = next((idx for idx, line in enumerate(lines) if line.startswith("## ")), 0)
    lines = lines[start:]
    i = 0
    section_count = 0
    first_after_section = False

    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i].rstrip())
                i += 1
            i += 1
            story.extend([Spacer(1, 1.5 * mm), make_code("\n".join(code_lines), doc.width, styles), Spacer(1, 2.5 * mm)])
            first_after_section = False
            continue
        if stripped == "[[ARCHITECTURE_DIAGRAM]]":
            story.extend([Diagram("architecture"), Spacer(1, 3 * mm)])
            i += 1
            continue
        if stripped == "[[VOICE_DIAGRAM]]":
            story.extend([Diagram("voice"), Spacer(1, 3 * mm)])
            i += 1
            continue
        if stripped == "[[VAULT_DIAGRAM]]":
            story.extend([Diagram("vault"), Spacer(1, 3 * mm)])
            i += 1
            continue
        if stripped == "[[EGRESSSEAL_DIAGRAM]]":
            story.extend([Diagram("egress"), Spacer(1, 3 * mm)])
            i += 1
            continue
        if stripped.startswith("## "):
            section_count += 1
            if section_count > 1:
                story.append(CondPageBreak(55 * mm))
            title = stripped[3:].strip()
            story.extend([Paragraph(inline_markup(title), styles["Section"]), Rule(TEAL, 1.1, 8)])
            first_after_section = True
            i += 1
            continue
        if stripped.startswith("### "):
            story.append(Paragraph(inline_markup(stripped[4:]), styles["H2"]))
            i += 1
            continue
        if stripped.startswith("#### "):
            story.append(Paragraph(inline_markup(stripped[5:]), styles["H3"]))
            i += 1
            continue
        if stripped.startswith("> "):
            values = []
            while i < len(lines) and lines[i].strip().startswith("> "):
                values.append(lines[i].strip()[2:])
                i += 1
            story.extend([make_callout(" ".join(values), styles), Spacer(1, 3 * mm)])
            first_after_section = False
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|", lines[i + 1]):
            rows = [[cell.strip() for cell in stripped.strip("|").split("|")]]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([cell.strip() for cell in lines[i].strip().strip("|").split("|")])
                i += 1
            story.extend([Spacer(1, 1.5 * mm), make_table(rows, doc.width, styles), Spacer(1, 2.5 * mm)])
            first_after_section = False
            continue
        if re.match(r"^[-*] ", stripped) or stripped.startswith("- ["):
            items = []
            while i < len(lines):
                current = lines[i].strip()
                if not (re.match(r"^[-*] ", current) or current.startswith("- [")):
                    break
                value = re.sub(r"^[-*] ", "", current)
                value = value.replace("[ ]", "☐", 1).replace("[x]", "☑", 1)
                items.append(ListItem(Paragraph(inline_markup(value), styles["bullet"]), leftIndent=8))
                i += 1
            story.append(ListFlowable(items, bulletType="bullet", start="circle", leftIndent=12, bulletFontName="AirSans", bulletFontSize=5, bulletColor=TEAL_DARK, spaceAfter=4))
            first_after_section = False
            continue
        if re.match(r"^\d+\. ", stripped):
            items = []
            start_number = int(stripped.split(".", 1)[0])
            while i < len(lines) and re.match(r"^\d+\. ", lines[i].strip()):
                value = re.sub(r"^\d+\. ", "", lines[i].strip())
                items.append(ListItem(Paragraph(inline_markup(value), styles["bullet"]), leftIndent=8))
                i += 1
            story.append(ListFlowable(items, bulletType="1", start=start_number, leftIndent=15, bulletFontName="AirSans-Bold", bulletFontSize=7, bulletColor=TEAL_DARK, spaceAfter=4))
            first_after_section = False
            continue
        if stripped == "---":
            story.append(Rule())
            i += 1
            continue

        paragraph_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt:
                i += 1
                break
            if nxt.startswith(("#", ">", "|", "```", "[[")) or nxt == "---" or re.match(r"^[-*] ", nxt) or re.match(r"^\d+\. ", nxt):
                break
            paragraph_lines.append(nxt)
            i += 1
        style = styles["lead"] if first_after_section else styles["body"]
        story.append(Paragraph(inline_markup(" ".join(paragraph_lines)), style))
        first_after_section = False

    return story


def build(spec: DocumentSpec) -> None:
    spec.output.parent.mkdir(parents=True, exist_ok=True)
    styles = get_styles()
    doc = AirShieldDoc(
        str(spec.output),
        spec,
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=23 * mm,
        bottomMargin=20 * mm,
        title=spec.short_title,
        author="AirShield",
        subject=spec.subject,
    )
    story = parse_markdown(spec.source.read_text(encoding="utf-8"), doc, styles)
    doc.multiBuild(story)
    print(spec.output)


if __name__ == "__main__":
    for document in SPECS:
        build(document)
