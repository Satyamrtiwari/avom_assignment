import os
import glob
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.base import Base
from app.db.session import engine


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_unsupported_file_extension_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create JD first
        jd_res = await ac.post("/api/v1/jd", data={"title": "Test JD", "text": "Requirements: Python, SQL"})
        jd_id = jd_res.json()["id"]

        files = [("files", ("malicious.exe", b"MZbinarycontent", "application/octet-stream"))]
        res = await ac.post("/api/v1/resumes", data={"jd_id": jd_id}, files=files)
        assert res.status_code == 201
        data = res.json()
        assert data["failed"] == 1
        assert data["processed"] == 0
        assert "Unsupported file format" in data["resumes"][0]["warnings"][0]


@pytest.mark.asyncio
async def test_empty_or_too_short_jd_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/jd", data={"text": "Short"})
        assert res.status_code == 400
        assert "too short" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_match_non_existent_jd_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/match", json={"jd_id": "00000000-0000-0000-0000-000000000000"})
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_match_with_zero_resumes_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        jd_res = await ac.post("/api/v1/jd", data={"title": "Empty JD", "text": "Valid requirements: Java, Spring, 5 years."})
        jd_id = jd_res.json()["id"]

        res = await ac.post("/api/v1/match", json={"jd_id": jd_id})
        assert res.status_code == 400
        assert "No resumes have been uploaded" in res.json()["detail"]


@pytest.mark.asyncio
async def test_batch_upload_all_12_resumes_and_full_ranking():
    """
    Test uploading all 12 synthetic resumes in a single batch,
    running matching, and verifying the 12-candidate ranking dashboard.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Upload sample JD
        sample_jd_path = "sample_data/sample_jd.pdf" if os.path.exists("sample_data/sample_jd.pdf") else "../sample_data/sample_jd.pdf"
        with open(sample_jd_path, "rb") as f:
            jd_res = await ac.post("/api/v1/jd", files={"file": ("sample_jd.pdf", f.read(), "application/pdf")})
        assert jd_res.status_code == 201
        jd_id = jd_res.json()["id"]

        # 2. Gather all 12 resumes from sample_data/resumes/
        resumes_dir = "sample_data/resumes" if os.path.exists("sample_data/resumes") else "../sample_data/resumes"
        resume_files = sorted(glob.glob(f"{resumes_dir}/*.*"))
        assert len(resume_files) >= 10, f"Expected at least 10 sample resumes, found {len(resume_files)}"

        multipart_files = []
        file_handles = []
        for r_path in resume_files:
            fname = os.path.basename(r_path)
            mime = "application/pdf" if fname.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            fh = open(r_path, "rb")
            file_handles.append(fh)
            multipart_files.append(("files", (fname, fh.read(), mime)))

        for fh in file_handles:
            fh.close()

        # 3. Upload all 12 in one single batch
        upload_res = await ac.post("/api/v1/resumes", data={"jd_id": jd_id}, files=multipart_files)
        assert upload_res.status_code == 201
        upload_data = upload_res.json()

        assert upload_data["total_received"] >= 10
        assert upload_data["processed"] >= 10
        assert upload_data["failed"] == 0

        # 4. Trigger matching
        match_res = await ac.post("/api/v1/match", json={"jd_id": jd_id})
        assert match_res.status_code == 200
        match_data = match_res.json()
        assert match_data["status"] == "completed"
        assert match_data["candidates_matched"] >= 10

        # 5. Fetch ranking dashboard results
        rank_res = await ac.get(f"/api/v1/results/{jd_id}")
        assert rank_res.status_code == 200
        rank_data = rank_res.json()
        candidates = rank_data["candidates"]
        assert len(candidates) >= 10

        # Verify descending order of scores
        scores = [c["overall_score"] for c in candidates]
        assert scores == sorted(scores, reverse=True), "Candidates must be ranked strictly descending by overall_score"

        # Verify ranks are sequential 1..N
        for idx, c in enumerate(candidates, start=1):
            assert c["rank"] == idx

        # Strong candidate (Amit Sharma) should be at or near Rank #1
        top_candidates = [c["candidate_name"] for c in candidates[:3]]
        assert "Amit Sharma" in top_candidates or "Rohit Verma" in top_candidates

        # Weak candidate (Divya Mehta) should be at the bottom
        bottom_candidates = [c["candidate_name"] for c in candidates[-3:]]
        assert "Divya Mehta" in bottom_candidates or "Sanjay Rawat" in bottom_candidates or "Rahul Deshmukh" in bottom_candidates
