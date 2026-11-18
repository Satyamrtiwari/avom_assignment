import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.db.base import Base
from app.db.session import engine
# Import all models so Base.metadata knows about them
import app.models  # noqa: F401
from app.api import api_router
from app.nlp.skill_taxonomy import SkillMatcher
from app.nlp.extractor import ResumeExtractor
from app.nlp.jd_extractor import JDExtractor
from app.nlp.embedder import Embedder
from app.nlp.scorer import ResumeScorer
from app.services.match_service import MatchService
import spacy

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("resumeranker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler: initializes DB tables and NLP components on startup."""
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully.")

    logger.info(f"Loading spaCy model '{settings.SPACY_MODEL}'...")
    nlp = spacy.load(settings.SPACY_MODEL)

    taxonomy_path = os.path.join(settings.DATA_DIR, "skills.json")
    logger.info(f"Loading skill taxonomy from {taxonomy_path}...")
    skill_matcher = SkillMatcher(nlp, taxonomy_path)

    logger.info("Initializing Resume and JD Extractors...")
    resume_extractor = ResumeExtractor(nlp, skill_matcher)
    jd_extractor = JDExtractor(nlp, skill_matcher)

    logger.info(f"Loading SentenceTransformer model '{settings.SBERT_MODEL}'...")
    embedder = Embedder.get_instance(settings.SBERT_MODEL)

    logger.info("Initializing ResumeScorer and MatchService...")
    scorer = ResumeScorer(
        embedder=embedder,
        weights={
            "skill": settings.WEIGHT_SKILL,
            "semantic": settings.WEIGHT_SEMANTIC,
            "experience": settings.WEIGHT_EXPERIENCE,
            "qualification": settings.WEIGHT_QUALIFICATION,
        },
        skill_matcher=skill_matcher,
    )
    match_service = MatchService()

    # Store singletons in app state
    app.state.nlp = nlp
    app.state.skill_matcher = skill_matcher
    app.state.resume_extractor = resume_extractor
    app.state.jd_extractor = jd_extractor
    app.state.embedder = embedder
    app.state.scorer = scorer
    app.state.match_service = match_service

    logger.info("All NLP components, models, and matching engine loaded. ResumeRanker API listening.")
    yield
    logger.info("Shutting down ResumeRanker API...")
    await engine.dispose()
    logger.info("Database connection closed.")


from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="ResumeRanker API",
    description="AI-Based Resume Matching & Candidate Ranking System Backend",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


def custom_openapi():
    """
    Custom OpenAPI schema generator to ensure full compatibility with Swagger UI:
    1. Replaces OpenAPI 3.1 `contentMediaType` with `format: binary` on array file items
       so Swagger UI renders the native multi-file picker button.
    2. Removes pre-filled dummy "string" defaults on optional Form fields.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Walk schemas to patch array file inputs for Swagger UI
    for schema_name, schema_obj in openapi_schema.get("components", {}).get("schemas", {}).items():
        for prop_name, prop in schema_obj.get("properties", {}).items():
            if prop.get("type") == "array" and "items" in prop:
                items = prop["items"]
                if "contentMediaType" in items:
                    del items["contentMediaType"]
                    items["format"] = "binary"
            # Prevent Swagger UI from pre-populating dummy "string" in optional JD form fields
            if schema_name == "Body_create_job_description_api_v1_jd_post":
                if prop_name in ("title", "text"):
                    prop["example"] = ""
                    prop["default"] = None
            if schema_name == "Body_upload_resumes_api_v1_resumes_post":
                if prop_name == "jd_id":
                    prop["example"] = ""
                    prop["default"] = None

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"Validation error on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


# Include API Endpoints
app.include_router(api_router)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint to verify backend status."""
    return {
        "status": "ok",
        "app": "ResumeRanker API",
        "version": "0.1.0",
        "nlp_loaded": hasattr(app.state, "nlp") if hasattr(app, "state") else False,
        "embedder_loaded": hasattr(app.state, "embedder") if hasattr(app, "state") else False,
        "scorer_loaded": hasattr(app.state, "scorer") if hasattr(app, "state") else False,
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with navigation links."""
    return {
        "message": "Welcome to ResumeRanker API",
        "documentation": "/docs",
        "health": "/health",
        "api_prefix": "/api/v1",
    }
