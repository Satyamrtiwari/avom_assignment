import pytest
from httpx import AsyncClient, ASGITransport
from app.nlp.embedder import Embedder
from app.nlp.scorer import ResumeScorer
from app.main import app
from app.db.base import Base
from app.db.session import engine


@pytest.fixture(scope="module")
def scorer():
    embedder = Embedder.get_instance("all-MiniLM-L6-v2")
    return ResumeScorer(
        embedder=embedder,
        weights={"skill": 0.35, "semantic": 0.30, "experience": 0.20, "qualification": 0.15},
    )


def test_skill_overlap_computation(scorer):
    jd_skills = ["Java", "Spring Boot", "PostgreSQL", "Docker", "Kubernetes"]

    # 1. Full overlap (5/5)
    cand_1_skills = ["Java", "Spring Boot", "PostgreSQL", "Docker", "Kubernetes", "Git"]
    res1 = scorer._compute_skill_score(jd_skills, cand_1_skills)
    assert res1["score"] == 100.0
    assert len(res1["matched"]) == 5
    assert len(res1["missing"]) == 0

    # 2. Partial overlap (3/5)
    cand_2_skills = ["Java", "Spring Boot", "PostgreSQL", "React"]
    res2 = scorer._compute_skill_score(jd_skills, cand_2_skills)
    assert 50.0 <= res2["score"] <= 75.0
    assert "Docker" in res2["missing"]
    assert "Kubernetes" in res2["missing"]

    # 3. Zero overlap (0/5)
    cand_3_skills = ["Ruby", "Rails"]
    res3 = scorer._compute_skill_score(jd_skills, cand_3_skills)
    assert res3["score"] == 0.0
    assert len(res3["missing"]) == 5


def test_experience_scoring_curve(scorer):
    # Meets or exceeds requirement (5 yrs actual vs 4 yrs req)
    exp1 = scorer._compute_experience_score(4.0, 5.0, "4+ years")
    assert exp1["score"] == 100.0
    assert exp1["comparison"]["meets_requirement"] is True

    # Slightly below requirement (3 yrs actual vs 4 yrs req, ratio=0.75)
    exp2 = scorer._compute_experience_score(4.0, 3.0, "4+ years")
    assert 70.0 <= exp2["score"] < 100.0
    assert exp2["comparison"]["meets_requirement"] is False

    # Below requirement (1 yr actual vs 5 yrs req, ratio=0.2)
    exp3 = scorer._compute_experience_score(5.0, 1.0, "5 years")
    assert exp3["score"] < 40.0
    assert exp3["comparison"]["meets_requirement"] is False


def test_full_scoring_and_explanation(scorer):
    breakdown = scorer.score(
        candidate_name="Rohit Verma",
        jd_skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
        resume_skills=["Python", "FastAPI", "PostgreSQL"],
        jd_embedding=[0.1] * 384,
        resume_embedding=[0.1] * 384,
        jd_exp_years=4.0,
        resume_exp_years=5.0,
        jd_exp_str="4+ years",
        jd_qualifications=["B.Tech in Computer Science"],
        resume_education=["B.Tech Computer Science - NIT Trichy"],
    )

    assert 70.0 <= breakdown.skill_score <= 85.0  # 3 of 4 skills with IDF weights
    assert breakdown.experience_score == 100.0  # 5 >= 4
    assert breakdown.qualification_score >= 90.0
    assert 70.0 <= breakdown.overall_score <= 100.0
    assert "Rohit Verma" in breakdown.explanation
    assert "Matched 3 of 4" in breakdown.explanation
    assert "Docker" in breakdown.missing_skills


@pytest.mark.asyncio
async def test_end_to_end_matching_api():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create JD
        jd_res = await ac.post(
            "/api/v1/jd",
            data={
                "title": "Backend Architect (Java)",
                "text": (
                    "Job Title: Backend Architect\n"
                    "Requirements:\n"
                    "- 5+ years of experience with Java, Spring Boot, PostgreSQL, Docker, Kubernetes\n"
                    "Qualifications:\n"
                    "- Bachelor's degree in Computer Science"
                ),
            },
        )
        assert jd_res.status_code == 201
        jd_id = jd_res.json()["id"]

        # 2. Upload 3 resumes: Strong, Moderate, Weak
        r_strong = (
            "Ananya Sen\n"
            "Email: ananya@example.com | Phone: +91 9876543211\n"
            "Job Title: Backend Architect\n"
            "Summary: Senior Backend Architect with 6 years experience in Java, Spring Boot, PostgreSQL, Docker, and Kubernetes.\n"
            "Led architecture and engineering for large-scale microservices, distributed systems, and cloud infrastructure.\n"
            "Education: Bachelor's degree in Computer Science."
        )
        r_moderate = (
            "Karan Malhotra\n"
            "Email: karan@example.com | Phone: +91 9876543212\n"
            "Java Developer with 3 years experience in Java, Spring Boot, MySQL.\n"
            "Education: B.Tech Information Technology."
        )
        r_weak = (
            "Sunita Rao\n"
            "Email: sunita@example.com | Phone: +91 9876543213\n"
            "Graphic Designer with 2 years experience in Photoshop and Illustrator.\n"
            "Education: Bachelor of Fine Arts."
        )

        files = [
            ("files", ("ananya.txt", r_strong.encode("utf-8"), "text/plain")),
            ("files", ("karan.txt", r_moderate.encode("utf-8"), "text/plain")),
            ("files", ("sunita.txt", r_weak.encode("utf-8"), "text/plain")),
        ]
        upload_res = await ac.post("/api/v1/resumes", data={"jd_id": jd_id}, files=files)
        assert upload_res.status_code == 201
        assert upload_res.json()["processed"] == 3

        # 3. Trigger matching
        match_res = await ac.post("/api/v1/match", json={"jd_id": jd_id})
        assert match_res.status_code == 200
        match_data = match_res.json()
        assert match_data["status"] == "completed"
        assert match_data["candidates_matched"] == 3

        # 4. Fetch ranking dashboard results
        rank_res = await ac.get(f"/api/v1/results/{jd_id}")
        assert rank_res.status_code == 200
        rank_data = rank_res.json()
        assert rank_data["total_candidates"] == 3

        candidates = rank_data["candidates"]
        # Verify ranking order: Strong (Ananya) > Moderate (Karan) > Weak (Sunita)
        assert candidates[0]["candidate_name"] == "Ananya Sen"
        assert candidates[0]["rank"] == 1
        assert candidates[0]["overall_score"] > candidates[1]["overall_score"]

        assert candidates[1]["candidate_name"] == "Karan Malhotra"
        assert candidates[1]["rank"] == 2
        assert candidates[1]["overall_score"] > candidates[2]["overall_score"]

        assert candidates[2]["candidate_name"] == "Sunita Rao"
        assert candidates[2]["rank"] == 3

        # 5. Fetch detailed analysis for the top candidate
        top_cand_id = candidates[0]["resume_id"]
        detail_res = await ac.get(f"/api/v1/results/{jd_id}/candidates/{top_cand_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["candidate_name"] == "Ananya Sen"
        assert detail["overall_score"] >= 80.0
        assert "Java" in detail["matched_skills"]
        assert "Spring Boot" in detail["matched_skills"]
        assert detail["score_breakdown"]["skill_match"] == 100.0
        assert detail["experience_comparison"]["meets_requirement"] is True
        assert len(detail["explanation"]) > 50


def test_relevance_factor_strong_candidate_uncatalogued_skills(scorer):
    """
    Test requirement 5:
    A strong candidate who has strong semantic alignment, relevant experience,
    and matching degrees, but whose niche/uncatalogued tools were not extracted
    as exact catalog taxonomy matches, must NOT be crushed (overall score remains >= 60.0).
    """
    # Simulate embedding similarity: raw cosine ~0.76 (strong domain fit)
    # Calibrated semantic score will be high (~75%)
    # Even if they matched only 1 of 3 required skills because others are uncatalogued
    breakdown = scorer.score(
        candidate_name="Elena Rostova",
        jd_skills=["Python", "Triton Inference Server", "vLLM Engine"],
        resume_skills=["Python"],  # Triton and vLLM uncatalogued in basic taxonomy
        jd_embedding=[0.15] * 384,
        resume_embedding=[0.15] * 384,  # perfect mock cosine = 1.0 (semantic score = 100)
        jd_exp_years=4.0,
        resume_exp_years=6.0,
        jd_exp_str="4+ years",
        jd_qualifications=["Master's degree in Computer Science or Data Science"],
        resume_education=["Master of Science in Computer Science - CMU"],
    )

    # Candidate has strong qual, exp, semantic, and partial skill match
    # Continuous relevance factor must modulate smoothly without crushing
    assert breakdown.overall_score >= 60.0, f"Expected overall score >= 60.0, got {breakdown.overall_score}"
    assert breakdown.raw_cosine == 1.0
    assert breakdown.qualification_score >= 85.0
    assert breakdown.experience_score >= 45.0
    assert "Python" in breakdown.matched_skills
    assert not any("capped at 10%" in w for w in breakdown.warnings)


def test_primary_skill_weighting_and_damping(scorer):
    """
    Test requirement 3.1:
    When a candidate matches 0 primary skills for a role (e.g. Java JD where Java is primary),
    the primary zero-damping multiplier (0.20) is applied, heavily reducing overall score.
    Conversely, candidate matching primary skills receives full credit.
    """
    # Candidate A: matches Java (primary) and Spring Boot
    cand_a = scorer.score(
        candidate_name="Java Pro",
        jd_skills=["Java", "Spring Boot", "Git", "Docker"],
        resume_skills=["Java", "Spring Boot", "Git"],
        jd_embedding=[0.2] * 384,
        resume_embedding=[0.2] * 384,
        jd_exp_years=3.0,
        resume_exp_years=4.0,
        jd_exp_str="3+ years",
        jd_qualifications=["B.Tech Computer Science"],
        resume_education=["B.Tech Computer Science"],
        primary_skills=["Java"],
    )

    # Candidate B: off-domain (e.g. Python backend dev), matches generic Git/Docker but 0 Java
    # Off-domain candidate has distinct/low-similarity semantic embedding
    cand_b = scorer.score(
        candidate_name="Python Dev",
        jd_skills=["Java", "Spring Boot", "Git", "Docker"],
        resume_skills=["Python", "Git", "Docker"],
        jd_embedding=[0.1] * 384,
        resume_embedding=[-0.1] * 384,
        jd_exp_years=3.0,
        resume_exp_years=4.0,
        jd_exp_str="3+ years",
        jd_qualifications=["B.Tech Computer Science"],
        resume_education=["B.Tech Computer Science"],
        primary_skills=["Java"],
    )

    assert cand_a.overall_score > 75.0
    # Candidate B has 0 primary skills -> score must be damped heavily (e.g. <= 25.0)
    assert cand_b.overall_score <= 25.0, f"Expected off-domain candidate to be <= 25.0, got {cand_b.overall_score}"
    assert any("zero primary skills" in w.lower() or "primary role skills" in w.lower() for w in cand_b.warnings)


def test_in_progress_degree_penalty(scorer):
    """
    Test requirement 3.7:
    In-progress degree receives configurable penalty (e.g. 12 pts lower)
    compared to fully completed degree.
    """
    comp = scorer._compute_qualification_score(
        jd_qualifications=["B.Tech in Computer Science"],
        resume_education=["Bachelor of Technology in Computer Science - 2022"],
        degree_details=[{"degree": "B.Tech", "field": "Computer Science", "level": 2, "is_completed": True}],
    )
    in_prog = scorer._compute_qualification_score(
        jd_qualifications=["B.Tech in Computer Science"],
        resume_education=["B.Tech Computer Science (Expected 2026)"],
        degree_details=[{"degree": "B.Tech", "field": "Computer Science", "level": 2, "is_completed": False}],
    )

    assert comp["score"] == 100.0
    assert in_prog["score"] <= 90.0
    assert in_prog["audit"]["is_in_progress"] is True
    assert in_prog["score"] < comp["score"]


def test_qualification_scoring_btech_it_and_unrelated_field(scorer):
    """
    Test long-term credential scoring:
    - Candidate with B.Tech in Information Technology receives 100.0% qualification
      against a JD requiring Bachelor's/Master's in CS/IT/related field.
    - Credential score is independent of technical skill overlap (not multiplied by relevance factor).
    - Unrelated degrees (e.g. Fine Arts for CS role) receive transparent partial tier score (40.0%).
    - Business degrees (e.g. BBA) correctly match Business/Marketing roles via cluster alignment.
    """
    jd_stem = ["Bachelor's or Master's degree in Computer Science, Information Technology, or related field."]

    # 1. B.Tech in IT (Ananya Sharma case)
    btech_it = scorer._compute_qualification_score(
        jd_qualifications=jd_stem,
        resume_education=["Bachelor of Technology in Information Technology"],
        degree_details=[{"raw": "Bachelor of Technology in Information Technology", "degree": "bachelor", "level": 2, "graduation_year": 2023, "is_completed": True}],
        relevance_factor=0.71,  # Lower skill overlap must NOT degrade qualification score
    )
    assert btech_it["score"] == 100.0, f"Expected 100.0, got {btech_it['score']}"
    assert btech_it["audit"]["field_matched"] is True
    assert btech_it["audit"]["candidate_level"] >= btech_it["audit"]["jd_required_level"]

    # 2. B.Tech in CS (Rohit Verma case)
    btech_cs = scorer._compute_qualification_score(
        jd_qualifications=jd_stem,
        resume_education=["Bachelor of Technology in Computer Science"],
        degree_details=[{"raw": "Bachelor of Technology in Computer Science", "degree": "bachelor", "level": 2, "graduation_year": 2020, "is_completed": True}],
        relevance_factor=1.0,
    )
    assert btech_cs["score"] == 100.0
    assert btech_cs["audit"]["field_matched"] is True

    # 3. Off-domain candidate with B.Tech in CS (relevance factor 0.15)
    btech_offdomain = scorer._compute_qualification_score(
        jd_qualifications=jd_stem,
        resume_education=["B.Tech Computer Science"],
        degree_details=[{"degree": "bachelor", "level": 2, "is_completed": True}],
        relevance_factor=0.15,
    )
    assert btech_offdomain["score"] == 100.0

    # 4. Unrelated degree: Bachelor of Fine Arts for CS role
    bfa_cs = scorer._compute_qualification_score(
        jd_qualifications=jd_stem,
        resume_education=["Bachelor of Fine Arts"],
        degree_details=[{"degree": "bachelor", "level": 2, "is_completed": True}],
        relevance_factor=0.50,
    )
    assert bfa_cs["score"] == 40.0
    assert bfa_cs["audit"]["field_matched"] is False

    # 5. Non-STEM role: Marketing JD with BBA candidate (cluster match)
    jd_mkt = ["Bachelor's degree in Marketing, Business Administration, or Communications."]
    bba_mkt = scorer._compute_qualification_score(
        jd_qualifications=jd_mkt,
        resume_education=["Bachelor of Business Administration"],
        degree_details=[{"degree": "bba", "level": 2, "is_completed": True}],
    )
    assert bba_mkt["score"] == 100.0
    assert bba_mkt["audit"]["field_matched"] is True


