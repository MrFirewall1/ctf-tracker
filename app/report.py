"""PDF-rapport med reportlab. Bruker bare tekst du selv har skrevet i forklaringene:
ingenting omskrives, oppsummeres eller legges til av appen (bortsett fra feltetiketter).
"""
from datetime import date
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .constants import CATEGORIES, DIFFICULTIES, PROTOCOLS, STATUSES
from .stats import compute_stats

FONT_DIRS = [Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/dejavu")]
ACCENT = colors.HexColor("#2456d6")
STATUS_COLORS = {"solved_alone": "#1f8a4c", "solved_hint": "#2456d6",
                 "solved_solution": "#d98b00", "unsolved": "#c0392b"}
CODE_WRAP = 88


def _fonts() -> tuple[str, str, str]:
    """(normal, fet, mono). DejaVu hvis tilgjengelig (full unicode), ellers innebygde."""
    for d in FONT_DIRS:
        files = {"Body": d / "DejaVuSans.ttf", "Body-Bold": d / "DejaVuSans-Bold.ttf",
                 "Mono": d / "DejaVuSansMono.ttf"}
        if all(p.is_file() for p in files.values()):
            for name, p in files.items():
                if name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, str(p)))
            pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold",
                                          italic="Body", boldItalic="Body-Bold")
            return "Body", "Body-Bold", "Mono"
    return "Helvetica", "Helvetica-Bold", "Courier"


def _styles():
    body, bold, mono = _fonts()
    return {
        "title": ParagraphStyle("title", fontName=bold, fontSize=30, leading=36, textColor=ACCENT),
        "sub": ParagraphStyle("sub", fontName=body, fontSize=14, leading=20, textColor=colors.HexColor("#444")),
        "h1": ParagraphStyle("h1", fontName=bold, fontSize=18, leading=22, spaceAfter=8),
        "h2": ParagraphStyle("h2", fontName=bold, fontSize=14, leading=18, spaceAfter=4, textColor=ACCENT),
        "h3": ParagraphStyle("h3", fontName=bold, fontSize=11, leading=14, spaceBefore=8, spaceAfter=2),
        "p": ParagraphStyle("p", fontName=body, fontSize=10, leading=14),
        "small": ParagraphStyle("small", fontName=body, fontSize=8.5, leading=11, textColor=colors.HexColor("#666")),
        "code": ParagraphStyle("code", fontName=mono, fontSize=8, leading=10.5,
                               backColor=colors.HexColor("#f1f3f6"), borderPadding=4,
                               leftIndent=4, spaceBefore=3, spaceAfter=6),
        "cell": ParagraphStyle("cell", fontName=body, fontSize=9, leading=12),
        "cellb": ParagraphStyle("cellb", fontName=bold, fontSize=9, leading=12,
                                textColor=colors.HexColor("#555")),
    }


def _text(s: str) -> str:
    """Escape for reportlab-markup og behold linjeskift. Ingen annen omskriving."""
    return escape(s).replace("\n", "<br/>")


def _wrap_code(lines: list[str]) -> str:
    out = []
    for line in lines:
        line = line.replace("\t", "    ")
        while len(line) > CODE_WRAP:
            out.append(line[:CODE_WRAP])
            line = "  " + line[CODE_WRAP:]  # kun visuell linjebryting
        out.append(line)
    return "\n".join(out)


def body_flowables(body: str, st) -> list:
    """Markdown-teksten din gjengis slik den står: overskrifter, avsnitt og kodeblokker."""
    out, para, code = [], [], None

    def flush():
        if para:
            out.append(Paragraph(_text("\n".join(para)), st["p"]))
            out.append(Spacer(1, 4))
            para.clear()

    for line in body.split("\n"):
        if line.strip().startswith("```"):
            if code is None:
                flush()
                code = []
            else:
                out.append(Preformatted(_wrap_code(code), st["code"]))
                code = None
            continue
        if code is not None:
            code.append(line)
        elif line.startswith("## "):
            flush()
            out.append(Paragraph(_text(line[3:]), st["h3"]))
        elif not line.strip():
            flush()
        else:
            para.append(line)
    if code is not None:  # ulukket kodeblokk: vis den likevel
        out.append(Preformatted(_wrap_code(code), st["code"]))
    flush()
    return out


# --- diagrammer ----------------------------------------------------------------

def _no_data(w, h, msg="Ingen data i utvalget"):
    d = Drawing(w, h)
    d.add(String(w / 2, h / 2, msg, textAnchor="middle", fontSize=9, fillColor=colors.grey))
    return d


def chart_solved_per_week(stats, font):
    s = stats["solved_over_time"]
    w, h = 480, 170
    if not s["labels"]:
        return _no_data(w, h)
    d = Drawing(w, h)
    c = VerticalBarChart()
    c.x, c.y, c.width, c.height = 35, 35, w - 50, h - 60
    c.data = [s["solved"]]
    c.categoryAxis.categoryNames = [l.replace("-U", " U") for l in s["labels"]]
    c.categoryAxis.labels.angle = 45
    c.categoryAxis.labels.boxAnchor = "ne"
    c.categoryAxis.labels.dy = -4
    c.categoryAxis.labels.fontName = font
    c.categoryAxis.labels.fontSize = 6.5
    c.valueAxis.valueMin = 0
    c.valueAxis.valueMax = max(max(s["solved"]), 1) + 1
    c.valueAxis.valueStep = 1 if c.valueAxis.valueMax <= 10 else None
    c.valueAxis.labels.fontName = font
    c.valueAxis.labels.fontSize = 7
    c.bars[0].fillColor = ACCENT
    d.add(c)
    return d


def chart_rate(rows, font, title_w=480):
    rows = [r for r in rows if r["rate"] is not None]
    if not rows:
        return _no_data(title_w, 80)
    h = 40 + 24 * len(rows)
    d = Drawing(title_w, h)
    c = HorizontalBarChart()
    c.x, c.y, c.width, c.height = 150, 15, title_w - 190, h - 30
    c.data = [[round(r["rate"] * 100) for r in reversed(rows)]]
    c.categoryAxis.categoryNames = [f"{r['label']} ({r['solved']}/{r['total']})" for r in reversed(rows)]
    c.categoryAxis.labels.fontName = font
    c.categoryAxis.labels.fontSize = 8
    c.valueAxis.valueMin, c.valueAxis.valueMax, c.valueAxis.valueStep = 0, 100, 25
    c.valueAxis.labels.fontName = font
    c.valueAxis.labels.fontSize = 7
    c.bars[0].fillColor = ACCENT
    d.add(c)
    return d


def chart_status(stats, font):
    items = [x for x in stats["status_share"] if x["count"]]
    w, h = 480, 140
    if not items:
        return _no_data(w, h)
    d = Drawing(w, h)
    p = Pie()
    p.x, p.y, p.width, p.height = 20, 15, 110, 110
    p.data = [x["count"] for x in items]
    p.labels = [str(x["count"]) for x in items]
    p.sideLabels = False
    p.slices.fontName = font
    p.slices.fontSize = 9
    for i, x in enumerate(items):
        p.slices[i].fillColor = colors.HexColor(STATUS_COLORS[x["key"]])
        d.add(String(170, h - 30 - i * 18, f"■ {x['label']}: {x['count']}", fontName=font, fontSize=10,
                     fillColor=colors.HexColor(STATUS_COLORS[x["key"]])))
    d.add(p)
    return d


# --- selve rapporten -------------------------------------------------------------

def select_tasks(tasks, start=None, end=None, ids=None):
    out = [t for t in tasks
           if (not start or t["date"] >= start) and (not end or t["date"] <= end)
           and (not ids or t["id"] in ids)]
    return sorted(out, key=lambda t: (t["date"], t["id"]))


def _meta_table(t, st):
    def yn(v):
        return "Ja" if v else "Nei"
    rows = [
        ("Dato", t["date"]), ("Kilde", t["source"] or "–"),
        ("Kategori", CATEGORIES[t["category"]]), ("Protokoll", PROTOCOLS[t["protocol"]] or "–"),
        ("Vanskelighetsgrad", DIFFICULTIES[t["difficulty"]]), ("Status", STATUSES[t["status"]]),
        ("Hint brukt", str(t["hints_used"])), ("Løst på nytt uten hjelp", yn(t["resolved_later"])),
        ("Verktøy", ", ".join(t["tools"]) or "–"), ("Tags", ", ".join(t["tags"]) or "–"),
    ]
    data = [[Paragraph(escape(k), st["cellb"]), Paragraph(escape(v), st["cell"])] for k, v in rows]
    tbl = Table(data, colWidths=[45 * mm, 120 * mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dde")),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return tbl


def build_report(tasks: list[dict], start: str | None = None, end: str | None = None,
                 today: date | None = None) -> bytes:
    """tasks: allerede valgt utvalg. Returnerer PDF som bytes."""
    st = _styles()
    font = st["p"].fontName
    today = today or date.today()
    stats = compute_stats(tasks, today=today)
    tot = stats["totals"]
    first = tasks[0]["date"] if tasks else "–"
    last = tasks[-1]["date"] if tasks else "–"
    period = f"{start or first} – {end or last}"

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm,
                            title="CTF-treningsrapport", author="")

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(20 * mm, 10 * mm, f"CTF-treningsrapport · {period}")
        canvas.drawRightString(A4[0] - 20 * mm, 10 * mm, f"Side {d.page}")
        canvas.restoreState()

    story = [
        Spacer(1, 70 * mm),
        Paragraph("CTF-treningsrapport", st["title"]),
        Spacer(1, 8 * mm),
        Paragraph(f"Periode: {period}", st["sub"]),
        Paragraph(f"{len(tasks)} oppgaver", st["sub"]),
        Spacer(1, 100 * mm),
        Paragraph(f"Generert {today.isoformat()}. Forklaringene er gjengitt slik jeg skrev dem.", st["small"]),
        PageBreak(),
        Paragraph("Sammendrag", st["h1"]),
    ]

    def pct(v):
        return "–" if v is None else f"{round(v * 100)} %"

    kv = [
        ("Oppgaver", tot["tasks"]), ("Løst (alene eller med hint)", tot["solved"]),
        ("Løsningsrate", pct(tot["rate"])),
        ("Hint per oppgave (snitt)", "–" if tot["avg_hints"] is None else tot["avg_hints"]),
        ("Løst på nytt uten hjelp", tot["resolved_later"]),
        ("«Hva jeg lærte» utfylt", f"{tot['explained']} / {tot['tasks']}"),
        ("Lengste streak", f"{stats['streak']['longest']} dager"),
    ]
    tbl = Table([[Paragraph(escape(k), st["cellb"]), Paragraph(escape(str(v)), st["cell"])] for k, v in kv],
                colWidths=[70 * mm, 40 * mm])
    tbl.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dde"))]))
    story += [tbl, Spacer(1, 6 * mm)]

    for title, chart in [
        ("Løste oppgaver per uke", chart_solved_per_week(stats, font)),
        ("Løsningsrate per kategori", chart_rate(stats["by_category"], font)),
        ("Løsningsrate per protokoll", chart_rate(stats["by_protocol"], font)),
        ("Løst alene / hint / fasit", chart_status(stats, font)),
    ]:
        story.append(KeepTogether([Paragraph(title, st["h3"]), chart]))

    if stats["weakest"]:
        rows = [[Paragraph(escape(w["label"]), st["cell"]), Paragraph(escape(w["kind"]), st["cell"]),
                 Paragraph(f"{w['solved']} / {w['total']}", st["cell"]), Paragraph(pct(w["rate"]), st["cell"])]
                for w in stats["weakest"]]
        wt = Table([[Paragraph(h, st["cellb"]) for h in ("Område", "Type", "Løst / totalt", "Rate")]] + rows,
                   colWidths=[60 * mm, 30 * mm, 35 * mm, 30 * mm])
        wt.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dde"))]))
        story += [Paragraph("Svakeste områder", st["h3"]), wt]
    story.append(Paragraph(
        "«Løst» = løst alene eller med hint. Løst med fasit teller som ikke løst.", st["small"]))

    for t in tasks:
        story.append(PageBreak())
        story.append(Paragraph(_text(t["title"]), st["h2"]))
        story.append(_meta_table(t, st))
        story.append(Spacer(1, 4 * mm))
        story += body_flowables(t["body"], st)

    doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=footer)
    return buf.getvalue()
