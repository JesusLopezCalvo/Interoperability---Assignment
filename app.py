# app.py
# Interoperability Needs Analysis & System Evaluation
# - Part 1 "Interface Planning" drives Part 2 (single source of truth)
# - Single-select checkbox tables (deselect supported)
# - Full explanatory text preserved
# - CSS/HTML to improve readability and sectioning
# - PDF tables wrap text and fit page width (no overlap)

import io
from datetime import datetime
from xml.sax.saxutils import escape

import streamlit as st
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ------------------------
# Streamlit page config
# ------------------------
st.set_page_config(
    page_title="Interoperability Needs Analysis & System Evaluation",
    layout="wide"
)
STYLES = """
<style>
:root {
  --base-font-size: 25px;
  --accent: #0b3d91;
  --accent-2: #8b0000;
  --muted: #f7f9fc;
}

html, body, [class*="css"] { font-size: var(--base-font-size); }
.block-container { padding-top: 0.5rem !important; padding-bottom: 4rem !important; max-width: 1600px !important; }

/* Headings */
h1, .stMarkdown h1, .stTitle { color: var(--accent); font-size: 2rem; margin-top: .25rem; }
h2, .stMarkdown h2, .stHeader>div>h2, .stSubheader>div>h2 {
  color: var(--accent);
  border-left: 6px solid var(--accent);
  padding-left: .6rem;
  margin-top: 1.0rem;
}

/* Section card look */
.section-card {
  background: #fff;
  border: 1px solid #e6eaf2;
  box-shadow: 0 1px 8px rgba(13,39,80,.07);
  border-radius: 14px;
  padding: 1rem 1.1rem;
  margin: 1rem 0 1.25rem 0;
}
.section-title { font-weight: 700; color: var(--accent); font-size: 1.15rem; margin: 0 0 .25rem 0; }
.section-subtitle { color: #4a5568; font-size: .95rem; margin: 0 0 .5rem 0; }

/* Subtle separator */
hr.sep {
  border: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, #cfd8ea, transparent);
  margin: 12px 0 18px 0;
}

/* Table-like header band for column-based layouts */
.table-band {
  background: var(--muted);
  border: 1px solid #e6eaf2;
  border-radius: 10px;
  padding: .4rem .6rem;
  margin: .25rem 0 .25rem 0;
}
.small { font-size: .92rem !important; color: #445; }

/* TABLE IMPROVEMENTS */
/* Prevent header text wrapping */
.stTable thead th {
  white-space: nowrap !important;
  padding: 10px 14px !important;
}

/* Auto-adjust table width to content */
.stTable table {
  width: auto !important;
  min-width: 100%;
}

/* Better column sizing */
.stTable td {
  padding: 8px 14px !important;
}

/* Alerts & captions */
.stAlert div[role="alert"] { font-size: 1rem; }
.stCaption { font-size: .92rem !important; color: #5b6b7e !important; }

/* Make radios / checkboxes text larger */
.stRadio > label, .stCheckbox > label { font-size: 1rem !important; }

/* Streamlit table font */
.stTable > div { font-size: .96rem; }

/* Center content in the "Select" column cells */
.select-cell { display:flex; align-items:center; justify-content:center; }
</style>
"""

st.markdown(STYLES, unsafe_allow_html=True)

# ------------------------
# Shared options & descriptions
# ------------------------
STANDARDS = ["HL7 v2", "DICOM", "FHIR"]
STANDARD_DESC = {
    "HL7 v2": {
        "Used By": "Meditech EHR (legacy)",
        "What It Does": "Sends patient data, orders, and results through text-based messages separated by pipes |.",
        "Limitations": "Fast but unstructured; no API; doesn’t handle images."
    },
    "DICOM": {
        "Used By": "Agfa PACS (imaging system)",
        "What It Does": "Stores and transmits images (X-rays, MRIs) with metadata (patient ID, modality, body part, date).",
        "Limitations": "Great for images, but doesn’t include full clinical notes or orders from EHRs."
    },
    "FHIR": {
        "Used By": "Modern systems and apps",
        "What It Does": "Web-based framework that represents data (patients, labs, imaging) as structured “resources.”",
        "Limitations": "Legacy systems often can’t use it without new modules or middleware."
    },
}

PLAN_ROWS = [
    {
        "Gap": "Data Silos",
        "Description": "EHR and PACS store data separately; clinicians must open two systems.",
        "Suggested Interface Type": "Interface Engine (Middleware)",
        "Suggested Fix": "Add/Optimize Interface Engine",
        "Reference": "CMS Criterion 3 – Data Availability"
    },
    {
        "Gap": "Inconsistent Patient IDs",
        "Description": "IDs differ in format/structure (e.g., “12345” vs “0012345”).",
        "Suggested Interface Type": "Interface Engine (Middleware)",
        "Suggested Fix": "Implement MPI",
        "Reference": "CMS Criterion 5 – Identity & Trust"
    },
    {
        "Gap": "Missing Clinical Context",
        "Description": "Imaging data lacks clinical notes or order linkage.",
        "Suggested Interface Type": "Interface Engine (Middleware)",
        "Suggested Fix": "Map HL7→DICOM Metadata",
        "Reference": "ONC §170.315(b) – Transitions of Care"
    },
    {
        "Gap": "No FHIR Connection",
        "Description": "Legacy EHR cannot use FHIR APIs for modern data exchange.",
        "Suggested Interface Type": "FHIR API",
        "Suggested Fix": "Enable/Upgrade EHR FHIR",
        "Reference": "ONC §170.315(g)(10) – API Exchange"
    },
    {
        "Gap": "Data Integrity & Security",
        "Description": "Lack of audit trails or accuracy checks between systems.",
        "Suggested Interface Type": "Interface Engine (Middleware)",
        "Suggested Fix": "Enable audit logs & integrity checks; shared audit trail",
        "Reference": "ONC §170.315(d)(9); CMS Criterion 5 – Identity & Trust"
    },
]

INTEGRITY_ROWS = [
    {
        "Area": "Data Accuracy (Integrity)",
        "Plain Meaning": "Ensure information stays correct and unchanged during transfer/storage.",
        "Likely Gap": "EHR/PACS show mismatched IDs/dates; altered payloads not detected.",
        "Improvement": "Enable message checksums/hashes; verify accession/MRN on receipt.",
        "Standards": "ONC §170.315(d)(9); HIPAA 164.312(c)(1)"
    },
    {
        "Area": "Access Tracking (Audit Logs)",
        "Plain Meaning": "Record who viewed/edited data to support privacy & accountability.",
        "Likely Gap": "Separate, incomplete audit trails; clocks not synchronized.",
        "Improvement": "Unified audit (engine/SIEM), unique IDs, NTP time sync, regular review.",
        "Standards": "ONC §170.315(d); HIPAA 164.312(b); CMS Identity/Security/Trust"
    },
    {
        "Area": "Error Detection & Alerts",
        "Plain Meaning": "Detect and surface failed transfers quickly.",
        "Likely Gap": "Orders/results fail silently; no retry queues or alerts.",
        "Improvement": "ACK/NACK monitoring, retries, routed alerts to on-call IT/imaging.",
        "Standards": "AHRQ Evaluation (data quality); supports CMS Data Availability"
    },
    {
        "Area": "Patient Identity Management (MPI)",
        "Plain Meaning": "One accurate identity across systems.",
        "Likely Gap": "Duplicate/mismatched MRNs; weak demographic matching.",
        "Improvement": "Implement/strengthen MPI; matching thresholds; periodic deduping.",
        "Standards": "CMS Identity & Trust"
    },
]

RECOMMENDED_INTEGRITY = {
    "Data Silos": "Access Tracking (Audit Logs)",
    "Inconsistent Patient IDs": "Patient Identity Management (MPI)",
    "Missing Clinical Context": "Data Accuracy (Integrity)",
    "No FHIR Connection": "Error Detection & Alerts",
    "Data Integrity & Security": "Data Accuracy (Integrity)",
}


HELP_LINKS = [
    "CMS Interoperability Framework: https://www.cms.gov/health-technology-ecosystem/interoperability-framework",
    "ONC §170.315 Certification Criteria: https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-D/part-170/subpart-C/section-170.315",
    "ONC Interoperability Standards Advisory (ISA): https://www.healthit.gov/isa",
    "AHRQ Health IT Evaluation Toolkit: https://digital.ahrq.gov/sites/default/files/docs/page/health-information-technology-evaluation-toolkit-2009-update.pdf",
    "HIMSS Interoperability in Healthcare: https://gkc.himss.org/resources/interoperability-healthcare",
    "Meditech Expanse Overview: https://ehr.meditech.com/ehr-solutions/meditech-expanse",
    "Agfa Enterprise Imaging Platform: https://www.agfahealthcare.com/enterprise-imaging-platform/",
]

# ------------------------
# PDF Helpers (wrapped cells + correct widths)
# ------------------------
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="H0", fontSize=16, leading=20, spaceAfter=10, textColor=colors.HexColor("#0b3d91")))
styles.add(ParagraphStyle(name="H1", fontSize=14, leading=18, spaceAfter=8, textColor=colors.HexColor("#0b3d91")))
styles.add(ParagraphStyle(name="H2", fontSize=12, leading=16, spaceAfter=6, textColor=colors.HexColor("#8b0000")))
styles.add(ParagraphStyle(name="Body", fontSize=11, leading=14.6))
styles.add(ParagraphStyle(name="Tiny", fontSize=9.6, leading=13, textColor=colors.grey))
styles.add(ParagraphStyle(name="Cell", fontSize=10.5, leading=14))           # table cell body
styles.add(ParagraphStyle(name="CellBold", fontSize=10.5, leading=14))       # for bold if needed

def P(text, style="Cell"):
    """Convert plain text to a ReportLab Paragraph for wrapping."""
    if isinstance(text, Paragraph):
        return text
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])

def make_table(head, rows, col_widths=None, header_bg="#0b3d91"):
    """Create a wrapped table. All cells are Paragraphs; widths fit page width."""
    head_p = [P(h, "CellBold") for h in head]
    rows_p = [[P(c, "Cell") for c in r] for r in rows]
    data = [head_p] + rows_p
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor(header_bg)),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#b7b7b7")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("WORDWRAP", (0,0), (-1,-1), True),
    ]))
    return t

def build_pdf(selections):
    """
    selections keys:
      - plan_gap, plan_iface, plan_fix, plan_ref
      - p2_integrity
      - include_all_options (bool)
    """
    def sel_or_dash(val):
        return val if val and val not in ("— select —", "— choose —") else "—"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER, title="Interoperability Needs Analysis & System Evaluation",
        leftMargin=50, rightMargin=50, topMargin=40, bottomMargin=40
    )
    story = []

    # Title
    story.append(Paragraph("Interoperability Needs Analysis & System Evaluation", styles["H0"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Tiny"]))
    story.append(Spacer(1, 8))

    # ------------------ PART 1 ------------------
    story.append(Paragraph("Part 1 – Interoperability Needs Analysis", styles["H1"]))
    story.append(Paragraph("(Guided by CMS Promoting Interoperability Program, ONC Interoperability Standards Advisory, and HIMSS Interoperability in Healthcare)", styles["Body"]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("1.1 Purpose", styles["H2"]))
    story.append(Paragraph(
        "Your goal in Part 1 is to identify where Riverbend’s systems fall short of CMS interoperability expectations. "
        "You will analyze how data moves between the legacy Meditech EHR (HL7 v2) and the Agfa PACS system (DICOM + FHIR), "
        "describe the standards they use, and determine where improvements are needed to meet Promoting Interoperability (PI) requirements.",
        styles["Body"]
    ))

    story.append(Paragraph("1.2 Introductory Reading", styles["H2"]))
    for link in [
        "Integrating DICOM with HL7: https://radsource.us/dicom-vs-hl7/",
        "HL7 v2 Integration Challenges in Hospitals: https://huspi.com/blog-open/hl7-v2-integration-challenges-in-hospitals/",
        "What is HL7 V2? A Guide in 2025: https://flatirons.com/blog/what-is-hl7-v2/",
        "What is DICOM & why it matters: https://www.intelerad.com/en/2023/02/23/handling-dicom-medical-imaging-data/",
        "What is HL7 FHIR?: https://www.particlehealth.com/blog/what-is-fhir",
        "FHIR vs HL7: https://binariks.com/blog/fhir-vs-hl7/"
    ]:
        story.append(Paragraph(f"• {link}", styles['Body']))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1.3 Background — What Each Standard Does", styles["H2"]))
    story.append(Paragraph(
        "Understanding how each standard works helps you explain why interoperability gaps exist between Riverbend’s systems.",
        styles["Body"]
    ))
    # PAGE WIDTH AVAILABLE = 612 - 50 - 50 = 512pt
    table_13_head = ["Standard", "Used By", "What It Does (Simplified)", "Limitations / Challenges"]
    table_13_rows = [
        ["HL7 v2", "Meditech EHR (legacy)", "Sends patient data, orders, and results through text-based messages separated by pipes |.", "Fast but unstructured; no API; doesn’t handle images."],
        ["DICOM", "Agfa PACS (imaging system)", "Stores and transmits images (X-rays, MRIs) with metadata (patient ID, modality, body part, date).", "Great for images, but doesn’t include full clinical notes or orders from EHRs."],
        ["FHIR", "Modern systems and apps", "Web-based framework that represents data (patients, labs, imaging) as structured “resources.”", "Legacy systems often can’t use it without new modules or middleware."],
    ]
    story.append(make_table(table_13_head, table_13_rows, col_widths=[70, 110, 180, 152], header_bg="#0b3d91"))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Why this matters:", styles["H2"]))
    story.append(Paragraph(
        "CMS expects health systems to use open standards that allow data to move safely and completely across departments. "
        "When systems use different standards (like HL7 v2 vs. DICOM/FHIR), data often gets fragmented or delayed, affecting patient safety and care coordination.",
        styles["Body"]
    ))
    story.append(Paragraph("Helpful Reading:", styles["H2"]))
    for link in [
        "• CMS Interoperability Framework",
        "• ONC Interoperability Standards Advisory",
        "• HIMSS: Interoperability in Healthcare"
    ]:
        story.append(Paragraph(link, styles["Body"]))

    story.append(Paragraph("1.4 CMS and ONC Expectations", styles["H2"]))
    story.append(Paragraph("Review these resources before writing your analysis:", styles["Body"]))
    for line in [
        "• CMS Interoperability Framework: defines interoperability “criteria” such as Data Availability, Network Connectivity, and Identity/Trust.",
        "• ONC Health IT Certification Criteria (§170.315): describes what certified systems must do (APIs, data integrity, privacy, and exchange functions).",
        "• ONC Health IT Certification Test Methods: https://www.healthit.gov/topic/certification-ehrs/onc-health-it-certification-program-test-method"
    ]:
        story.append(Paragraph(line, styles["Body"]))
    story.append(Paragraph("Focus on these ideas:", styles["Body"]))
    for line in [
        "• Systems must exchange and display data consistently (CMS Criterion 3).",
        "• Systems must verify data accuracy and integrity (ONC §170.315(d)(9)).",
        "• Systems should use FHIR APIs for patient and population-level access (ONC §170.315(g)(10)).",
    ]:
        story.append(Paragraph(line, styles["Body"]))

    story.append(Paragraph("1.5 Analyze and Identify Gaps (template)", styles["H2"]))
    table_15_head = ["Step", "What to Do", "Guiding Question", "Example (Reasoned Assumption)"]
    table_15_rows = [
        ["1. Select Two Standards to Compare", "Choose HL7 v2 vs. DICOM, or HL7 v2 vs. FHIR.", "Which standard does each system rely on?", "Meditech uses HL7 v2; Agfa uses DICOM and FHIR."],
        ["2. Describe How They Interact", "Explain how the systems communicate.", "What is sent? How is it received?", "EHR sends an HL7 order; PACS returns DICOM images and a report."],
        ["3. Identify a Gap", "Point out where exchange fails or data is lost.", "Is any key information missing or mismatched?", "EHR can’t show images or metadata from PACS."],
        ["4. Propose a Fix", "Suggest one realistic improvement.", "Would an interface engine or API help?", "Add middleware that converts HL7 v2 messages into FHIR/DICOM."],
        ["5. Explain the Impact", "Connect your fix to CMS/ONC standards.", "What criterion would this satisfy?", "Meets CMS “Data Availability” and ONC API criteria."],
    ]
    story.append(make_table(table_15_head, table_15_rows, col_widths=[120, 140, 120, 132], header_bg="#8b0000"))

    story.append(Paragraph("1.6 Example Analysis", styles["H2"]))
    story.append(Paragraph(
        "Riverbend’s legacy Meditech EHR relies on HL7 v2 messages, which can send orders and results but cannot natively display DICOM images from the Agfa PACS. "
        "While Agfa supports FHIR APIs for modern data exchange, the EHR cannot consume this format. This creates a gap where clinicians must view imaging and reports separately, "
        "causing delays and fragmented records. Adding a middleware interface that converts HL7 v2 messages into FHIR or DICOM format would allow more consistent data exchange, "
        "fulfilling CMS’s data-availability and ONC’s API requirements.",
        styles["Body"]
    ))
    story.append(Paragraph("Instructor note: This is an example only. Students must expand with their own analysis, metrics, citations, and applicable standards.", styles["Tiny"]))

    story.append(Paragraph("1.7 Your Selection (Interface Planning summary)", styles["H2"]))
    plan_gap = sel_or_dash(selections.get("plan_gap"))
    plan_iface = sel_or_dash(selections.get("plan_iface"))
    plan_fix = sel_or_dash(selections.get("plan_fix"))
    plan_ref = sel_or_dash(selections.get("plan_ref"))
    story.append(make_table(
        ["Item", "Selection"],
        [
            ["Gap", plan_gap],
            ["Suggested Interface Type", plan_iface],
            ["Suggested Fix", plan_fix],
            ["Standard Reference", plan_ref],
        ],
        col_widths=[150, 362],
        header_bg="#0b3d91"
    ))

    # ------------------ PART 2 ------------------
    story.append(PageBreak())
    story.append(Paragraph("Part 2 – System Evaluation & Improvement Plan", styles["H1"]))
    story.append(Paragraph("(Guided by CMS Promoting Interoperability Program, ONC Certification Criteria, and AHRQ Health IT Evaluation Toolkit)", styles["Body"]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("2.1 Purpose", styles["H2"]))
    story.append(Paragraph(
        "Now that you’ve identified where interoperability breaks down, your goal in Part 2 is to evaluate the system’s current capabilities and suggest measurable improvements. "
        "Use federal guidance (CMS Framework, ONC Criteria, AHRQ Toolkit) to ensure your plan supports data integrity, workflow efficiency, and compliance.",
        styles["Body"]
    ))

    story.append(Paragraph("2.2 Evaluate How Systems Connect (Interfaces)", styles["H2"]))
    story.append(Paragraph("(Based on CMS Interoperability Framework – Criteria 3 & 5 and ONC §170.315(g)(10))", styles["Body"]))
    story.append(Paragraph("Background", styles["H2"]))
    for line in [
        "• Meditech EHR (legacy): uses HL7 v2 messages (text-based orders/results).",
        "• Agfa PACS (modern): uses DICOM for imaging data and FHIR APIs for structured exchange.",
        "This means Riverbend can send text orders and receive reports but likely cannot share images or metadata automatically.",
    ]:
        story.append(Paragraph(line, styles["Body"]))

    story.append(Paragraph("Common Gaps and Fixes", styles["H2"]))
    table_22_head = ["Gap Type", "Description", "Example at Riverbend (Logical Assumption)", "Possible Fix", "Why It Matters / Standard Reference"]
    table_22_rows = [
        ["Data Silos", "EHR and PACS store data separately.", "Clinicians open two systems to view reports and images.", "Add an interface engine linking HL7 v2 and DICOM.", "CMS Criterion 3 – Data Availability."],
        ["Inconsistent Patient IDs", "IDs formatted differently in each system.", "“12345” in EHR vs. “0012345” in PACS.", "Implement a Master Patient Index (MPI).", "CMS Criterion 5 – Identity & Trust."],
        ["Missing Clinical Context", "Imaging data lacks notes or order details.", "PACS shows image only.", "Map HL7 order fields into DICOM metadata.", "ONC §170.315(b) – Transitions of Care."],
        ["No FHIR Connection", "Legacy EHR cannot use FHIR APIs.", "Agfa exposes FHIR but EHR can’t read it.", "Enable Meditech’s FHIR module or use translator middleware.", "ONC §170.315(g)(10) – API Exchange."],
        ["Data Integrity & Security", "Lack of accuracy checks or audit trails.", "EHR/PACS mismatch IDs, limited tracking.", "Enable audit logs & integrity checks; shared audit trail.", "ONC §170.315(d)(9); CMS Criterion 5 – Identity & Trust."],
    ]
    story.append(make_table(table_22_head, table_22_rows, col_widths=[90, 115, 120, 105, 82], header_bg="#0b3d91"))

    story.append(Spacer(1, 6))
    story.append(Paragraph("2.3 Evaluate Data Integrity and Security", styles["H2"]))
    story.append(Paragraph("(Based on ONC §170.315(d): Privacy and Security and CMS Criterion 5: Identity, Security & Trust)", styles["Body"]))
    story.append(Paragraph("Purpose", styles["H2"]))
    story.append(Paragraph("To ensure that Riverbend’s data remains accurate, secure, and auditable while being exchanged.", styles["Body"]))

    story.append(make_table(
        ["Item", "Selection"],
        [["Integrity/Security Focus", sel_or_dash(selections.get("p2_integrity"))]],
        col_widths=[190, 322],
        header_bg="#8b0000"
    ))

    story.append(Paragraph("2.4 Plan How to Evaluate Your Fix", styles["H2"]))
    story.append(Paragraph("(Guided by AHRQ Health IT Evaluation Toolkit – Sections II & III)", styles["Body"]))
    table_24_head = ["Evaluation Element", "Explanation", "Example"]
    table_24_rows = [
        ["Goal / Outcome", "What improvement do you want to see?", "“Reduce failed interface messages by 50%.”"],
        ["Metric to Measure", "A quantitative or qualitative measure.", "% of successful message transfers; time to access image report."],
        ["Data Source / Method", "How you’ll collect data.", "System logs, user survey, chart audit."],
        ["Who Collects Data", "Roles responsible.", "IT analyst, imaging supervisor."],
        ["Timeline / Feasibility", "When and how long to track.", "Weekly over 3 months."],
        ["Barriers", "Challenges or limitations.", "Staff time, cost, training needs."],
        ["Using Results", "How findings will guide improvement.", "Present at quality meeting to plan upgrades."],
    ]
    story.append(make_table(table_24_head, table_24_rows, col_widths=[140, 170, 202], header_bg="#0b3d91"))

    story.append(Paragraph("2.5 Reflection (200–300 Words)", styles["H2"]))
    story.append(Paragraph(
        "In your reflection, summarize what you learned about how interface design and data integrity affect interoperability. "
        "Discuss how your recommended fix aligns with CMS and ONC requirements and how your evaluation plan would measure its success.",
        styles["Body"]
    ))

    story.append(Paragraph("2.6 Key Resources", styles["H2"]))
    story.append(Paragraph('• CMS Interoperability Framework: https://www.cms.gov/health-technology-ecosystem/interoperability-framework', styles["Body"]))
    story.append(Paragraph('• <link href="https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-D/part-170/subpart-C/section-170.315">ONC §170.315 Certification Criteria (ecfr.gov)</link>', styles["Body"]))
    story.append(Paragraph('• ONC Interoperability Standards Advisory (ISA): https://www.healthit.gov/isa', styles["Body"]))
    story.append(Paragraph('• AHRQ Health IT Evaluation Toolkit: https://digital.ahrq.gov/sites/default/files/docs/page/health-information-technology-evaluation-toolkit-2009-update.pdf', styles["Body"]))
    story.append(Paragraph('• HIMSS Interoperability in Healthcare: https://gkc.himss.org/resources/interoperability-healthcare', styles["Body"]))
    story.append(Paragraph('• Meditech Expanse Overview: https://ehr.meditech.com/ehr-solutions/meditech-expanse', styles["Body"]))
    story.append(Paragraph('• Agfa Enterprise Imaging Platform: https://www.agfahealthcare.com/enterprise-imaging-platform/', styles["Body"]))

    if selections.get("include_all_options"):
        story.append(PageBreak())
        story.append(Paragraph("Appendix: All Interface Planning Options", styles["H1"]))
        all_head = ["Gap", "Suggested Interface Type", "Suggested Fix", "Standard Reference", "Selected"]
        all_rows = []
        for r in PLAN_ROWS:
            selected_mark = "✓" if (
                r["Gap"] == selections.get("plan_gap") and
                r["Suggested Interface Type"] == selections.get("plan_iface") and
                r["Suggested Fix"] == selections.get("plan_fix")
            ) else ""
            all_rows.append([r["Gap"], r["Suggested Interface Type"], r["Suggested Fix"], r["Reference"], selected_mark])
        story.append(make_table(all_head, all_rows, col_widths=[110, 140, 140, 102, 20], header_bg="#0b3d91"))

    doc.build(story)
    buf.seek(0)
    return buf

# ------------------------
# Utilities
# ------------------------
def slug(s: str) -> str:
    import re
    return re.sub(r'[^A-Za-z0-9_]+', '_', s)

def reset_other_checkboxes(checked_keys, keep_key):
    """Enforce single-select for checkbox rows by unchecking all but keep_key."""
    for k in checked_keys:
        if k != keep_key and st.session_state.get(k):
            st.session_state[k] = False

# ------------------------
# UI
# ------------------------
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.title("Interoperability Needs Analysis & System Evaluation")
st.markdown('<hr class="sep"></div>', unsafe_allow_html=True)

# --- PART 1 ---
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.header("Part 1 – Interoperability Needs Analysis")
st.write("(Guided by CMS Promoting Interoperability Program, ONC Interoperability Standards Advisory, and HIMSS Interoperability in Healthcare)")

st.subheader("1.1 Purpose")
st.write(
    "Your goal in Part 1 is to identify where Riverbend’s systems fall short of CMS interoperability expectations.\n"
    "You will analyze how data moves between the legacy Meditech EHR (HL7 v2) and the Agfa PACS system (DICOM + FHIR), "
    "describe the standards they use, and determine where improvements are needed to meet Promoting Interoperability (PI) requirements."
)

st.subheader("1.2 Introductory Reading")
st.markdown(
    "- Integrating DICOM with HL7: https://radsource.us/dicom-vs-hl7/\n"
    "- HL7 v2 Integration Challenges in Hospitals: https://huspi.com/blog-open/hl7-v2-integration-challenges-in-hospitals/\n"
    "- What is HL7 V2? A Guide in 2025: https://flatirons.com/blog/what-is-hl7-v2/\n"
    "- What is DICOM & why it matters: https://www.intelerad.com/en/2023/02/23/handling-dicom-medical-imaging-data/\n"
    "- What is HL7 FHIR?: https://www.particlehealth.com/blog/what-is-fhir\n"
    "- FHIR vs HL7: https://binariks.com/blog/fhir-vs-hl7/"
)

st.subheader("1.3 Background — What Each Standard Does")
st.write("Understanding how each standard works helps you explain why interoperability gaps exist between Riverbend’s systems.")
st.table({
    "Standard": ["HL7 v2", "DICOM", "FHIR"],
    "Used By": [STANDARD_DESC[s]["Used By"] for s in STANDARDS],
    "What It Does (Simplified)": [STANDARD_DESC[s]["What It Does"] for s in STANDARDS],
    "Limitations / Challenges": [STANDARD_DESC[s]["Limitations"] for s in STANDARDS]
})
st.markdown("**Why this matters:**  \n"
            "CMS expects health systems to use open standards that allow data to move safely and completely across departments.  \n"
            "When systems use different standards (like HL7 v2 vs. DICOM/FHIR), data often gets fragmented or delayed, affecting patient safety and care coordination.")
st.markdown("**Helpful Reading:**     \n - CMS Interoperability Framework: https://www.cms.gov/health-technology-ecosystem/interoperability-framework\n"
    "- **ONC §170.315 Certification Criteria:** [ecfr.gov — §170.315](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-D/part-170/subpart-C/section-170.315)\n"
    "- HIMSS Interoperability in Healthcare: https://gkc.himss.org/resources/interoperability-healthcare\n")

st.subheader("1.4 CMS and ONC Expectations")
st.write("Review these resources before writing your analysis:")
st.markdown("- CMS Interoperability Framework: defines interoperability “criteria” such as Data Availability, Network Connectivity, and Identity/Trust.\n"
            "- **ONC Health IT Certification Criteria (§170.315):** [ecfr.gov — §170.315](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-D/part-170/subpart-C/section-170.315)\n"
            "- ONC Health IT Certification Test Methods: https://www.healthit.gov/topic/certification-ehrs/onc-health-it-certification-program-test-method")
st.write("Focus on these ideas:")
st.markdown("- Systems must exchange and display data consistently (CMS Criterion 3).\n"
            "- Systems must verify data accuracy and integrity (ONC §170.315(d)(9)).\n"
            "- Systems should use FHIR APIs for patient and population-level access (ONC §170.315(g)(10)).")

st.subheader("1.5 Analyze and Identify Gaps")
st.table({
    "Step": [
        "1. Select One Standards to Compare",
        "2. Describe How They Interact",
        "3. Identify a Gap",
        "4. Propose a Fix",
        "5. Explain the Impact"
    ],
    "What to Do": [
        "Choose HL7 v2 vs. DICOM, or HL7 v2 vs. FHIR.",
        "Explain how the systems communicate.",
        "Point out where exchange fails or data is lost.",
        "Suggest one realistic improvement.",
        "Connect your fix to CMS/ONC standards."
    ],
    "Guiding Question": [
        "Which standard does each system rely on?",
        "What is sent? How is it received?",
        "Is any key information missing or mismatched?",
        "Would an interface engine or API help?",
        "What criterion would this satisfy?"
    ],
    "Example (Reasoned Assumption)": [
        "Meditech uses HL7 v2; Agfa uses DICOM and FHIR.",
        "EHR sends an HL7 order; PACS returns DICOM images and a report.",
        "EHR can’t show images or metadata from PACS.",
        "Add middleware that converts HL7 v2 messages into FHIR/DICOM.",
        "Meets CMS “Data Availability” and ONC API criteria."
    ]
})

st.subheader("1.6 Example Analysis")
st.write(
    "Riverbend’s legacy Meditech EHR relies on HL7 v2 messages, which can send orders and results but cannot natively display DICOM images from the Agfa PACS. "
    "While Agfa supports FHIR APIs for modern data exchange, the EHR cannot consume this format. This creates a gap where clinicians must view imaging and reports separately, "
    "causing delays and fragmented records. Adding a middleware interface that converts HL7 v2 messages into FHIR or DICOM format would allow more consistent data exchange, "
    "fulfilling CMS’s data-availability and ONC’s API requirements."
)
st.warning(
    "**Example only — do not submit this paragraph as your own.**\n"
    "Use it as a starting point. Your report must **add your own analysis** and **cite sources**.\n\n"
    "**For full credit, include:**\n"
    "1) A specific gap and matching fix from **your** Interface Planning choice\n"
    "2) At least **two** supporting sources (reading list or similar)\n"
    "3) One **measurable goal + metric** (e.g., cut image lookup time by 30% and how you’ll measure it)\n"
    "4) One **standard/reg** that applies (CMS PI, ONC §170.315, HIPAA)\n"
    "5) A short **feasibility plan** (who, timeline, barriers)\n\n"
    "_If you copy the Example Analysis paragraph as-is, you won't receive full credit_"
)


# --- 1.7: Interface Planning (single-select checkbox table — drives Part 2) ---
st.subheader("1.7 Your Selection – Interface Planning (single select)")
st.caption("Choose the row that best represents the gap, interface type, and fix for Riverbend’s systems. This will drive the Part 2 content.")


cols_hdr = st.columns([2, 4, 2.6, 2.6, 2.4, 1.0])
cols_hdr[0].markdown("**Gap**")
cols_hdr[1].markdown("**Description**")
cols_hdr[2].markdown("**Suggested Interface Type**")
cols_hdr[3].markdown("**Suggested Fix**")
cols_hdr[4].markdown("**Standard Reference**")
cols_hdr[5].markdown("**Select**")

checked_keys = []
chosen_idx = None
for i, row in enumerate(PLAN_ROWS):
    c = st.columns([2, 4, 2.6, 2.6, 2.4, 1.0])
    c[0].write(row["Gap"])
    c[1].write(row["Description"])
    c[2].write(row["Suggested Interface Type"])
    c[3].write(row["Suggested Fix"])
    c[4].write(row["Reference"])
    key = f"plan_row_{i}_{slug(row['Gap'])}"
    checked = c[5].checkbox("", key=key)
    if checked:
        checked_keys.append(key)
        chosen_idx = i

if len(checked_keys) > 1:
    st.warning("Please select only one option. Keeping the first checked and unchecking the rest.")
    keep_key = checked_keys[0]
    reset_other_checkboxes(checked_keys, keep_key)

plan_selected = None
for i, row in enumerate(PLAN_ROWS):
    key = f"plan_row_{i}_{slug(row['Gap'])}"
    if st.session_state.get(key):
        plan_selected = row
        break

if plan_selected:
    st.success(
        f"**Selected:** {plan_selected['Gap']} → {plan_selected['Suggested Interface Type']} → {plan_selected['Suggested Fix']} "
        f"({plan_selected['Reference']})"
    )
else:
    st.info("Select exactly one row above to drive the evaluation sections in Part 2.")
st.markdown('</div>', unsafe_allow_html=True)  # close section card

# --- PART 2 ---
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.header("Part 2 – System Evaluation & Improvement Plan")
st.write("(Guided by CMS Promoting Interoperability Program, ONC Certification Criteria, and AHRQ Health IT Evaluation Toolkit)")

st.subheader("2.1 Purpose")
st.write(
    "Now that you’ve identified where interoperability breaks down, your goal in Part 2 is to evaluate the system’s current capabilities and suggest measurable improvements. "
    "Use federal guidance (CMS Framework, ONC Criteria, AHRQ Toolkit) to ensure your plan supports data integrity, workflow efficiency, and compliance."
)

st.subheader("2.2 Evaluate How Systems Connect (Interfaces)")
st.write("(Based on CMS Interoperability Framework – Criteria 3 & 5 and ONC §170.315(g)(10))")
st.markdown("**Background**\n- Meditech EHR (legacy): uses HL7 v2 messages (text-based orders/results).\n- Agfa PACS (modern): uses DICOM for imaging data and FHIR APIs for structured exchange.\nThis means Riverbend can send text orders and receive reports but likely cannot share images or metadata automatically.")

if plan_selected:
    st.info(
        f"**Selected plan**  \n"
        f"- Gap: {plan_selected['Gap']}  \n"
        f"- Interface Type: {plan_selected['Suggested Interface Type']}  \n"
        f"- Fix: {plan_selected['Suggested Fix']}  \n"
        f"- Reference: {plan_selected['Reference']}"
    )



st.markdown('<hr class="sep">', unsafe_allow_html=True)

# -------------------------------
# 2.3 – Integrity/Security Focus (single table + single-select CHECKBOXES)
# -------------------------------
st.subheader("2.3 – Integrity/Security Focus (single selection)")
recommended_area = RECOMMENDED_INTEGRITY.get(plan_selected["Gap"]) if plan_selected else None

# Quick actions
btn_cols = st.columns([1.4, 1.2, 6])
with btn_cols[0]:
    if st.button("Use recommended", disabled=not recommended_area):
        # Check only the recommended row
        for i, row in enumerate(INTEGRITY_ROWS):
            st.session_state[f"p2_integrity_{i}_{slug(row['Area'])}"] = (row["Area"] == recommended_area)
        st.rerun()
with btn_cols[1]:
    if st.button("Clear selection"):
        for i, row in enumerate(INTEGRITY_ROWS):
            st.session_state[f"p2_integrity_{i}_{slug(row['Area'])}"] = False
        st.rerun()

if not any(st.session_state.get(f"p2_integrity_{i}_{slug(r['Area'])}", False) for i, r in enumerate(INTEGRITY_ROWS)) and recommended_area:
    st.caption(f"**Recommended based on your selected gap:** {recommended_area}")

hdr = st.columns([2.5, 3.6, 3.0, 3.2, 2.6, 1.0])
hdr[0].markdown("**Area**")
hdr[1].markdown("**Plain Meaning**")
hdr[2].markdown("**Likely Gap**")
hdr[3].markdown("**Improvement**")
hdr[4].markdown("**Standards**")
hdr[5].markdown("**Select**")

integrity_checked_keys = []
selected_area = None

for i, row in enumerate(INTEGRITY_ROWS):
    c = st.columns([2.5, 3.6, 3.0, 3.2, 2.6, 1.0])
    c[0].write(row["Area"])
    c[1].write(row["Plain Meaning"])
    c[2].write(row["Likely Gap"])
    c[3].write(row["Improvement"])
    c[4].write(row["Standards"])
    key = f"p2_integrity_{i}_{slug(row['Area'])}"
    if c[5].checkbox("", key=key):
        integrity_checked_keys.append(key)

    # Determine selected area while looping
    if st.session_state.get(key, False):
        selected_area = row["Area"]

    # 🔧 CHANGED: render Select cell (✅ / Recommended) inside the row
    # 🔧 CHANGED: render Select cell (✅ / Recommended) inside the row
    is_selected = (selected_area == row["Area"])
    is_recommended = (not selected_area) and (recommended_area == row["Area"])

    badge_html = '<span class="badge-rec">Recommended</span>'
    parts = []
    if is_selected:
        parts.append("✅")
    if is_recommended:
        parts.append(badge_html)

    sel_html = f'<div class="select-cell">{"".join(parts)}</div>'
    c[5].markdown(sel_html, unsafe_allow_html=True)


# Enforce single-select & support deselect
if len(integrity_checked_keys) > 1:
    st.warning("Please select only one Integrity/Security focus. Keeping the first checked and unchecking the rest.")
    keep_key = integrity_checked_keys[0]
    reset_other_checkboxes(integrity_checked_keys, keep_key)

p2_integrity = selected_area if selected_area else (recommended_area if recommended_area else "— select —")
st.markdown('</div>', unsafe_allow_html=True)  # close section card

# --- Evaluation template, Reflection, Resources ---
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("2.4 Plan How to Evaluate Your Fix (Read-only template)")
st.table({
    "Evaluation Element": [
        "Goal / Outcome", "Metric to Measure", "Data Source / Method",
        "Who Collects Data", "Timeline / Feasibility", "Barriers", "Using Results"
    ],
    "Explanation": [
        "What improvement do you want to see?",
        "A quantitative or qualitative measure.",
        "How you’ll collect data.",
        "Roles responsible.",
        "When and how long to track.",
        "Challenges or limitations.",
        "How findings will guide improvement."
    ],
    "Example": [
        "“Reduce failed interface messages by 50%. ”",
        "% of successful message transfers; time to access image report.",
        "System logs, user survey, chart audit.",
        "IT analyst, imaging supervisor.",
        "Weekly over 3 months.",
        "Staff time, cost, training needs.",
        "Present at quality meeting to plan upgrades."
    ]
})
st.markdown('<hr class="sep">', unsafe_allow_html=True)

st.subheader("2.5 Report and Reflection ")
st.write(
    "Youp need to create a report using the template provided with your system analysis and evaluation plan. "
    "In your reflection (200 - 300 words), summarize what you learned about how interface design and data integrity affect interoperability. "
    "Discuss how your recommended fix aligns with CMS and ONC requirements and how your evaluation plan would measure its success."
    "Include your reflection in your report."
)

st.subheader("2.6 Key Resources")
st.markdown(
    "- CMS Interoperability Framework: https://www.cms.gov/health-technology-ecosystem/interoperability-framework\n"
    "- **ONC §170.315 Certification Criteria:** [ecfr.gov — §170.315](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-D/part-170/subpart-C/section-170.315)\n"
    "- ONC Interoperability Standards Advisory (ISA): https://www.healthit.gov/isa\n"
    "- AHRQ Health IT Evaluation Toolkit: https://digital.ahrq.gov/sites/default/files/docs/page/health-information-technology-evaluation-toolkit-2009-update.pdf\n"
    "- HIMSS Interoperability in Healthcare: https://gkc.himss.org/resources/interoperability-healthcare\n"
    "- Meditech Expanse Overview: https://ehr.meditech.com/ehr-solutions/meditech-expanse\n"
    "- Agfa Enterprise Imaging Platform: https://www.agfahealthcare.com/enterprise-imaging-platform/"
)
st.markdown('</div>', unsafe_allow_html=True)

# ------------------------
# Build PDF with current selections
# ------------------------
if plan_selected:
    plan_gap = plan_selected["Gap"]
    plan_iface = plan_selected["Suggested Interface Type"]
    plan_fix = plan_selected["Suggested Fix"]
    plan_ref = plan_selected["Reference"]
else:
    plan_gap = "— choose —"
    plan_iface = "— select —"
    plan_fix = "— choose —"
    plan_ref = "—"

include_all_options = st.checkbox("Include an appendix with ALL interface planning options in the PDF", value=False)

selections = {
    "plan_gap": plan_gap,
    "plan_iface": plan_iface,
    "plan_fix": plan_fix,
    "plan_ref": plan_ref,
    "p2_integrity": p2_integrity,
    "include_all_options": include_all_options,
}

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("📥 Export")
st.caption("The PDF includes the full template text and tables plus your current selections. (Placeholders will print as — if nothing is chosen.)")
if st.button("Generate PDF"):
    pdf_buf = build_pdf(selections)
    st.download_button(
        label="⬇️ Download Interoperability_Template_with_Selections.pdf",
        data=pdf_buf,
        file_name="Interoperability_Template_with_Selections.pdf",
        mime="application/pdf"
    )
st.markdown('</div>', unsafe_allow_html=True)
