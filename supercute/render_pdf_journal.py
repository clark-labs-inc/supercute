"""Render the markdown paper to a TWO-COLUMN, journal-style PDF (reportlab). Body text
flows in two balanced columns; tables and the figure span the full page width; the
title/author/abstract form a full-width header. Single source -> journal PDF.

  python -m supercute.render_pdf_journal docs/paper/supercute_gpt55.md docs/paper/supercute_gpt55.pdf
"""
from __future__ import annotations

import os
import re
import sys

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (BalancedColumns, Image, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle, HRFlowable)

ss = getSampleStyleSheet()
TITLE = ParagraphStyle("T", parent=ss["Title"], fontName="Times-Bold", fontSize=15, leading=18, alignment=TA_CENTER, spaceAfter=4)
AUTH = ParagraphStyle("A", parent=ss["Normal"], fontName="Times-Roman", fontSize=10, leading=12, alignment=TA_CENTER, spaceAfter=1)
ABSH = ParagraphStyle("ABSH", parent=ss["Normal"], fontName="Times-Bold", fontSize=9.5, leading=11, alignment=TA_CENTER, spaceBefore=6, spaceAfter=3)
ABS = ParagraphStyle("ABS", parent=ss["Normal"], fontName="Times-Roman", fontSize=8.8, leading=11.4, alignment=TA_JUSTIFY, leftIndent=24, rightIndent=24, spaceAfter=4)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Times-Bold", fontSize=10.5, leading=12, spaceBefore=7, spaceAfter=3)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontName="Times-Bold", fontSize=9.5, leading=11, spaceBefore=4, spaceAfter=2)
BODY = ParagraphStyle("B", parent=ss["Normal"], fontName="Times-Roman", fontSize=9, leading=11.2, alignment=TA_JUSTIFY, spaceAfter=4)
CAP = ParagraphStyle("C", parent=ss["Normal"], fontName="Times-Italic", fontSize=8, leading=9.6, alignment=TA_CENTER, textColor=colors.black, spaceAfter=7)
CELL = ParagraphStyle("cell", parent=ss["Normal"], fontName="Times-Roman", fontSize=8, leading=9.6)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Times-Bold")


def _inline(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', t)
    t = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", t)
    t = re.sub(r"(?<![\*\w])\*(?!\*)(.+?)(?<!\*)\*(?![\*\w])", r"<i>\1</i>", t)
    return t


def _table(tbl_lines):
    rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tbl_lines]
    rows = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]
    data = [[Paragraph(_inline(c), CELLB if ri == 0 else CELL) for c in r] for ri, r in enumerate(rows)]
    t = Table(data, hAlign="CENTER", repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("LINEABOVE", (0, 0), (-1, 0), 0.9, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.9, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.9, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def build(md_path, pdf_path):
    base = os.path.dirname(os.path.abspath(md_path))
    lines = open(md_path, encoding="utf-8").read().split("\n")
    header = []          # full-width title/author/abstract block
    story = []           # sequence of ("text",[flowables]) and ("wide",flowable)
    buf = []             # current text run
    i, seen_title, seen_section = 0, False, False

    def flush():
        if buf:
            story.append(("text", buf[:])); buf.clear()

    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1; continue
        if ln.startswith("# ") and not seen_title:
            header.append(Paragraph(_inline(ln[2:]), TITLE)); seen_title = True; i += 1; continue
        if ln.startswith("## "):
            seen_section = True
            label = ln[3:]
            (buf.append(Paragraph(_inline(label), ABSH if label.lower() == "abstract" else H2)))
            i += 1; continue
        if ln.startswith("### "):
            buf.append(Paragraph(_inline(ln[4:]), H3)); i += 1; continue
        if ln.strip() == "---":
            i += 1; continue
        m = re.match(r"!\[.*?\]\((.+?)\)", ln)
        if m:
            flush()
            p = m.group(1) if os.path.isabs(m.group(1)) else os.path.join(base, m.group(1))
            if os.path.exists(p):
                img = Image(p); maxw = 4.0 * inch
                if img.drawWidth > maxw:
                    img.drawHeight *= maxw / img.drawWidth; img.drawWidth = maxw
                img.hAlign = "CENTER"; story.append(("wide", img))
            i += 1; continue
        if ln.lstrip().startswith("|"):
            flush()
            tbl = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                tbl.append(lines[i]); i += 1
            story.append(("wide", _table(tbl)))
            continue
        # body / abstract / caption
        if ln.strip().startswith("*") and ln.strip().endswith("*"):
            buf.append(Paragraph(_inline(ln), CAP))
        elif seen_title and not seen_section:
            header.append(Paragraph(_inline(ln), AUTH))
        elif not seen_section:
            buf.append(Paragraph(_inline(ln), ABS))
        else:
            # decide abstract vs body by whether we are inside the Abstract section
            buf.append(Paragraph(_inline(ln), BODY))
        i += 1
    flush()

    flow = list(header) + [HRFlowable(width="100%", thickness=0.6, color=colors.black, spaceBefore=4, spaceAfter=6)]
    for kind, item in story:
        if kind == "wide":
            flow.append(item); flow.append(Spacer(1, 5))
        else:
            flow.append(BalancedColumns(item, nCols=2, innerPadding=14, spaceBefore=2, spaceAfter=2))

    doc = SimpleDocTemplate(pdf_path, pagesize=letter, topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            leftMargin=0.7 * inch, rightMargin=0.7 * inch, title="SUPERCUTE study")
    doc.build(flow)
    print(f"wrote {pdf_path}")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
