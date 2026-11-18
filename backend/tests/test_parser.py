import os
import tempfile
import pytest
import pymupdf
import docx
from app.nlp.parser import parse_pdf, parse_docx, parse_txt, parse_document, clean_text


def test_clean_text():
    dirty = "Hello \u00a0 world!\n\n\n\n- Bullet item 1\n• Bullet item 2  "
    cleaned = clean_text(dirty)
    assert "Hello world!" in cleaned
    assert "- Bullet item 1" in cleaned
    assert "- Bullet item 2" in cleaned
    assert "\n\n\n" not in cleaned


def test_parse_pdf_single_page():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        doc = pymupdf.open()
        page = doc.new_page()
        sample_text = (
            "Alice Johnson\n"
            "Software Engineer - 4 years experience\n"
            "Skills: Python, FastAPI, PostgreSQL, Docker, AWS, Git.\n"
            "Education: B.Tech Computer Science, 2020."
        )
        page.insert_text((50, 72), sample_text)
        doc.save(tmp_path)
        doc.close()

        result = parse_pdf(tmp_path)
        assert result.file_type == "pdf"
        assert result.page_count == 1
        assert "Alice Johnson" in result.raw_text
        assert "FastAPI" in result.raw_text
        assert result.quality in ["good", "partial"]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_parse_pdf_multipage():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        doc = pymupdf.open()
        p1 = doc.new_page()
        p1.insert_text((50, 72), "Page 1: Bob Smith - Senior Backend Architect with extensive Java and Spring Boot expertise.")
        p2 = doc.new_page()
        p2.insert_text((50, 72), "Page 2: Education and Certifications - AWS Certified Solutions Architect, Kubernetes CKA.")
        doc.save(tmp_path)
        doc.close()

        result = parse_pdf(tmp_path)
        assert result.page_count == 2
        assert "Bob Smith" in result.raw_text
        assert "AWS Certified" in result.raw_text
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_parse_empty_pdf_detects_poor_quality():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        doc = pymupdf.open()
        doc.new_page()  # blank page
        doc.save(tmp_path)
        doc.close()

        result = parse_pdf(tmp_path)
        assert result.quality == "poor"
        assert len(result.warnings) > 0
        assert "scanned" in result.warnings[0].lower() or "50 characters" in result.warnings[0].lower()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_parse_docx_with_tables():
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        doc = docx.Document()
        doc.add_heading("Candidate Resume: Charlie Davis", level=1)
        doc.add_paragraph("Full Stack Developer with 3+ years experience building modern web apps.")
        doc.add_paragraph("Core competencies: React, TypeScript, Node.js, GraphQL, MongoDB.")

        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Degree"
        table.cell(0, 1).text = "Institution"
        table.cell(1, 0).text = "B.S. in Software Engineering"
        table.cell(1, 1).text = "State University"

        doc.save(tmp_path)

        result = parse_docx(tmp_path)
        assert result.file_type == "docx"
        assert "Charlie Davis" in result.raw_text
        assert "TypeScript" in result.raw_text
        assert "B.S. in Software Engineering" in result.raw_text
        assert result.quality in ["good", "partial"]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_parse_document_router():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(b"David Wilson\nDevOps Engineer with 5 years experience in Terraform and Kubernetes.")
        tmp_path = tmp.name

    try:
        result = parse_document(tmp_path)
        assert result.file_type == "txt"
        assert "David Wilson" in result.raw_text
        assert "Kubernetes" in result.raw_text
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_parse_unsupported_file():
    result = parse_document("invalid_file.xyz")
    assert result.file_type == "unsupported"
    assert result.quality == "poor"
    assert "Unsupported file format" in result.warnings[0]

