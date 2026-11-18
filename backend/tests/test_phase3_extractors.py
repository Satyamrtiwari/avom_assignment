import os
import pytest
import spacy
from httpx import AsyncClient, ASGITransport
from app.nlp.skill_taxonomy import SkillMatcher
from app.nlp.extractor import ResumeExtractor
from app.nlp.jd_extractor import JDExtractor
from app.main import app
from app.db.base import Base
from app.db.session import engine


@pytest.fixture(scope="module")
def nlp():
    return spacy.load("en_core_web_sm")


@pytest.fixture(scope="module")
def skill_matcher(nlp):
    taxonomy_path = os.path.join("backend", "data", "skills.json")
    if not os.path.exists(taxonomy_path):
        taxonomy_path = os.path.join("data", "skills.json")
    return SkillMatcher(nlp, taxonomy_path)


def test_skill_matcher_exact_and_aliases(skill_matcher):
    sample_text = (
        "We need a backend developer experienced with python, k8s, springboot, and postgres. "
        "Knowledge of reactjs, AWS, and REST APIs is required."
    )
    skills = skill_matcher.extract_skills(sample_text)

    # Check canonical mapping
    assert "Python" in skills
    assert "Kubernetes" in skills   # from alias 'k8s'
    assert "Spring Boot" in skills  # from alias 'springboot'
    assert "PostgreSQL" in skills   # from alias 'postgres'
    assert "React" in skills        # from alias 'reactjs'
    assert "AWS" in skills
    assert "REST APIs" in skills


def test_resume_extractor_profile(nlp, skill_matcher):
    extractor = ResumeExtractor(nlp, skill_matcher)
    resume_text = """
    Aarav Mehta
    aarav.mehta@example.com | +91 9876543210
    Bengaluru, Karnataka

    PROFESSIONAL SUMMARY
    Senior Software Engineer with 6 years of experience building scalable backend microservices.
    Proficient in Python, FastAPI, Docker, and PostgreSQL.

    WORK EXPERIENCE
    Lead Backend Engineer - CloudTech (2020 - Present)
    - Architected REST APIs using FastAPI and PostgreSQL.
    - Managed Docker containers and deployed on Kubernetes.

    EDUCATION
    B.Tech in Computer Science & Engineering - IIT Bombay (2014 - 2018)
    """
    data = extractor.extract(resume_text)

    assert data.candidate_name == "Aarav Mehta"
    assert data.email == "aarav.mehta@example.com"
    assert "9876543210" in data.phone
    assert data.experience_years == 6.0
    assert "Python" in data.skills
    assert "FastAPI" in data.skills
    assert "Docker" in data.skills
    assert "PostgreSQL" in data.skills
    assert any("Bachelor" in edu or "B.Tech" in edu for edu in data.education)


def test_jd_extractor_requirements(nlp, skill_matcher):
    extractor = JDExtractor(nlp, skill_matcher)
    jd_text = """
    Job Title: Senior Cloud Engineer
    Experience: 5+ years of experience

    Requirements:
    - 5+ years experience in AWS, Kubernetes, and Terraform.
    - Solid background in Python or Go.
    - Deep understanding of CI/CD pipelines and Docker.

    Nice to have:
    - Experience with Kafka and GraphQL.

    Qualifications:
    - Bachelor's degree in Computer Science or equivalent.

    Responsibilities:
    - Design and maintain production cloud infrastructure.
    - Automate infrastructure deployment using Terraform.
    """
    data = extractor.extract(jd_text)

    assert data.title == "Senior Cloud Engineer"
    assert data.experience_years == 5.0
    assert "AWS" in data.required_skills
    assert "Kubernetes" in data.required_skills
    assert "Terraform" in data.required_skills
    assert "Docker" in data.required_skills
    # Check nice to have
    assert "Kafka" in data.preferred_skills or "GraphQL" in data.preferred_skills
    assert len(data.responsibilities) >= 1
    assert any("Bachelor" in q for q in data.qualifications)


@pytest.mark.asyncio
async def test_api_extraction_integration():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create JD via text
        jd_payload = {
            "title": "Lead Java Architect",
            "text": (
                "Role: Lead Java Architect\n"
                "Requirements:\n"
                "- 8+ years experience in Java, Spring Boot, Microservices, and PostgreSQL.\n"
                "- Docker and Kubernetes.\n"
                "Qualifications:\n"
                "- B.Tech / M.Tech in CS."
            ),
        }
        jd_res = await ac.post("/api/v1/jd", data=jd_payload)
        assert jd_res.status_code == 201
        jd_data = jd_res.json()
        assert "Java" in jd_data["required_skills"]
        assert "Spring Boot" in jd_data["required_skills"]
        assert jd_data["experience_years"] == 8.0
        jd_id = jd_data["id"]

        # 2. Upload candidate resume
        resume_content = (
            "Vikram Singh\n"
            "Email: vikram.singh@example.com | Phone: +91 9988776655\n"
            "Summary: Java Developer with 7 years of experience in Spring Boot, SQL, and Docker.\n"
            "Education: B.Tech Computer Science."
        )
        files = [
            ("files", ("vikram_resume.txt", resume_content.encode("utf-8"), "text/plain")),
        ]
        res = await ac.post("/api/v1/resumes", data={"jd_id": jd_id}, files=files)
        assert res.status_code == 201
        res_data = res.json()
        resume_id = res_data["resumes"][0]["id"]

        # 3. Retrieve resume details and check extracted values
        detail_res = await ac.get(f"/api/v1/resumes/{resume_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["candidate_name"] == "Vikram Singh"
        assert detail["email"] == "vikram.singh@example.com"
        assert "9988776655" in detail["phone"]
        assert detail["experience_years"] == 7.0
        assert "Java" in detail["skills"]
        assert "Spring Boot" in detail["skills"]
        assert "Docker" in detail["skills"]


def test_fuzzy_skill_matching_false_positives(skill_matcher):
    """
    Requirement 7:
    Restrict fuzzy skill matching to terms of 5+ characters and never to ambiguous short names.
    Test for false positives:
    - JavaScript in resume must NOT match Java in JD.
    - Ambiguous short terms ('Go', 'C', 'R') in ordinary sentences must NOT falsely match.
    - Valid typographical variation on long term (e.g. 'Kubernets' -> 'Kubernetes') matches.
    """
    # 1. Candidate mentions JavaScript, but NOT Java
    js_text = "Frontend specialist skilled in JavaScript, TypeScript, CSS3, and React."
    res_java = skill_matcher.match_target_skills(["Java"], js_text)
    assert "Java" not in res_java["matched"], "JavaScript must NOT trigger false match for Java"
    assert "Java" in res_java["missing"]

    # 2. Candidate has ordinary English words matching short terms
    prose_text = "I like to go for running every morning. Received an A grade in school and participated in R&D projects."
    res_short = skill_matcher.match_target_skills(["Go", "C", "R"], prose_text)
    assert "Go" not in res_short["matched"]
    assert "C" not in res_short["matched"]
    assert "R" not in res_short["matched"]

    # 3. Legitimate fuzzy match on term >= 5 characters (e.g. 'Kubernets' typo for 'Kubernetes')
    typo_text = "Experienced with Docker containers and Kubernets cluster deployment."
    res_k8s = skill_matcher.match_target_skills(["Kubernetes"], typo_text)
    assert "Kubernetes" in res_k8s["matched"]
    assert res_k8s["evidence"]["Kubernetes"]["type"].startswith("fuzzy_")


def test_jd_lead_in_stripping_and_clean_extraction(nlp, skill_matcher):
    extractor = JDExtractor(nlp, skill_matcher)
    jd_text = """
    Job Title: Senior Backend Developer
    Experience: 4+ years

    Requirements:
    - Cloud experience on AWS and Docker containerization.
    - Deep knowledge of PostgreSQL database optimization.
    - Solid understanding of Kubernetes cluster architecture.
    - Familiarity with CI/CD pipelines.
    """
    data = extractor.extract(jd_text)
    # Lead-in phrases must be stripped, producing canonical or clean tokens
    assert "AWS" in data.required_skills
    assert "Docker" in data.required_skills
    assert "PostgreSQL" in data.required_skills
    assert "Kubernetes" in data.required_skills
    assert not any("Cloud experience on" in s for s in data.required_skills)
    assert not any("Deep knowledge of" in s for s in data.required_skills)


def test_marketing_jd_open_vocabulary_skills(nlp, skill_matcher):
    extractor = JDExtractor(nlp, skill_matcher)
    jd_text = """
    Job Title: Digital Marketing Executive
    Experience: 2+ years

    Requirements:
    - Proven track record with SEO and SEM strategies.
    - Hands-on experience with Google Ads and Meta Ads management.
    - Expertise in Google Analytics, Content Marketing, and Email Marketing.
    - Knowledge of HubSpot and Social Media Marketing.
    """
    data = extractor.extract(jd_text)
    # Open-vocabulary skill extraction must extract non-software skills
    skills_lower = [s.lower() for s in data.required_skills]
    assert any("seo" in s for s in skills_lower)
    assert any("google ads" in s for s in skills_lower)
    assert any("meta ads" in s or "facebook" in s for s in skills_lower)
    assert any("google analytics" in s for s in skills_lower)
    assert any("email marketing" in s or "content marketing" in s for s in skills_lower)


def test_or_groups_sentence_boundary_and_multitoken(nlp, skill_matcher):
    extractor = JDExtractor(nlp, skill_matcher)
    jd_text = """
    Job Title: Full Stack Developer
    Requirements:
    - Must be proficient in Python or Go for backend microservices.
    - Experience in Jest or React Testing Library for frontend quality.
    - Experience with AWS, GCP or Azure cloud environments.
    Another sentence mentions Docker.
    """
    data = extractor.extract(jd_text)
    groups = data.or_groups
    assert len(groups) >= 2
    # Verify 'Python or Go' group
    python_go = [g for g in groups if "Python" in g or "Go" in g]
    assert len(python_go) > 0
    # Verify 'Jest or React Testing Library' preserves multi-token
    jest_rtl = [g for g in groups if any("React Testing Library" in opt for opt in g)]
    assert len(jest_rtl) > 0
    assert any("Jest" in opt for opt in jest_rtl[0])



