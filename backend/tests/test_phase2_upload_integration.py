import io
import pytest
from httpx import AsyncClient, ASGITransport
import pymupdf
import docx
from app.main import app
from app.db.base import Base
from app.db.session import engine


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


def generate_test_pdf_bytes(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def generate_test_docx_bytes(heading: str, paragraphs: list[str]) -> bytes:
    doc = docx.Document()
    doc.add_heading(heading, level=1)
    for p in paragraphs:
        doc.add_paragraph(p)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


@pytest.mark.asyncio
async def test_upload_jd_as_pdf():
    pdf_text = (
        "Role: Senior Java Developer\n"
        "Requirements:\n"
        "- 5+ years of experience with Core Java and Spring Boot\n"
        "- Microservices architecture, SQL, Docker, Kafka\n"
        "- B.Tech in Computer Science or equivalent"
    )
    pdf_bytes = generate_test_pdf_bytes(pdf_text)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = {
            "file": ("senior_java_developer_jd.pdf", pdf_bytes, "application/pdf"),
        }
        res = await ac.post("/api/v1/jd", data={"title": "Senior Java Developer"}, files=files)
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Senior Java Developer"
        assert "Core Java and Spring Boot" in data["raw_text"]
        assert "Microservices architecture" in data["raw_text"]


@pytest.mark.asyncio
async def test_batch_upload_mixed_resumes_pdf_and_docx():
    # 1. Create JD
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        jd_res = await ac.post(
            "/api/v1/jd",
            data={
                "title": "Cloud Architect",
                "text": "Requires 5+ years cloud infrastructure experience with AWS, Kubernetes, Terraform.",
            },
        )
        jd_id = jd_res.json()["id"]

        # 2. Prepare 1 PDF resume and 1 DOCX resume
        pdf_resume = generate_test_pdf_bytes(
            "Candidate One\nCloud Engineer with 4 years experience in AWS, Kubernetes, and Docker.\nEducation: B.Tech IT."
        )
        docx_resume = generate_test_docx_bytes(
            "Candidate Two",
            [
                "DevOps Consultant with 6 years experience.",
                "Specialized in Terraform, CI/CD, Ansible, and Python automation.",
                "Education: M.S. Software Engineering.",
            ],
        )

        files = [
            ("files", ("candidate_one.pdf", pdf_resume, "application/pdf")),
            ("files", ("candidate_two.docx", docx_resume, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ]

        # 3. Batch upload
        upload_res = await ac.post("/api/v1/resumes", data={"jd_id": jd_id}, files=files)
        assert upload_res.status_code == 201
        upload_data = upload_res.json()

        assert upload_data["total_received"] == 2
        assert upload_data["processed"] == 2
        assert upload_data["failed"] == 0

        # Verify raw_text was extracted and saved for both
        for r_status in upload_data["resumes"]:
            assert r_status["status"] == "success"
            resume_detail = await ac.get(f"/api/v1/resumes/{r_status['id']}")
            assert resume_detail.status_code == 200
            detail_data = resume_detail.json()
            assert detail_data["raw_text"] is not None
            assert len(detail_data["raw_text"]) > 30
            if "one.pdf" in r_status["filename"]:
                assert "Candidate One" in detail_data["raw_text"]
                assert "AWS, Kubernetes" in detail_data["raw_text"]
            elif "two.docx" in r_status["filename"]:
                assert "Candidate Two" in detail_data["raw_text"]
                assert "Terraform" in detail_data["raw_text"]

