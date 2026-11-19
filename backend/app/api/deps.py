import os
from collections.abc import AsyncGenerator
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_factory
from app.config import settings

_lazy_nlp = None
_lazy_skill_matcher = None
_lazy_resume_extractor = None
_lazy_jd_extractor = None
_lazy_embedder = None
_lazy_scorer = None
_lazy_match_service = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _get_shared_nlp_components():
    global _lazy_nlp, _lazy_skill_matcher
    if _lazy_nlp is None:
        import spacy
        _lazy_nlp = spacy.load(
            settings.SPACY_MODEL,
            disable=["parser", "tagger", "lemmatizer", "attribute_ruler"],
        )
    if _lazy_skill_matcher is None:
        from app.nlp.skill_taxonomy import SkillMatcher
        taxonomy_path = os.path.join(settings.DATA_DIR, "skills.json")
        _lazy_skill_matcher = SkillMatcher(_lazy_nlp, taxonomy_path)
    return _lazy_nlp, _lazy_skill_matcher


def get_skill_matcher(request: Request):
    """Retrieve SkillMatcher singleton from app state or lazy initialize."""
    if hasattr(request.app, "state") and getattr(request.app.state, "skill_matcher", None):
        return request.app.state.skill_matcher
    _, matcher = _get_shared_nlp_components()
    return matcher


def get_resume_extractor(request: Request):
    """
    Retrieve ResumeExtractor singleton from app state,
    falling back to lazy initialization if app lifespan wasn't triggered (e.g. test clients).
    """
    global _lazy_resume_extractor
    if hasattr(request.app, "state") and getattr(request.app.state, "resume_extractor", None):
        return request.app.state.resume_extractor

    if _lazy_resume_extractor is None:
        from app.nlp.extractor import ResumeExtractor
        nlp, matcher = _get_shared_nlp_components()
        _lazy_resume_extractor = ResumeExtractor(nlp, matcher)
    return _lazy_resume_extractor


def get_jd_extractor(request: Request):
    """
    Retrieve JDExtractor singleton from app state,
    falling back to lazy initialization if app lifespan wasn't triggered.
    """
    global _lazy_jd_extractor
    if hasattr(request.app, "state") and getattr(request.app.state, "jd_extractor", None):
        return request.app.state.jd_extractor

    if _lazy_jd_extractor is None:
        from app.nlp.jd_extractor import JDExtractor
        nlp, matcher = _get_shared_nlp_components()
        _lazy_jd_extractor = JDExtractor(nlp, matcher)
    return _lazy_jd_extractor


def get_embedder(request: Request):
    """
    Retrieve Embedder singleton from app state,
    falling back to lazy initialization if app lifespan wasn't triggered.
    """
    global _lazy_embedder
    if hasattr(request.app, "state") and getattr(request.app.state, "embedder", None):
        return request.app.state.embedder

    if _lazy_embedder is None:
        from app.nlp.embedder import Embedder
        _lazy_embedder = Embedder.get_instance(settings.SBERT_MODEL)
    return _lazy_embedder


def get_scorer(request: Request):
    """
    Retrieve ResumeScorer singleton from app state,
    falling back to lazy initialization if app lifespan wasn't triggered.
    """
    global _lazy_scorer
    if hasattr(request.app, "state") and getattr(request.app.state, "scorer", None):
        return request.app.state.scorer

    if _lazy_scorer is None:
        from app.nlp.scorer import ResumeScorer
        embedder = get_embedder(request)
        _lazy_scorer = ResumeScorer(
            embedder=embedder,
            weights={
                "skill": settings.WEIGHT_SKILL,
                "semantic": settings.WEIGHT_SEMANTIC,
                "experience": settings.WEIGHT_EXPERIENCE,
                "qualification": settings.WEIGHT_QUALIFICATION,
            },
            skill_matcher=get_skill_matcher(request),
        )
    return _lazy_scorer


def get_match_service(request: Request):
    """Retrieve MatchService instance."""
    global _lazy_match_service
    if _lazy_match_service is None:
        from app.services.match_service import MatchService
        _lazy_match_service = MatchService()
    return _lazy_match_service
