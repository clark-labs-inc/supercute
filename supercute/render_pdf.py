"""Render a (restricted) markdown paper to a clean academic-looking PDF with reportlab.
Supports: # title, author block, ## / ### headings, GFM pipe tables, ![alt](img)
figures, **bold**, *italic*, and paragraphs. Single source -> PDF.

  python -m supercute.render_pdf docs/paper/supercute_gpt55.md docs/paper/supercute_gpt55.pdf
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
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, HRFlowable)


def _inline(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', t)
    t = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", t)            # drop link targets, keep text
    t = re.sub(r"(?<![\*\w])\*(?!\*)(.+?)(?<!\*)\*(?![\*\w])", r"<i>\1</i>", t)
    return t


def build(md_path, pdf_path):
    base = os.path.dirname(os.path.abspath(md_path))
    ss = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=ss["Title"], fontSize=16, leading=20, alignment=TA_CENTER, spaceAfter=6)
    author = ParagraphStyle("A", parent=ss["Normal"], fontSize=10.5, leading=13, alignment=TA_CENTER, spaceAfter=2)
    h2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12, leading=14, spaceBefore=10, spaceAfter=4)
    h3 = ParagraphStyle("H3", parent=ss["Heading3"], fontSize=10.5, leading=13, spaceBefore=6, spaceAfter=3)
    body = ParagraphStyle("B", parent=ss["Normal"], fontSize=9.6, leading=13.2, alignment=TA_JUSTIFY, spaceAfter=5)
    cap = ParagraphStyle("C", parent=ss["Normal"], fontSize=8.6, leading=11, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=8)
    cell = ParagraphStyle("cell", parent=ss["Normal"], fontSize=8.4, leading=10.5)
    cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")

    lines = open(md_path, encoding="utf-8").read().split("\n")
    flow = []
    i = 0
    seen_title = False
    seen_section = False
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1
            continue
        if ln.startswith("# ") and not seen_title:
            flow.append(Paragraph(_inline(ln[2:]), title)); seen_title = True; i += 1
            continue
        if ln.startswith("## "):
            seen_section = True
            flow.append(Paragraph(_inline(ln[3:]), h2)); i += 1
            continue
        if ln.startswith("### "):
            flow.append(Paragraph(_inline(ln[4:]), h3)); i += 1
            continue
        if ln.strip() == "---":
            flow.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceBefore=4, spaceAfter=6)); i += 1
            continue
        m = re.match(r"!\[.*?\]\((.+?)\)", ln)
        if m:
            p = m.group(1)
            if not os.path.isabs(p):
                p = os.path.join(base, p)
            if os.path.exists(p):
                img = Image(p); maxw = 6.5 * inch
                if img.drawWidth > maxw:
                    img.drawHeight *= maxw / img.drawWidth; img.drawWidth = maxw
                img.hAlign = "CENTER"; flow.append(img); flow.append(Spacer(1, 4))
            i += 1
            continue
        if ln.lstrip().startswith("|"):                    # table block
            tbl = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                tbl.append(lines[i]); i += 1
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tbl]
            rows = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]  # drop separator row
            data = [[Paragraph(_inline(c), cellb if ri == 0 else cell) for c in r] for ri, r in enumerate(rows)]
            t = Table(data, hAlign="CENTER")
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
                ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]))
            flow.append(t); flow.append(Spacer(1, 5))
            continue
        # caption (italic line wrapped in *), author block (after title, before 1st ##), else body
        if ln.strip().startswith("*") and ln.strip().endswith("*"):
            style = cap
        elif seen_title and not seen_section:
            style = author
        else:
            style = body
        flow.append(Paragraph(_inline(ln), style)); i += 1

    doc = SimpleDocTemplate(pdf_path, pagesize=letter, topMargin=0.8 * inch, bottomMargin=0.8 * inch,
                            leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                            title="SUPERCUTE GPT-5.5 study")
    doc.build(flow)
    print(f"wrote {pdf_path}")




if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
