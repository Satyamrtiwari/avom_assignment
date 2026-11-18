import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.base import Base
from app.db.session import engine


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield



@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ResumeRanker API" in data["app"]


@pytest.mark.asyncio
async def test_create_and_get_jd():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create JD
        jd_payload = {
            "title": "Senior Python Backend Engineer",
            "text": "We are seeking a Senior Python Engineer with 5+ years of experience in FastAPI, PostgreSQL, Docker, and REST APIs.",
        }
        res = await ac.post("/api/v1/jd", data=jd_payload)
        assert res.status_code == 201
        created = res.json()
        assert created["title"] == "Senior Python Backend Engineer"
        jd_id = created["id"]

        # Get JD
        get_res = await ac.get(f"/api/v1/jd/{jd_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == jd_id

        # List JDs
        list_res = await ac.get("/api/v1/jd")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1


@pytest.mark.asyncio
async def test_upload_resumes_and_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create a JD first
        jd_res = await ac.post(
            "/api/v1/jd",
            data={
                "title": "Full Stack Dev",
                "text": "Requires React, FastAPI, SQL, 3 years experience.",
            },
        )
        jd_id = jd_res.json()["id"]

        # 2. Upload test text resumes
        files = [
            ("files", ("candidate_alice.txt", b"Alice Developer: 4 years Python, React, PostgreSQL", "text/plain")),
            ("files", ("candidate_bob.txt", b"Bob Engineer: 2 years Java, Spring Boot, MySQL", "text/plain")),
        ]
        upload_res = await ac.post("/api/v1/resumes", data={"jd_id": jd_id}, files=files)
        assert upload_res.status_code == 201
        upload_data = upload_res.json()
        assert upload_data["processed"] == 2
        assert upload_data["failed"] == 0
        assert len(upload_data["resumes"]) == 2

        # 3. Retrieve single resume
        resume_id = upload_data["resumes"][0]["id"]
        detail_res = await ac.get(f"/api/v1/resumes/{resume_id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["filename"] == "candidate_alice.txt"

        # 4. Trigger match stub
        match_res = await ac.post("/api/v1/match", json={"jd_id": jd_id})
        assert match_res.status_code == 200
        assert match_res.json()["candidates_matched"] == 2
