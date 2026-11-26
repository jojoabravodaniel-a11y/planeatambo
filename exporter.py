"""Exportación del material revisado a Word (.docx) y PDF."""
import io
import re
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Pt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

FOOTER = "Material generado con apoyo de IA y revisado por el docente · I.E. Politécnico Francisco de Paula Santander, El Tambo, Cauca"


def _clean(t):
    return re.sub(r"\*\*(.+?)\*\*", r"\1", t)


def _blocks(text):
    """Divide el texto en bloques ('bullet'|'p', contenido)."""
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith(("- ", "* ")):
            yield "bullet", _clean(s[2:])
        else:
            yield "p", _clean(s)


def to_docx(title, meta, sections):
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    doc.add_heading(title, 0)
    doc.add_paragraph(meta)
    for label, text in sections:
        doc.add_heading(label, 2)
        for kind, content in _blocks(text):
            doc.add_paragraph(content, style="List Bullet" if kind == "bullet" else None)
    p = doc.add_paragraph()
    r = p.add_run(FOOTER)
    r.italic, r.font.size = True, Pt(8)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def to_pdf(title, meta, sections):
    ss = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8, textColor="#666666")
    story = [Paragraph(escape(title), ss["Title"]), Paragraph(escape(meta), ss["Normal"]), Spacer(1, 10)]
    for label, text in sections:
        story.append(Paragraph(escape(label), ss["Heading2"]))
        bullets = []
        for kind, content in _blocks(text):
            if kind == "bullet":
                bullets.append(ListItem(Paragraph(escape(content), ss["Normal"])))
                continue
            if bullets:
                story.append(ListFlowable(bullets, bulletType="bullet"))
                bullets = []
            story.append(Paragraph(escape(content), ss["Normal"]))
        if bullets:
            story.append(ListFlowable(bullets, bulletType="bullet"))
    story += [Spacer(1, 16), Paragraph(escape(FOOTER), small)]
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm).build(story)
    return buf.getvalue()
