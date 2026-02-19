import streamlit as st
import tempfile
import os
import re
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
import docx2txt
import pdfplumber

# =========================
# SETTINGS
# =========================
FONT_NAME = "Times New Roman"
FONT_SIZE = 10

SUMMARY_HEADING = "Summary :"
TECH_HEADING = "Technical Skills :"
EDU_HEADING = "Education :"
EXP_HEADING = "Professional Experience :"

st.title("BRFv1.0 Strict Resume Formatter")

uploaded_file = st.file_uploader("Upload Resume (PDF or DOCX)", type=["pdf", "docx"])

# =========================
# TEXT EXTRACTION
# =========================
def extract_text(path):
    ext = os.path.splitext(path)[1].lower()
    text = ""

    if ext == ".pdf":
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    elif ext == ".docx":
        text = docx2txt.process(path)

    return text


# =========================
# REMOVE ORIGINAL BULLETS
# =========================
def remove_original_bullets(line):
    return re.sub(
        r'^\s*[\-\•\●\▪\◦\■\□\*\–\—\→\►\➤\➔\➢\✓\✔\·]+\s*',
        '',
        line
    )


# =========================
# BRF BULLET FORMAT
# • + TAB + TEXT
# =========================
def add_brf_bullet(doc, text):
    para = doc.add_paragraph()
    para.add_run("•\t" + text)
    return para


# =========================
# GLOBAL FORMATTING
# =========================
def apply_global_formatting(doc):
    style = doc.styles["Normal"]
    style.font.name = FONT_NAME
    style.font.size = Pt(FONT_SIZE)

    for p in doc.paragraphs:
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1


# =========================
# PROJECT HEADER
# =========================
def add_project_header(doc, header_line):
    para = doc.add_paragraph()

    duration_match = re.search(
        r'([A-Za-z]{3,9}\s\d{4}\s?[–-]\s?[A-Za-z]{3,9}\s\d{4}|Present|Current)',
        header_line
    )

    if duration_match:
        duration = duration_match.group(0)
        left_part = header_line.replace(duration, "").strip()

        para.add_run(left_part)
        para.add_run("\t")
        para.add_run(duration)

        para.paragraph_format.tab_stops.add_tab_stop(
            Pt(450),
            WD_TAB_ALIGNMENT.RIGHT
        )
    else:
        para.add_run(header_line)


# =========================
# SAFE PARSER
# =========================
def parse_sections(text):

    if not text or not text.strip():
        raise ValueError("Unable to extract text from resume.")

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    if len(lines) == 0:
        raise ValueError("Resume appears empty after extraction.")

    name = lines[0]

    name_parts = name.split()

    if len(name_parts) == 0:
        first = "Candidate"
        last = ""
    elif len(name_parts) == 1:
        first = name_parts[0]
        last = ""
    else:
        first = name_parts[0]
        last = " ".join(name_parts[1:])

    sections = {
        "summary": [],
        "technical": [],
        "education": [],
        "experience": []
    }

    current = None

    for line in lines[1:]:
        lower = line.lower()

        if "summary" in lower:
            current = "summary"
            continue
        elif "technical" in lower:
            current = "technical"
            continue
        elif "education" in lower:
            current = "education"
            continue
        elif "experience" in lower:
            current = "experience"
            continue

        if current:
            sections[current].append(line)

    return name, first, last, sections


# =========================
# CREATE DOCUMENT
# =========================
def create_document(name, first, last, sections):

    doc = Document()

    # Name centered
    p = doc.add_paragraph(name)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ================= SUMMARY =================
    p = doc.add_paragraph(SUMMARY_HEADING)
    p.runs[0].bold = True

    for line in sections["summary"]:
        cleaned = remove_original_bullets(line).strip()
        if cleaned:
            add_brf_bullet(doc, cleaned)

    doc.add_paragraph()

    # ================= TECHNICAL =================
    p = doc.add_paragraph(TECH_HEADING)
    p.runs[0].bold = True

    for line in sections["technical"]:
        cleaned = remove_original_bullets(line).strip()
        if cleaned:
            doc.add_paragraph(cleaned)

    # ================= EDUCATION =================
    p = doc.add_paragraph(EDU_HEADING)
    p.runs[0].bold = True

    for line in sections["education"]:
        cleaned = remove_original_bullets(line).strip()
        if cleaned:
            doc.add_paragraph(cleaned)

    doc.add_paragraph()

    # ================= EXPERIENCE =================
    p = doc.add_paragraph(EXP_HEADING)
    p.runs[0].bold = True

    exp_lines = [
        remove_original_bullets(l).strip()
        for l in sections["experience"]
        if l.strip()
    ]

    i = 0
    while i < len(exp_lines):

        add_project_header(doc, exp_lines[i])
        i += 1

        if i < len(exp_lines):
            doc.add_paragraph(exp_lines[i])
            i += 1

        while i < len(exp_lines) and not re.search(
            r'[A-Za-z]{3,9}\s\d{4}\s?[–-]\s?[A-Za-z]{3,9}\s\d{4}',
            exp_lines[i]
        ):
            add_brf_bullet(doc, exp_lines[i])
            i += 1

        doc.add_paragraph()

    apply_global_formatting(doc)

    filename = f"{first} {last}.docx"
    output_path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(output_path)

    return output_path


# =========================
# MAIN EXECUTION
# =========================
if uploaded_file:

    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        text = extract_text(tmp_path)

        name, first, last, sections = parse_sections(text)

        output_path = create_document(name, first, last, sections)

        with open(output_path, "rb") as f:
            st.download_button(
                label="Download BRFv1.0 Resume",
                data=f,
                file_name=f"{first} {last}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    except Exception as e:
        st.error(f"Error: {str(e)}")
