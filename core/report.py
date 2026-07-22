from __future__ import annotations

from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .analytics import automatic_insights, pareto_frame


def _fmt_number(value: float) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_pdf(df: pd.DataFrame, project: str, filters: str = "") -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenterTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#0B3058")))
    story = [Paragraph("ROOT CAUSE ANALYTICS — Lean Six Sigma", styles["CenterTitle"]), Spacer(1, 5 * mm)]
    story.append(Paragraph(f"Projeto: {project}", styles["Heading2"]))
    story.append(Paragraph(f"Filtros aplicados: {filters or 'Nenhum'}", styles["BodyText"]))
    story.append(Spacer(1, 3 * mm))

    total = len(df)
    cost = float(df["custo"].sum()) if "custo" in df else 0
    downtime = float(df["tempo_parada"].sum()) if "tempo_parada" in df else 0
    kpis = [["Ocorrências", "Custo total", "Tempo de parada"], [str(total), f"R$ {_fmt_number(cost)}", _fmt_number(downtime)]]
    table = Table(kpis, colWidths=[80 * mm, 80 * mm, 80 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B5CAB")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#B7C5D5")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [table, Spacer(1, 6 * mm), Paragraph("Principais insights", styles["Heading2"])]
    for item in automatic_insights(df):
        story.append(Paragraph(f"<b>{item['tipo']}:</b> {item['texto']}", styles["BodyText"]))

    for category, title in [("categoria", "Pareto por categoria"), ("fornecedor", "Pareto por fornecedor"), ("causa", "Pareto de causas")]:
        if category not in df or not df[category].notna().any():
            continue
        story += [PageBreak(), Paragraph(title, styles["Heading1"])]
        p = pareto_frame(df, category).head(20)
        rows = [["Item", "Impacto", "%", "% acumulado"]] + [
            [str(r[category])[:60], _fmt_number(r["valor"]), f"{r['percentual']:.1f}%", f"{r['acumulado']:.1f}%"]
            for _, r in p.iterrows()
        ]
        pt = Table(rows, repeatRows=1, colWidths=[135 * mm, 35 * mm, 35 * mm, 40 * mm])
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B5CAB")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#B7C5D5")), ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ]))
        story.append(pt)
    doc.build(story)
    return buffer.getvalue()

