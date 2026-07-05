from reportlab.lib.pagesizes import landscape, LETTER
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

GREEN = colors.HexColor("#0fa958")
GREEN_DARK = colors.HexColor("#0c8a48")
GREEN_LIGHT = colors.HexColor("#e6f8ee")
GRAY_900 = colors.HexColor("#141b18")
GRAY_600 = colors.HexColor("#5e6d55")
GRAY_100 = colors.HexColor("#f4f7f5")
BORDER = colors.HexColor("#e0e6e2")
RED = colors.HexColor("#e5484d")
AMBER = colors.HexColor("#f0a020")

RISK_COLORS = {"Low": GREEN_DARK, "Medium": AMBER, "High": RED}

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=20, textColor=GRAY_900, spaceAfter=4))
styles.add(ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13, textColor=GREEN_DARK, spaceBefore=14, spaceAfter=8))
styles.add(ParagraphStyle("Body", fontName="Helvetica", fontSize=9, textColor=GRAY_900, leading=13))
styles.add(ParagraphStyle("BodyGray", fontName="Helvetica", fontSize=9, textColor=GRAY_600, leading=13))
styles.add(ParagraphStyle("Small", fontName="Helvetica", fontSize=8, textColor=GRAY_600, leading=11))
styles.add(ParagraphStyle("CellHead", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white))
styles.add(ParagraphStyle("Cell", fontName="Helvetica", fontSize=8.5, textColor=GRAY_900, leading=11))


def _p(text, style="Cell"):
    return Paragraph(str(text) if text is not None else "-", styles[style])


def _money(n):
    if n is None:
        return "-"
    try:
        return f"${float(n):,.0f}"
    except (ValueError, TypeError):
        return str(n)


def _table(data, col_widths, header=True, risk_col=None):
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, GRAY_100]),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ]
    t.setStyle(TableStyle(style))
    return t


def _section_header(title):
    return Paragraph(title, styles["H2"])


def export_pdf(report: dict, client_name: str, out_path: str):
    doc = SimpleDocTemplate(
        out_path, pagesize=landscape(LETTER),
        leftMargin=36, rightMargin=36, topMargin=32, bottomMargin=32,
    )
    story = []

    # --- Cover / Header ---
    story.append(Paragraph("Tax Strategy Consultancy Report", styles["H1"]))
    story.append(Paragraph(f"Prepared for: {client_name}", styles["BodyGray"]))
    story.append(Spacer(1, 14))

    # --- 1. Executive Summary ---
    story.append(_section_header("1. Executive Summary"))
    story.append(Paragraph(report.get("executive_summary", ""), styles["Body"]))
    story.append(Spacer(1, 10))

    cur = report.get("current_tax_liability")
    opt = report.get("optimized_tax_liability")
    savings_low = report.get("estimated_total_savings_low", 0)
    savings_high = report.get("estimated_total_savings_high", 0)
    hp_count = report.get("high_priority_actions_count", len(report.get("action_plan", [])))
    comp_risk = report.get("compliance_risk", "Medium")
    audit_risk = report.get("audit_risk", "Low")

    exec_data = [
        ["Category", "Current", "Optimized"],
        ["Estimated Tax Liability", _money(cur), _money(opt)],
        ["Potential Savings", "-", f"{_money(savings_low)} - {_money(savings_high)}"],
        ["High Priority Actions", str(hp_count), "-"],
        ["Compliance Risk", comp_risk, "-"],
        ["Estimated Audit Risk", audit_risk, "-"],
    ]
    exec_data_p = [[Paragraph(c, styles["CellHead"] if r == 0 else styles["Cell"]) for c in row] for r, row in enumerate(exec_data)]
    story.append(_table(exec_data_p, [3.2 * inch, 2.2 * inch, 2.6 * inch]))
    story.append(PageBreak())

    # --- 2. Optimization Opportunities ---
    story.append(_section_header("2. Optimization Opportunities"))
    opp_header = ["Opportunity", "Est. Savings", "Difficulty", "Deadline", "Priority"]
    opp_rows = [[Paragraph(h, styles["CellHead"]) for h in opp_header]]
    for i, s in enumerate(report.get("strategies", [])):
        savings = f"{_money(s.get('estimated_savings_low'))} - {_money(s.get('estimated_savings_high'))}"
        priority = "High" if i < 3 else ("Medium" if i < 6 else "Low")
        opp_rows.append([
            _p(s.get("name", "")), _p(savings), _p(s.get("difficulty", "Medium")),
            _p(s.get("deadline", "Before filing")), _p(priority),
        ])
    story.append(_table(opp_rows, [3.0 * inch, 1.8 * inch, 1.3 * inch, 1.6 * inch, 1.3 * inch]))
    story.append(Spacer(1, 16))

    # --- 3. Strategy Details ---
    story.append(_section_header("3. Strategy Detail"))
    for s in report.get("strategies", []):
        block = [
            Paragraph(s.get("name", ""), ParagraphStyle("SN", fontName="Helvetica-Bold", fontSize=10.5, textColor=GREEN_DARK, spaceAfter=4)),
            Paragraph(f"<b>What it is:</b> {s.get('what_it_is','')}", styles["Body"]),
            Paragraph(f"<b>Why you qualify:</b> {s.get('why_you_qualify','')}", styles["Body"]),
            Paragraph(f"<b>Estimated impact:</b> {s.get('estimated_impact','')}", styles["Body"]),
            Paragraph(f"<b>Implementation notes:</b> {s.get('implementation_notes','')}", styles["Body"]),
            Spacer(1, 8),
        ]
        story.append(KeepTogether(block))
    story.append(PageBreak())

    # --- 4. Risk Assessment ---
    story.append(_section_header("4. Risk Assessment"))
    risk_header = ["Item", "Risk Level", "IRS Scrutiny", "Documentation Needed", "Mitigation"]
    risk_rows = [[Paragraph(h, styles["CellHead"]) for h in risk_header]]
    for r in report.get("risk_assessment", []):
        risk_rows.append([
            _p(r.get("item", "")), _p(r.get("risk_level", "")), _p(r.get("irs_scrutiny", "")),
            _p(r.get("documentation_needed", "")), _p(r.get("mitigation", "")),
        ])
    if len(risk_rows) > 1:
        story.append(_table(risk_rows, [1.8 * inch, 1.1 * inch, 1.8 * inch, 2.3 * inch, 2.0 * inch]))
    else:
        story.append(Paragraph("No significant risk items identified.", styles["BodyGray"]))
    story.append(Spacer(1, 16))

    # --- 5. Missing Documentation ---
    story.append(_section_header("5. Missing Documentation"))
    docs = report.get("missing_documentation", [])
    if docs:
        for d in docs:
            story.append(Paragraph(f"&#8226; {d}", styles["Body"]))
    else:
        story.append(Paragraph("No outstanding documentation identified.", styles["BodyGray"]))
    story.append(PageBreak())

    # --- 6. Scenario Planning ---
    story.append(_section_header("6. Scenario Planning"))
    scenarios = report.get("scenario_planning", [])
    if scenarios:
        sc_rows = [[Paragraph("Scenario", styles["CellHead"]), Paragraph("Tax Liability", styles["CellHead"])]]
        for sc in scenarios:
            sc_rows.append([_p(sc.get("scenario", "")), _p(_money(sc.get("tax_liability")))])
        story.append(_table(sc_rows, [5.0 * inch, 3.0 * inch]))
    else:
        story.append(Paragraph("Insufficient data for scenario modeling.", styles["BodyGray"]))
    story.append(Spacer(1, 16))

    # --- 7. Action Plan ---
    story.append(_section_header("7. Prioritized Action Plan"))
    ap_header = ["Priority", "Task", "Impact", "Deadline"]
    ap_rows = [[Paragraph(h, styles["CellHead"]) for h in ap_header]]
    for a in report.get("action_plan", []):
        ap_rows.append([
            _p(a.get("priority", "")), _p(a.get("strategy", "")),
            _p(a.get("impact", a.get("reason", ""))), _p(a.get("deadline", "-")),
        ])
    story.append(_table(ap_rows, [0.9 * inch, 3.5 * inch, 3.0 * inch, 1.6 * inch]))
    story.append(PageBreak())

    # --- 8. Long Term Strategy ---
    story.append(_section_header("8. Long-Term Tax Strategy (3-5 Years)"))
    lts = report.get("long_term_strategy", [])
    if lts:
        for item in lts:
            story.append(Paragraph(f"&#8226; {item}", styles["Body"]))
    else:
        story.append(Paragraph("No long-term recommendations available.", styles["BodyGray"]))
    story.append(Spacer(1, 20))

    # --- Disclaimer ---
    story.append(Paragraph(
        report.get("disclaimer", "This report is for informational purposes only and does not constitute tax or legal advice."),
        ParagraphStyle("Disc", fontName="Helvetica-Oblique", fontSize=8, textColor=colors.HexColor("#7a5c00"), leading=11)
    ))

    doc.build(story)
    return out_path