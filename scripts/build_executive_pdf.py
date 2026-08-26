#!/usr/bin/env python3
"""Build the client-ready AirShield executive architecture/business PDF."""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

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
RED = colors.HexColor("#DF5960")
RED_PALE = colors.HexColor("#FDE9EA")
WHITE = colors.white

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "AIRSHIELD_EXECUTIVE_ARCHITECTURE_AND_BUSINESS.md"
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "docs" / "AirShield_Executive_Architecture_and_Business_Dossier.pdf"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("AirSans", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("AirSans-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("AirMono", str(FONT_DIR / "DejaVuSansMono.ttf")))
pdfmetrics.registerFontFamily("AirSans", normal="AirSans", bold="AirSans-Bold")


class AirShieldDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, **kwargs)
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
            id="content",
        )
        self.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=draw_page))

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "H1":
            text = flowable.getPlainText()
            key = "section-" + re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=0, closed=False)
            self.notify("TOCEntry", (0, text, self.page, key))


class Rule(Flowable):
    def __init__(self, color=LINE, thickness=0.7, space=8):
        super().__init__()
        self.color = color
        self.thickness = thickness
        self.height = space

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.height / 2, self._availWidth, self.height / 2)

    def wrap(self, availWidth, availHeight):
        self._availWidth = availWidth
        return availWidth, self.height


class CoverPage(Flowable):
    def __init__(self, width: float, height: float):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = availHeight
        return availWidth, availHeight

    def draw_shield(self, c: Canvas, x: float, y: float, size: float):
        p = c.beginPath()
        p.moveTo(x + size * 0.5, y + size)
        p.lineTo(x + size * 0.92, y + size * 0.82)
        p.lineTo(x + size * 0.84, y + size * 0.32)
        p.curveTo(x + size * 0.75, y + size * 0.12, x + size * 0.60, y + size * 0.03, x + size * 0.5, y)
        p.curveTo(x + size * 0.40, y + size * 0.03, x + size * 0.25, y + size * 0.12, x + size * 0.16, y + size * 0.32)
        p.lineTo(x + size * 0.08, y + size * 0.82)
        p.close()
        c.setFillColor(colors.HexColor("#0C353B"))
        c.setStrokeColor(TEAL)
        c.setLineWidth(2)
        c.drawPath(p, fill=1, stroke=1)
        c.setStrokeColor(WHITE)
        c.setLineWidth(2.2)
        c.line(x + size * 0.29, y + size * 0.51, x + size * 0.44, y + size * 0.36)
        c.line(x + size * 0.44, y + size * 0.36, x + size * 0.72, y + size * 0.66)

    def draw(self):
        c = self.canv
        c.saveState()
        left = 4 * mm
        top = self.height - 12 * mm
        self.draw_shield(c, left, top - 18 * mm, 16 * mm)
        c.setFillColor(WHITE)
        c.setFont("AirSans-Bold", 12)
        c.drawString(left + 21 * mm, top - 8 * mm, "AIRSHIELD")
        c.setFillColor(colors.HexColor("#7BA5A7"))
        c.setFont("AirSans-Bold", 6.5)
        c.drawString(left + 21 * mm, top - 12 * mm, "PRIVATE AI CONTROL PLANE")

        badge_y = self.height - 54 * mm
        c.setFillColor(colors.HexColor("#123A40"))
        c.roundRect(left, badge_y, 72 * mm, 8 * mm, 4 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#8EE6D5"))
        c.setFont("AirSans-Bold", 6.5)
        c.drawCentredString(left + 36 * mm, badge_y + 2.7 * mm, "EXECUTIVE  •  ARCHITECTURE  •  COMMERCIAL")

        c.setFillColor(WHITE)
        c.setFont("AirSans-Bold", 31)
        c.drawString(left, badge_y - 23 * mm, "Executive Architecture")
        c.drawString(left, badge_y - 36 * mm, "& Business Dossier")
        c.setFillColor(colors.HexColor("#9BBABC"))
        c.setFont("AirSans", 12)
        c.drawString(left, badge_y - 49 * mm, "A privacy firewall for AI voice and text workflows")

        statement_y = badge_y - 80 * mm
        c.setFillColor(TEAL)
        c.roundRect(left, statement_y, 3 * mm, 30 * mm, 1.5 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("AirSans-Bold", 17)
        c.drawString(left + 9 * mm, statement_y + 18 * mm, "Keep the intelligence.")
        c.drawString(left + 9 * mm, statement_y + 9 * mm, "Remove the identifiers.")

        c.setFillColor(colors.HexColor("#9BBABC"))
        c.setFont("AirSans", 8.5)
        cover_lines = [
            "For executive, client, architecture, security, privacy, and product discussions",
            "English-first • self-hosted • provider-neutral • Azure-private or portable Kubernetes",
        ]
        for idx, line in enumerate(cover_lines):
            c.drawString(left, statement_y - (13 + idx * 5) * mm, line)

        # Decorative privacy pipeline.
        pipe_y = 35 * mm
        labels = ["CAPTURE", "PROTECT", "AUTHORIZE", "PROVE"]
        for idx, label in enumerate(labels):
            x = left + idx * 41 * mm
            c.setFillColor(colors.HexColor("#123A40"))
            c.roundRect(x, pipe_y, 33 * mm, 13 * mm, 3 * mm, fill=1, stroke=0)
            c.setFillColor(TEAL if idx < 3 else colors.HexColor("#8EE6D5"))
            c.setFont("AirSans-Bold", 6.5)
            c.drawCentredString(x + 16.5 * mm, pipe_y + 5.2 * mm, label)
            if idx < len(labels) - 1:
                c.setStrokeColor(colors.HexColor("#2A5559"))
                c.setLineWidth(1)
                c.line(x + 34 * mm, pipe_y + 6.5 * mm, x + 39 * mm, pipe_y + 6.5 * mm)

        c.setFillColor(colors.HexColor("#708F93"))
        c.setFont("AirSans", 7)
        c.drawString(left, 16 * mm, "Client-ready discussion document  •  Version 1.0  •  20 August 2026")
        c.drawRightString(self.width - left, 16 * mm, "CONFIDENTIAL DISCUSSION DRAFT")
        c.restoreState()


class AtAGlance(Flowable):
    def __init__(self):
        super().__init__()
        self.height = 42 * mm

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return availWidth, self.height

    def draw(self):
        c = self.canv
        items = [
            ("PRE-EGRESS", "Protect before AI receives raw identity", TEAL),
            ("PRIVATE", "Self-hosted speech and customer key custody", BLUE),
            ("PORTABLE", "Azure-private or cloud-neutral Kubernetes", AMBER),
            ("EVIDENCE", "Signed decisions and controlled reidentification", colors.HexColor("#7757C8")),
        ]
        gap = 3 * mm
        box_w = (self.width - gap * 3) / 4
        for idx, (title, body, accent) in enumerate(items):
            x = idx * (box_w + gap)
            c.setFillColor(WHITE)
            c.setStrokeColor(LINE)
            c.roundRect(x, 0, box_w, self.height - 2 * mm, 3 * mm, fill=1, stroke=1)
            c.setFillColor(accent)
            c.roundRect(x, self.height - 6 * mm, box_w, 4 * mm, 2 * mm, fill=1, stroke=0)
            c.setFillColor(INK)
            c.setFont("AirSans-Bold", 7)
            c.drawString(x + 4 * mm, self.height - 13 * mm, title)
            text = c.beginText(x + 4 * mm, self.height - 20 * mm)
            text.setFont("AirSans", 6.7)
            text.setFillColor(INK_2)
            for line in wrap_words(body, 26):
                text.textLine(line)
            c.drawText(text)


class BusinessFlowDiagram(Flowable):
    def __init__(self):
        super().__init__()
        self.height = 83 * mm

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return availWidth, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(PALE)
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, self.width, self.height, 4 * mm, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("AirSans-Bold", 9)
        c.drawString(6 * mm, self.height - 9 * mm, "Operational privacy flow")
        steps = [
            ("1", "AUTHENTICATE", "Host SSO / OTP / IVR"),
            ("2", "CAPTURE", "Voice or application text"),
            ("3", "TRANSCRIBE", "Self-hosted English ASR"),
            ("4", "DETECT", "PII / PHI / PCI / secrets"),
            ("5", "PROTECT", "Mask, tokenize or block"),
            ("6", "AUTHORIZE", "Tenant + destination policy"),
            ("7", "USE AI", "Protected meaning only"),
            ("8", "PROVE", "Signed receipt and evidence"),
        ]
        gap = 4 * mm
        cols = 4
        box_w = (self.width - 12 * mm - gap * (cols - 1)) / cols
        box_h = 24 * mm
        for idx, (number, title, detail) in enumerate(steps):
            row = idx // cols
            col = idx % cols
            x = 6 * mm + col * (box_w + gap)
            y = self.height - 18 * mm - (row + 1) * box_h - row * 7 * mm
            c.setFillColor(WHITE)
            c.setStrokeColor(colors.HexColor("#C9DDDA"))
            c.roundRect(x, y, box_w, box_h, 3 * mm, fill=1, stroke=1)
            c.setFillColor(TEAL_DARK)
            c.circle(x + 6 * mm, y + box_h - 6 * mm, 3.2 * mm, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont("AirSans-Bold", 6.5)
            c.drawCentredString(x + 6 * mm, y + box_h - 8 * mm, number)
            c.setFillColor(INK)
            c.setFont("AirSans-Bold", 6.7)
            c.drawString(x + 11 * mm, y + box_h - 7.8 * mm, title)
            c.setFillColor(INK_2)
            c.setFont("AirSans", 6.2)
            lines = wrap_words(detail, 23)
            for n, line in enumerate(lines[:3]):
                c.drawString(x + 4 * mm, y + 8 * mm - n * 3.5 * mm, line)
            if idx < len(steps) - 1 and col < cols - 1:
                arrow(c, x + box_w + 0.8 * mm, y + box_h / 2, x + box_w + gap - 0.8 * mm, y + box_h / 2, TEAL)
        # Turn connector.
        arrow(c, self.width - 8 * mm, self.height - 30 * mm, self.width - 8 * mm, 30 * mm, TEAL)


class ArchitectureDiagram(Flowable):
    def __init__(self):
        super().__init__()
        self.height = 112 * mm

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return availWidth, self.height

    def box(self, c, x, y, w, h, title, detail, fill=WHITE, stroke=LINE, accent=TEAL):
        c.setFillColor(fill)
        c.setStrokeColor(stroke)
        c.roundRect(x, y, w, h, 3 * mm, fill=1, stroke=1)
        c.setFillColor(accent)
        c.roundRect(x, y + h - 3 * mm, w, 3 * mm, 1.5 * mm, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("AirSans-Bold", 7)
        c.drawString(x + 4 * mm, y + h - 9 * mm, title)
        c.setFillColor(INK_2)
        c.setFont("AirSans", 6.1)
        chars = max(18, int((w / mm) / 1.8))
        for i, line in enumerate(wrap_words(detail, chars)[:2]):
            c.drawString(x + 4 * mm, y + h - 13 * mm - i * 3.2 * mm, line)

    def draw(self):
        c = self.canv
        c.setFillColor(PALE)
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, self.width, self.height, 4 * mm, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("AirSans-Bold", 9)
        c.drawString(6 * mm, self.height - 9 * mm, "AirShield logical architecture and trust boundaries")

        x0 = 6 * mm
        gap = 4 * mm
        top_y = self.height - 34 * mm
        channel_w = (self.width - 12 * mm - gap * 3) / 4
        channels = [("WEB / MOBILE", "Authenticated host UI"), ("TELEPHONY", "Approved media adapter"), ("LEGACY", "Proxy or sidecar"), ("BATCH / EVENTS", "Restricted adapter")]
        for idx, (title, detail) in enumerate(channels):
            self.box(c, x0 + idx * (channel_w + gap), top_y, channel_w, 17 * mm, title, detail, WHITE, LINE, BLUE)

        gateway_y = top_y - 27 * mm
        gateway_w = self.width - 36 * mm
        self.box(c, 18 * mm, gateway_y, gateway_w, 18 * mm, "TRUSTED WSS / API GATEWAY", "OIDC, exact origin and tenant, bounded protocol, rate and size limits", colors.HexColor("#E9F7F4"), colors.HexColor("#A7E9DC"), TEAL)
        for idx in range(4):
            cx = x0 + idx * (channel_w + gap) + channel_w / 2
            arrow(c, cx, top_y, cx, gateway_y + 18 * mm, TEAL)

        mid_y = gateway_y - 25 * mm
        half_w = (self.width - 18 * mm) / 2
        self.box(c, 6 * mm, mid_y, half_w, 19 * mm, "SELF-HOSTED VOICE EDGE", "faster-whisper, optional diarization, provisional transcript pairs", WHITE, LINE, BLUE)
        self.box(c, 12 * mm + half_w, mid_y, half_w, 19 * mm, "PYTHON CONTROL PLANE", "Tenant policy, detection, destination authorization and evidence", WHITE, LINE, TEAL)
        gateway_cx = self.width / 2
        edge_cx = 6 * mm + half_w / 2
        cp_x = 12 * mm + half_w + half_w / 2
        arrow(c, gateway_cx, gateway_y, edge_cx, mid_y + 19 * mm, TEAL)
        arrow(c, gateway_cx, gateway_y, cp_x, mid_y + 19 * mm, TEAL)
        arrow(c, 6 * mm + half_w, mid_y + 9.5 * mm, 12 * mm + half_w, mid_y + 9.5 * mm, TEAL)

        bottom_y = 2 * mm
        bw = (self.width - 20 * mm) / 3
        self.box(c, 6 * mm, bottom_y, bw, 19 * mm, "VAULT + POSTGRESQL", "Encrypted token maps and tenant metadata", WHITE, LINE, colors.HexColor("#7757C8"))
        self.box(c, 10 * mm + bw, bottom_y, bw, 19 * mm, "KEYS + EVIDENCE", "Key wrapping, signing and receipt chains", WHITE, LINE, AMBER)
        self.box(c, 14 * mm + 2 * bw, bottom_y, bw, 19 * mm, "APPROVED AI", "Protected content after authorization", WHITE, LINE, TEAL)
        for target_x in [6 * mm + bw / 2, 10 * mm + bw + bw / 2, 14 * mm + 2 * bw + bw / 2]:
            arrow(c, cp_x, mid_y, target_x, bottom_y + 19 * mm, colors.HexColor("#7EA39E"))


class IntegrationDiagram(Flowable):
    def __init__(self):
        super().__init__()
        self.height = 76 * mm

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return availWidth, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(PALE)
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, self.width, self.height, 4 * mm, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("AirSans-Bold", 9)
        c.drawString(6 * mm, self.height - 9 * mm, "Legacy integration: wrap before rewrite")
        left = 5 * mm
        source_w = 30 * mm
        source_h = 13 * mm
        sources = ["MONOLITH", "CONTACT CENTER", "BATCH / ETL", "EVENT BUS"]
        y0 = self.height - 27 * mm
        for idx, label in enumerate(sources):
            y = y0 - idx * 14 * mm
            c.setFillColor(WHITE)
            c.setStrokeColor(LINE)
            c.roundRect(left, y, source_w, source_h - 2 * mm, 2 * mm, fill=1, stroke=1)
            c.setFillColor(INK)
            c.setFont("AirSans-Bold", 6.4)
            c.drawCentredString(left + source_w / 2, y + 3.8 * mm, label)

        adapter_x = left + source_w + 5 * mm
        adapter_w = 41 * mm
        c.setFillColor(BLUE_PALE)
        c.setStrokeColor(colors.HexColor("#B9CCF0"))
        c.roundRect(adapter_x, 13 * mm, adapter_w, 49 * mm, 4 * mm, fill=1, stroke=1)
        c.setFillColor(BLUE)
        c.setFont("AirSans-Bold", 8)
        c.drawCentredString(adapter_x + adapter_w / 2, 53 * mm, "THIN ADAPTER LAYER")
        c.setFillColor(INK_2)
        c.setFont("AirSans", 6.2)
        for i, line in enumerate(["Reverse proxy / sidecar", "Media-stream connector", "Queue consumer / producer", "Identity broker", "Receipt propagation"]):
            c.drawCentredString(adapter_x + adapter_w / 2, 45 * mm - i * 6 * mm, line)
        for idx in range(4):
            y = y0 - idx * 14 * mm + (source_h - 2 * mm) / 2
            arrow(c, left + source_w, y, adapter_x, 37.5 * mm, BLUE)

        shield_x = adapter_x + adapter_w + 5 * mm
        shield_w = 31 * mm
        c.setFillColor(MINT)
        c.setStrokeColor(colors.HexColor("#A7E9DC"))
        c.roundRect(shield_x, 22 * mm, shield_w, 31 * mm, 4 * mm, fill=1, stroke=1)
        c.setFillColor(TEAL_DARK)
        c.setFont("AirSans-Bold", 8)
        c.drawCentredString(shield_x + shield_w / 2, 43 * mm, "AIRSHIELD")
        c.setFont("AirSans", 6.1)
        c.drawCentredString(shield_x + shield_w / 2, 35 * mm, "Protect + authorize")
        c.drawCentredString(shield_x + shield_w / 2, 29 * mm, "Tokenize + prove")
        arrow(c, adapter_x + adapter_w, 37.5 * mm, shield_x, 37.5 * mm, TEAL)

        ai_x = shield_x + shield_w + 5 * mm
        ai_w = self.width - ai_x - 5 * mm
        c.setFillColor(WHITE)
        c.setStrokeColor(LINE)
        c.roundRect(ai_x, 22 * mm, ai_w, 31 * mm, 4 * mm, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("AirSans-Bold", 7)
        c.drawCentredString(ai_x + ai_w / 2, 43 * mm, "APPROVED AI / CLOUD")
        c.setFillColor(INK_2)
        c.setFont("AirSans", 6)
        c.drawCentredString(ai_x + ai_w / 2, 34 * mm, "Protected content")
        c.drawCentredString(ai_x + ai_w / 2, 28 * mm, "Receipt-linked result")
        arrow(c, shield_x + shield_w, 37.5 * mm, ai_x, 37.5 * mm, TEAL)


class DifferentiationGrid(Flowable):
    def __init__(self):
        super().__init__()
        self.height = 62 * mm

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        return availWidth, self.height

    def draw(self):
        c = self.canv
        items = [
            ("PRE-EGRESS", "Control runs before the destination model"),
            ("VOICE-FIRST", "Live raw versus protected proof"),
            ("IDENTITY-SAFE", "Host trust separated from diarization"),
            ("REVERSIBLE", "Purpose-bound dual-control reidentification"),
            ("PORTABLE", "Azure-private and cloud-neutral profiles"),
            ("EVIDENCE", "Signed tenant decision chains"),
        ]
        gap = 4 * mm
        box_w = (self.width - gap * 2) / 3
        box_h = 25 * mm
        for idx, (title, detail) in enumerate(items):
            row, col = divmod(idx, 3)
            x = col * (box_w + gap)
            y = self.height - (row + 1) * box_h - row * 5 * mm
            c.setFillColor(MINT if idx in {0, 1, 5} else WHITE)
            c.setStrokeColor(colors.HexColor("#BFE3DC") if idx in {0, 1, 5} else LINE)
            c.roundRect(x, y, box_w, box_h, 3 * mm, fill=1, stroke=1)
            c.setFillColor(TEAL_DARK)
            c.setFont("AirSans-Bold", 7)
            c.drawString(x + 4 * mm, y + 16 * mm, title)
            c.setFillColor(INK_2)
            c.setFont("AirSans", 6.3)
            for n, line in enumerate(wrap_words(detail, 29)[:2]):
                c.drawString(x + 4 * mm, y + 9 * mm - n * 3.5 * mm, line)


def wrap_words(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def arrow(c: Canvas, x1: float, y1: float, x2: float, y2: float, color):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(1.1)
    c.line(x1, y1, x2, y2)
    angle_vertical = abs(y2 - y1) > abs(x2 - x1)
    if angle_vertical:
        direction = 1 if y2 > y1 else -1
        p = c.beginPath()
        p.moveTo(x2, y2)
        p.lineTo(x2 - 1.7 * mm, y2 - direction * 2.5 * mm)
        p.lineTo(x2 + 1.7 * mm, y2 - direction * 2.5 * mm)
    else:
        direction = 1 if x2 > x1 else -1
        p = c.beginPath()
        p.moveTo(x2, y2)
        p.lineTo(x2 - direction * 2.5 * mm, y2 - 1.7 * mm)
        p.lineTo(x2 - direction * 2.5 * mm, y2 + 1.7 * mm)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def draw_page(c: Canvas, doc):
    c.saveState()
    c.setTitle("AirShield Executive Architecture & Business Dossier")
    c.setAuthor("AirShield")
    c.setSubject("Architecture, business flow, integration, technology, differentiation and executive case")
    if doc.page == 1:
        c.setFillColor(NAVY)
        c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#0B2B31"))
        c.circle(PAGE_W + 18 * mm, PAGE_H - 38 * mm, 76 * mm, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#164147"))
        c.setLineWidth(1)
        for radius in (38, 54, 70):
            c.circle(PAGE_W - 8 * mm, PAGE_H - 42 * mm, radius * mm, fill=0, stroke=1)
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
        c.drawRightString(PAGE_W - doc.rightMargin, PAGE_H - 12.8 * mm, "EXECUTIVE ARCHITECTURE & BUSINESS DOSSIER")
        c.setStrokeColor(LINE)
        c.line(doc.leftMargin, 15 * mm, PAGE_W - doc.rightMargin, 15 * mm)
        c.setFillColor(MUTED)
        c.setFont("AirSans", 6.2)
        c.drawString(doc.leftMargin, 10 * mm, "CONFIDENTIAL DISCUSSION DRAFT  •  Not a compliance certificate or legal opinion")
        c.drawRightString(PAGE_W - doc.rightMargin, 10 * mm, f"PAGE {doc.page - 1}")
    c.restoreState()


def inline_markup(value: str) -> str:
    value = html.escape(value.strip())
    value = re.sub(r"`([^`]+)`", r'<font name="AirMono" color="#087D6F">\1</font>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", value)
    return value


def styles():
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="AirSans", fontSize=8.4, leading=12.1, textColor=INK, spaceAfter=5.5, allowWidows=0, allowOrphans=0),
        "lead": ParagraphStyle("Lead", parent=base["BodyText"], fontName="AirSans", fontSize=10.1, leading=14.2, textColor=INK, spaceAfter=10),
        "H1": ParagraphStyle("H1", parent=base["Heading1"], fontName="AirSans-Bold", fontSize=17, leading=21, textColor=NAVY, spaceBefore=8, spaceAfter=9, keepWithNext=True),
        "H2": ParagraphStyle("H2", parent=base["Heading2"], fontName="AirSans-Bold", fontSize=11.2, leading=14.2, textColor=TEAL_DARK, spaceBefore=8, spaceAfter=4.5, keepWithNext=True),
        "H3": ParagraphStyle("H3", parent=base["Heading3"], fontName="AirSans-Bold", fontSize=9.2, leading=12, textColor=INK, spaceBefore=6.5, spaceAfter=3, keepWithNext=True),
        "bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName="AirSans", fontSize=8.2, leading=11.5, leftIndent=10, firstLineIndent=0, textColor=INK, spaceAfter=2.8),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName="AirSans", fontSize=7.2, leading=9.6, textColor=INK_2),
        "table_head": ParagraphStyle("TableHead", parent=base["BodyText"], fontName="AirSans-Bold", fontSize=6.8, leading=8.5, textColor=WHITE),
        "table": ParagraphStyle("TableBody", parent=base["BodyText"], fontName="AirSans", fontSize=6.6, leading=8.7, textColor=INK),
        "quote": ParagraphStyle("Quote", parent=base["BodyText"], fontName="AirSans-Bold", fontSize=9.3, leading=13.5, textColor=TEAL_DARK, spaceAfter=0),
        "toc_title": ParagraphStyle("TOCTitle", parent=base["Heading1"], fontName="AirSans-Bold", fontSize=22, leading=26, textColor=NAVY, spaceAfter=8),
    }


def callout(text: str, sty) -> Table:
    content = Paragraph(inline_markup(text), sty["quote"])
    table = Table([["", content]], colWidths=[3 * mm, 159 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), TEAL),
                ("BACKGROUND", (1, 0), (1, -1), MINT),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (1, 0), (1, -1), 10),
                ("RIGHTPADDING", (1, 0), (1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B9E6DD")),
            ]
        )
    )
    return table


def make_table(rows: list[list[str]], avail_width: float, sty) -> Table:
    cols = max(len(r) for r in rows)
    normalized = [r + [""] * (cols - len(r)) for r in rows]
    data = []
    for ridx, row in enumerate(normalized):
        style = sty["table_head"] if ridx == 0 else sty["table"]
        data.append([Paragraph(inline_markup(cell), style) for cell in row])
    if cols == 2:
        widths = [avail_width * 0.31, avail_width * 0.69]
    elif cols == 3:
        widths = [avail_width * 0.22, avail_width * 0.33, avail_width * 0.45]
    elif cols == 4:
        widths = [avail_width * 0.18, avail_width * 0.24, avail_width * 0.27, avail_width * 0.31]
    else:
        widths = [avail_width / cols] * cols
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_2),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for ridx in range(1, len(data)):
        commands.append(("BACKGROUND", (0, ridx), (-1, ridx), WHITE if ridx % 2 else PALE))
    table.setStyle(TableStyle(commands))
    return table


def paragraph_block(lines: list[str], sty, first_after_h1: bool = False) -> Paragraph:
    text = " ".join(line.strip() for line in lines)
    return Paragraph(inline_markup(text), sty["lead"] if first_after_h1 else sty["body"])


def build_story(markdown: str, doc: AirShieldDocTemplate, sty):
    story: list[Flowable] = [CoverPage(doc.width, doc.height), PageBreak()]

    story.append(Paragraph("Contents", sty["toc_title"]))
    story.append(Paragraph("Architecture, integration, commercial case, assurance, and executive decisions", sty["lead"]))
    story.append(Rule(TEAL, 1.3, 10))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOCLevel1",
            fontName="AirSans",
            fontSize=8.2,
            leading=12.5,
            leftIndent=0,
            firstLineIndent=0,
            textColor=INK,
            spaceBefore=1,
        )
    ]
    story.append(toc)
    story.append(PageBreak())

    # Start at section one; cover metadata is already rendered graphically.
    lines = markdown.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("# 1. Executive brief"))
    lines = lines[start:]
    i = 0
    first_section = True
    first_after_h1 = False
    force_break_sections = {"4", "5", "7", "9", "10", "11", "13", "14", "16", "18"}

    while i < len(lines):
        raw = lines[i].rstrip()
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue
        if stripped == "---":
            story.append(Rule())
            i += 1
            continue
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            section_match = re.match(r"(\d+)", title)
            if not first_section and section_match and section_match.group(1) in force_break_sections:
                story.append(PageBreak())
            elif not first_section:
                story.append(CondPageBreak(55 * mm))
            first_section = False
            story.append(Paragraph(inline_markup(title), sty["H1"]))
            story.append(Rule(TEAL, 1.2, 8))
            if title.startswith("1."):
                story.append(AtAGlance())
                story.append(Spacer(1, 3 * mm))
            elif title.startswith("4."):
                story.append(BusinessFlowDiagram())
                story.append(Spacer(1, 3 * mm))
            elif title.startswith("5."):
                story.append(ArchitectureDiagram())
                story.append(Spacer(1, 3 * mm))
            elif title.startswith("8."):
                story.append(IntegrationDiagram())
                story.append(Spacer(1, 3 * mm))
            elif title.startswith("10."):
                story.append(DifferentiationGrid())
                story.append(Spacer(1, 3 * mm))
            first_after_h1 = True
            i += 1
            continue
        if stripped.startswith("## "):
            story.append(Paragraph(inline_markup(stripped[3:]), sty["H2"]))
            i += 1
            continue
        if stripped.startswith("### "):
            story.append(Paragraph(inline_markup(stripped[4:]), sty["H3"]))
            i += 1
            continue
        if stripped.startswith("> "):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith("> "):
                quote_lines.append(lines[i].strip()[2:])
                i += 1
            story.append(callout(" ".join(quote_lines), sty))
            story.append(Spacer(1, 3 * mm))
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|", lines[i + 1]):
            table_rows = []
            header = [cell.strip() for cell in stripped.strip("|").split("|")]
            table_rows.append(header)
            i += 2  # Skip delimiter row.
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_rows.append([cell.strip() for cell in lines[i].strip().strip("|").split("|")])
                i += 1
            story.append(Spacer(1, 2 * mm))
            story.append(make_table(table_rows, doc.width, sty))
            story.append(Spacer(1, 3 * mm))
            first_after_h1 = False
            continue
        if re.match(r"^[-*] ", stripped):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*] ", lines[i].strip()):
                item_text = re.sub(r"^[-*] ", "", lines[i].strip())
                items.append(ListItem(Paragraph(inline_markup(item_text), sty["bullet"]), leftIndent=8))
                i += 1
            story.append(ListFlowable(items, bulletType="bullet", start="circle", leftIndent=12, bulletFontName="AirSans", bulletFontSize=5, bulletColor=TEAL_DARK, spaceAfter=4))
            first_after_h1 = False
            continue
        if re.match(r"^\d+\. ", stripped):
            items = []
            start_number = int(stripped.split(".", 1)[0])
            while i < len(lines) and re.match(r"^\d+\. ", lines[i].strip()):
                item_text = re.sub(r"^\d+\. ", "", lines[i].strip())
                items.append(ListItem(Paragraph(inline_markup(item_text), sty["bullet"]), leftIndent=8))
                i += 1
            story.append(ListFlowable(items, bulletType="1", start=start_number, leftIndent=15, bulletFontName="AirSans-Bold", bulletFontSize=7, bulletColor=TEAL_DARK, spaceAfter=4))
            first_after_h1 = False
            continue

        paragraph_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt:
                i += 1
                break
            if nxt.startswith(("#", ">", "|", "---")) or re.match(r"^[-*] ", nxt) or re.match(r"^\d+\. ", nxt):
                break
            paragraph_lines.append(nxt)
            i += 1
        story.append(paragraph_block(paragraph_lines, sty, first_after_h1))
        first_after_h1 = False

    return story


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sty = styles()
    doc = AirShieldDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=23 * mm,
        bottomMargin=20 * mm,
        title="AirShield Executive Architecture & Business Dossier",
        author="AirShield",
        subject="Architecture, uses, business flow, integrations, technology and executive case",
    )
    story = build_story(SOURCE.read_text(encoding="utf-8"), doc, sty)
    doc.multiBuild(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()
