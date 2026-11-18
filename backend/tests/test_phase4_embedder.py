import pytest
from httpx import AsyncClient, ASGITransport
from app.nlp.embedder import Embedder
from app.main import app
from app.db.base import Base
from app.db.session import engine


@pytest.fixture(scope="module")
def embedder():
    return Embedder.get_instance("all-MiniLM-L6-v2")


def test_embed_dimension_and_type(embedder):
    text = "FastAPI is a modern, fast web framework for building APIs with Python."
    vec = embedder.embed(text)
    assert len(vec) == 384
    assert isinstance(vec[0], float)


def test_semantic_similarity_comparison(embedder):
    t_java_jd = "Looking for a Senior Java Developer with Spring Boot, PostgreSQL, and REST API experience."
    t_java_resume = "Backend software engineer with 5 years building scalable microservices in Java and Spring Boot."
    t_unrelated_resume = "Executive head chef specializing in French pastry, culinary arts, and kitchen sanitation."

    emb_jd = embedder.embed(t_java_jd)
    emb_java_res = embedder.embed(t_java_resume)
    emb_chef_res = embedder.embed(t_unrelated_resume)

    sim_related = embedder.similarity(emb_jd, emb_java_res)
    sim_unrelated = embedder.similarity(emb_jd, emb_chef_res)

    assert sim_related > 0.50, f"Expected strong relative similarity, got {sim_related}"
    assert sim_unrelated < 0.25, f"Expected low similarity for chef, got {sim_unrelated}"
    assert sim_related > sim_unrelated + 0.30, "Related text should score significantly higher than unrelated"


def test_chunking_long_document(embedder):
    paragraphs = [
        f"Paragraph {i}: Detailed engineering experience with distributed systems, databases, caching layers, and high-availability design."
        for i in range(15)
    ]
    long_doc = "\n\n".join(paragraphs)
    chunks = embedder._chunk_text(long_doc, max_words=60)
    assert len(chunks) > 1

    vec = embedder.embed(long_doc)
    assert len(vec) == 384


def test_batch_embedding(embedder):
    texts = [
        "Python data scientist",
        "React frontend developer",
        "DevOps engineer with Kubernetes",
        "Mobile developer with Flutter",
    ]
    vectors = embedder.embed_batch(texts)
    assert len(vectors) == 4
    for v in vectors:
        assert len(v) == 384


@pytest.mark.asyncio
async def test_api_embedding_integration():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create JD and check embedding is populated
        jd_res = await ac.post(
            "/api/v1/jd",
            data={
                "title": "AI Engineer",
                "text": "Seeking an AI Engineer with PyTorch, NLP, and sentence transformers experience.",
            },
        )
        assert jd_res.status_code == 201
        jd_data = jd_res.json()
        assert jd_data["has_embedding"] is True
        jd_id = jd_data["id"]

        # 2. Upload resume and check embedding is populated
        files = [
            ("files", ("ai_candidate.txt", b"Maya Patel: 3 years experience in NLP, PyTorch, and Deep Learning.", "text/plain")),
        ]
        upload_res = await ac.post("/api/v1/resumes", data={"jd_id": jd_id}, files=files)
        assert upload_res.status_code == 201
        res_id = upload_res.json()["resumes"][0]["id"]

        detail_res = await ac.get(f"/api/v1/resumes/{res_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["has_embedding"] is True
