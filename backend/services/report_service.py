"""
Report Service - PDF generation with reportlab fallback to HTML
"""
from io import BytesIO
from datetime import datetime

# Try to import reportlab; fall back gracefully if not installed
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    _REPORTLAB = True
except ImportError:
    _REPORTLAB = False


# ── Colour palette (only defined when reportlab is available) ──────────────
if _REPORTLAB:
    BLUE_DARK  = colors.HexColor("#1e3a8a")
    BLUE_MID   = colors.HexColor("#2563eb")
    BLUE_LIGHT = colors.HexColor("#eff6ff")
    GREEN      = colors.HexColor("#059669")
    RED        = colors.HexColor("#dc2626")
    YELLOW     = colors.HexColor("#d97706")
    PURPLE     = colors.HexColor("#7c3aed")
    GRAY_DARK  = colors.HexColor("#334155")
    GRAY_MID   = colors.HexColor("#64748b")
    GRAY_LIGHT = colors.HexColor("#f1f5f9")
    WHITE      = colors.white


def _risk_color(risk_level):
    if not risk_level:
        return GRAY_MID
    rl = risk_level.upper()
    if "VERY" in rl:   return PURPLE
    if "HIGH" in rl:   return RED
    if "MODERATE" in rl: return YELLOW
    return GREEN


def _styles():
    base = getSampleStyleSheet()
    return {
        "title":    ParagraphStyle("title",    fontSize=20, textColor=WHITE,      alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", fontSize=10, textColor=colors.HexColor("#bfdbfe"), alignment=TA_CENTER, fontName="Helvetica"),
        "h2":       ParagraphStyle("h2",       fontSize=12, textColor=BLUE_DARK,  fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4),
        "body":     ParagraphStyle("body",     fontSize=9,  textColor=GRAY_DARK,  fontName="Helvetica",      spaceAfter=3),
        "small":    ParagraphStyle("small",    fontSize=8,  textColor=GRAY_MID,   fontName="Helvetica"),
        "center":   ParagraphStyle("center",   fontSize=9,  textColor=GRAY_DARK,  alignment=TA_CENTER),
        "right":    ParagraphStyle("right",    fontSize=8,  textColor=GRAY_MID,   alignment=TA_RIGHT),
    }


def _tbl_style(header_color=BLUE_DARK):
    return TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  header_color),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  9),
        ("ALIGN",       (0, 0), (-1, 0),  "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("ALIGN",       (0, 1), (-1, -1), "CENTER"),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ])


def generate_patient_pdf(patient_info, predictions, prescriptions, lab_results, appointments):
    """
    Generate a patient health report PDF.
    Falls back to a plain HTML-as-bytes report if reportlab is not installed.
    Returns: BytesIO buffer.
    """
    if not _REPORTLAB:
        return _html_patient_report(patient_info, predictions, prescriptions, lab_results, appointments)
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=15*mm, bottomMargin=15*mm
    )
    s = _styles()
    W = A4[0] - 36*mm   # usable width
    story = []

    # ── Header banner ────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("🏥  Diabetes Prediction System", s["title"]),
        Paragraph("Patient Health Report", s["subtitle"]),
    ]]
    header_tbl = Table([[
        Paragraph("🏥  Diabetes Prediction System", s["title"]),
    ]], colWidths=[W])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(header_tbl)

    sub_tbl = Table([[
        Paragraph("Patient Health Report", s["subtitle"]),
        Paragraph(f"Generated: {datetime.utcnow().strftime('%d %b %Y, %H:%M')} UTC", s["right"]),
    ]], colWidths=[W*0.6, W*0.4])
    sub_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_MID),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(sub_tbl)
    story.append(Spacer(1, 8*mm))

    # ── Patient Info ─────────────────────────────────────────────────────────
    story.append(Paragraph("Patient Information", s["h2"]))
    story.append(HRFlowable(width=W, thickness=1, color=BLUE_MID, spaceAfter=4))

    pi = patient_info or {}
    info_data = [
        ["Patient ID", pi.get("patient_id", "—"),   "Name",  pi.get("name", pi.get("username", "—"))],
        ["Email",      pi.get("email", "—"),          "Blood Group", pi.get("blood_group", "—")],
    ]
    info_tbl = Table(info_data, colWidths=[W*0.18, W*0.32, W*0.18, W*0.32])
    info_tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BLUE_DARK),
        ("TEXTCOLOR", (2, 0), (2, -1), BLUE_DARK),
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("GRID",      (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 6*mm))

    # ── Predictions ──────────────────────────────────────────────────────────
    story.append(Paragraph("Prediction History", s["h2"]))
    story.append(HRFlowable(width=W, thickness=1, color=BLUE_MID, spaceAfter=4))

    if predictions:
        pred_data = [["Date", "Result", "Risk Level", "Probability %"]]
        for p in predictions[:10]:
            date = (p.get("date") or p.get("created_at") or "")[:10]
            result = p.get("result", "—")
            risk = p.get("risk_level", "—")
            prob = f"{p.get('probability_percent', 0):.1f}%"
            pred_data.append([date, result, risk, prob])
        pred_tbl = Table(pred_data, colWidths=[W*0.22, W*0.22, W*0.32, W*0.24])
        pred_tbl.setStyle(_tbl_style(BLUE_DARK))
        story.append(pred_tbl)
    else:
        story.append(Paragraph("No prediction records found.", s["body"]))
    story.append(Spacer(1, 6*mm))

    # ── Prescriptions ────────────────────────────────────────────────────────
    story.append(Paragraph("Prescriptions", s["h2"]))
    story.append(HRFlowable(width=W, thickness=1, color=GREEN, spaceAfter=4))

    if prescriptions:
        rx_data = [["Date", "Medication", "Dosage", "Status"]]
        for rx in prescriptions[:10]:
            date = (rx.get("date") or rx.get("created_at") or "")[:10]
            rx_data.append([date, rx.get("medication", "—"), rx.get("dosage", "—"), rx.get("status", "—")])
        rx_tbl = Table(rx_data, colWidths=[W*0.20, W*0.35, W*0.25, W*0.20])
        rx_tbl.setStyle(_tbl_style(GREEN))
        story.append(rx_tbl)
    else:
        story.append(Paragraph("No prescription records found.", s["body"]))
    story.append(Spacer(1, 6*mm))

    # ── Lab Results ──────────────────────────────────────────────────────────
    story.append(Paragraph("Lab Results", s["h2"]))
    story.append(HRFlowable(width=W, thickness=1, color=YELLOW, spaceAfter=4))

    if lab_results:
        lab_data = [["Date", "Test Name", "Result", "Status"]]
        for lab in lab_results[:10]:
            date = (lab.get("date") or lab.get("created_at") or "")[:10]
            lab_data.append([date, lab.get("test_name", "—"), str(lab.get("results", "—")), lab.get("status", "—")])
        lab_tbl = Table(lab_data, colWidths=[W*0.20, W*0.35, W*0.25, W*0.20])
        lab_tbl.setStyle(_tbl_style(YELLOW))
        story.append(lab_tbl)
    else:
        story.append(Paragraph("No lab results found.", s["body"]))
    story.append(Spacer(1, 6*mm))

    # ── Appointments ─────────────────────────────────────────────────────────
    story.append(Paragraph("Appointments", s["h2"]))
    story.append(HRFlowable(width=W, thickness=1, color=PURPLE, spaceAfter=4))

    if appointments:
        apt_data = [["Date", "Time", "Reason", "Status"]]
        for apt in appointments[:10]:
            apt_data.append([
                str(apt.get("date", "—")),
                apt.get("time") or "—",
                apt.get("reason", "—"),
                apt.get("status", "—")
            ])
        apt_tbl = Table(apt_data, colWidths=[W*0.20, W*0.15, W*0.40, W*0.25])
        apt_tbl.setStyle(_tbl_style(PURPLE))
        story.append(apt_tbl)
    else:
        story.append(Paragraph("No appointment records found.", s["body"]))

    # ── Footer ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=GRAY_MID))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "This report is generated by the Diabetes Prediction System and is for informational purposes only. "
        "Always consult a qualified healthcare professional for medical advice.",
        s["small"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf


def generate_payment_receipt_pdf(payment_info, patient_info):
    """
    Generate a payment receipt PDF.
    Falls back to HTML if reportlab is not installed.
    Returns: BytesIO buffer.
    """
    if not _REPORTLAB:
        return _html_payment_receipt(payment_info, patient_info)
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=25*mm, rightMargin=25*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )
    s = _styles()
    W = A4[0] - 50*mm
    story = []

    # Header
    hdr = Table([[Paragraph("🏥  Diabetes Prediction System", s["title"])]],
                colWidths=[W])
    hdr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
    ]))
    story.append(hdr)

    sub = Table([[Paragraph("PAYMENT RECEIPT", s["subtitle"])]],
                colWidths=[W])
    sub.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_MID),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(sub)
    story.append(Spacer(1, 8*mm))

    pi = patient_info or {}
    pay = payment_info or {}

    # Receipt details
    details = [
        ["Receipt No.",    pay.get("payment_id", "—"),   "Date", pay.get("date", "—")[:10]],
        ["Patient",        pi.get("name", pi.get("username", "—")), "Method", pay.get("payment_method", "—")],
        ["Invoice ID",     pay.get("invoice_id", "—"),   "Status", pay.get("status", "—").upper()],
    ]
    det_tbl = Table(details, colWidths=[W*0.18, W*0.32, W*0.18, W*0.32])
    det_tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BLUE_DARK),
        ("TEXTCOLOR", (2, 0), (2, -1), BLUE_DARK),
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("GRID",      (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(det_tbl)
    story.append(Spacer(1, 6*mm))

    # Amount summary
    story.append(Paragraph("Payment Summary", s["h2"]))
    story.append(HRFlowable(width=W, thickness=1, color=BLUE_MID, spaceAfter=4))

    services_note = pay.get("notes", "Healthcare Services")
    amt_data = [
        ["Description", "Amount (ETB)"],
        [services_note, f"ETB {float(pay.get('amount', 0)):.2f}"],
        ["Tax", f"ETB {float(pay.get('tax', 0)):.2f}"],
        ["Discount", f"ETB {float(pay.get('discount', 0)):.2f}"],
        ["TOTAL", f"ETB {float(pay.get('total_amount', 0)):.2f}"],
    ]
    amt_tbl = Table(amt_data, colWidths=[W*0.65, W*0.35])
    amt_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  BLUE_DARK),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTNAME",    (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND",  (0, -1), (-1, -1), GREEN),
        ("TEXTCOLOR",   (0, -1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, GRAY_LIGHT]),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("ALIGN",       (1, 0), (1, -1),  "RIGHT"),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(amt_tbl)
    story.append(Spacer(1, 10*mm))

    # Thank you
    thank_tbl = Table([[Paragraph("Thank you for your payment!", s["center"])]],
                      colWidths=[W])
    thank_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(thank_tbl)
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=GRAY_MID))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "This is a computer-generated receipt. Diabetes Prediction System © 2026",
        s["small"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf


# ── HTML fallbacks (used when reportlab is not installed) ────────────────────

def _html_patient_report(patient_info, predictions, prescriptions, lab_results, appointments):
    """Return a printable HTML report as BytesIO when reportlab is unavailable."""
    pi = patient_info or {}
    now = datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')

    def rows(data, cols):
        if not data:
            return '<tr><td colspan="' + str(len(cols)) + '" style="text-align:center;color:#94a3b8;">No records</td></tr>'
        return ''.join(
            '<tr>' + ''.join(f'<td style="padding:6px 10px;border-bottom:1px solid #f1f5f9;">{str(row.get(c,"—"))}</td>' for c in cols) + '</tr>'
            for row in data
        )

    def thead(cols):
        return '<tr>' + ''.join(f'<th style="padding:8px 10px;background:#1e3a8a;color:#fff;text-align:left;">{c}</th>' for c in cols) + '</tr>'

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Health Report - {pi.get('name','Patient')}</title>
<style>body{{font-family:Arial,sans-serif;color:#334155;margin:0;padding:20px;}}
h1{{background:#1e3a8a;color:#fff;padding:16px;margin:0;}}
h2{{color:#1e3a8a;border-bottom:2px solid #2563eb;padding-bottom:4px;margin-top:24px;}}
table{{width:100%;border-collapse:collapse;margin-bottom:16px;}}
th{{background:#1e3a8a;color:#fff;}}
tr:nth-child(even){{background:#f1f5f9;}}
.info-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;background:#eff6ff;padding:12px;border-radius:8px;}}
.info-item span{{font-weight:700;color:#1e3a8a;}}
footer{{margin-top:32px;font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:8px;}}
@media print{{body{{padding:0;}}}}
</style></head><body>
<h1>🏥 Diabetes Prediction System — Patient Health Report</h1>
<p style="color:#64748b;font-size:13px;">Generated: {now}</p>
<h2>Patient Information</h2>
<div class="info-grid">
  <div class="info-item"><span>Patient ID:</span> {pi.get('patient_id','—')}</div>
  <div class="info-item"><span>Name:</span> {pi.get('name', pi.get('username','—'))}</div>
  <div class="info-item"><span>Email:</span> {pi.get('email','—')}</div>
  <div class="info-item"><span>Blood Group:</span> {pi.get('blood_group','—')}</div>
</div>
<h2>Prediction History</h2>
<table>{thead(['Date','Result','Risk Level','Probability %'])}
{''.join(f"<tr><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{str(p.get('date',p.get('created_at',''))[:10])}</td><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{p.get('result','—')}</td><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{p.get('risk_level','—')}</td><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{p.get('probability_percent',0):.1f}%</td></tr>" for p in (predictions or [])) or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:8px;">No records</td></tr>'}
</table>
<h2>Prescriptions</h2>
<table>{thead(['Date','Medication','Dosage','Status'])}
{''.join(f"<tr><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{str(r.get('date',r.get('created_at',''))[:10])}</td><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{r.get('medication','—')}</td><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{r.get('dosage','—')}</td><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{r.get('status','—')}</td></tr>" for r in (prescriptions or [])) or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:8px;">No records</td></tr>'}
</table>
<h2>Lab Results</h2>
<table>{thead(['Date','Test Name','Result','Status'])}
{''.join(f"<tr><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{str(l.get('date',l.get('created_at',''))[:10])}</td><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{l.get('test_name','—')}</td><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{str(l.get('results','—'))}</td><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{l.get('status','—')}</td></tr>" for l in (lab_results or [])) or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:8px;">No records</td></tr>'}
</table>
<h2>Appointments</h2>
<table>{thead(['Date','Time','Reason','Status'])}
{''.join(f"<tr><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{str(a.get('date','—'))}</td><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{a.get('time','—')}</td><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{a.get('reason','—')}</td><td style='padding:6px 10px;border-bottom:1px solid #f1f5f9;'>{a.get('status','—')}</td></tr>" for a in (appointments or [])) or '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:8px;">No records</td></tr>'}
</table>
<footer>This report is for informational purposes only. Always consult a qualified healthcare professional.</footer>
</body></html>"""
    buf = BytesIO(html.encode('utf-8'))
    buf.seek(0)
    return buf


def _html_payment_receipt(payment_info, patient_info):
    """Return a printable HTML receipt as BytesIO when reportlab is unavailable."""
    pi = patient_info or {}
    pay = payment_info or {}
    now = datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Payment Receipt - {pay.get('payment_id','')}</title>
<style>body{{font-family:Arial,sans-serif;color:#334155;margin:0;padding:20px;max-width:600px;margin:0 auto;}}
h1{{background:#1e3a8a;color:#fff;padding:16px;margin:0;text-align:center;}}
.sub{{background:#2563eb;color:#fff;text-align:center;padding:6px;font-size:13px;}}
table{{width:100%;border-collapse:collapse;margin:16px 0;}}
td{{padding:8px 12px;border:1px solid #e2e8f0;}}
.label{{font-weight:700;color:#1e3a8a;background:#eff6ff;width:30%;}}
.total{{background:#059669;color:#fff;font-weight:700;font-size:16px;}}
.thanks{{background:#eff6ff;text-align:center;padding:16px;border-radius:8px;color:#1e3a8a;font-weight:700;margin-top:16px;}}
footer{{margin-top:24px;font-size:11px;color:#94a3b8;text-align:center;}}
@media print{{body{{padding:0;}}}}
</style></head><body>
<h1>🏥 Diabetes Prediction System</h1>
<div class="sub">PAYMENT RECEIPT &nbsp;|&nbsp; Generated: {now}</div>
<table>
  <tr><td class="label">Receipt No.</td><td>{pay.get('payment_id','—')}</td><td class="label">Date</td><td>{str(pay.get('date','—'))[:10]}</td></tr>
  <tr><td class="label">Patient</td><td>{pi.get('name', pi.get('username','—'))}</td><td class="label">Method</td><td>{pay.get('payment_method','—')}</td></tr>
  <tr><td class="label">Invoice ID</td><td>{pay.get('invoice_id','—')}</td><td class="label">Status</td><td>{str(pay.get('status','—')).upper()}</td></tr>
</table>
<table>
  <tr><th style="background:#1e3a8a;color:#fff;padding:8px;">Description</th><th style="background:#1e3a8a;color:#fff;padding:8px;text-align:right;">Amount (ETB)</th></tr>
  <tr><td style="padding:8px;">{pay.get('notes','Healthcare Services')}</td><td style="padding:8px;text-align:right;">ETB {float(pay.get('amount',0)):.2f}</td></tr>
  <tr><td style="padding:8px;">Tax</td><td style="padding:8px;text-align:right;">ETB {float(pay.get('tax',0)):.2f}</td></tr>
  <tr><td style="padding:8px;">Discount</td><td style="padding:8px;text-align:right;">ETB {float(pay.get('discount',0)):.2f}</td></tr>
  <tr class="total"><td style="padding:8px;">TOTAL</td><td style="padding:8px;text-align:right;">ETB {float(pay.get('total_amount',0)):.2f}</td></tr>
</table>
<div class="thanks">Thank you for your payment!</div>
<footer>This is a computer-generated receipt. Diabetes Prediction System &copy; 2026</footer>
</body></html>"""
    buf = BytesIO(html.encode('utf-8'))
    buf.seek(0)
    return buf
