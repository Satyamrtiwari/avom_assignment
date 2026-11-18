from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import (
    get_db,
    get_scorer,
    get_embedder,
    get_match_service,
    get_jd_extractor,
    get_resume_extractor,
)
from app.models.jd import JobDescription
from app.models.resume import Resume
from app.models.match_result import MatchResult
from app.schemas.match import (
    MatchRequest,
    MatchResponse,
    RankingResponse,
    CandidateRanking,
    CandidateDetailResponse,
)
from app.nlp.scorer import ResumeScorer
from app.nlp.embedder import Embedder
from app.nlp.jd_extractor import JDExtractor
from app.nlp.extractor import ResumeExtractor
from app.services.match_service import MatchService

router = APIRouter(tags=["Matching & Ranking"])


@router.post("/match", response_model=MatchResponse)
async def run_matching(
    request: MatchRequest,
    db: AsyncSession = Depends(get_db),
    scorer: ResumeScorer = Depends(get_scorer),
    embedder: Embedder = Depends(get_embedder),
    match_service: MatchService = Depends(get_match_service),
    jd_extractor: JDExtractor = Depends(get_jd_extractor),
    resume_extractor: ResumeExtractor = Depends(get_resume_extractor),
):
    """
    Trigger the multi-signal AI matching algorithm for a given Job Description.
    Calculates skill overlap, semantic similarity, experience delta, and qualifications.
    Stores and returns ranked candidate evaluations.
    """
    results = await match_service.run_matching(
        jd_id=request.jd_id,
        db=db,
        scorer=scorer,
        embedder=embedder,
        jd_extractor=jd_extractor,
        resume_extractor=resume_extractor,
    )

    return MatchResponse(
        jd_id=request.jd_id,
        status="completed",
        message=f"Successfully analyzed, scored, and ranked {len(results)} candidate resumes.",
        candidates_matched=len(results),
    )


@router.get("/results/{jd_id}", response_model=RankingResponse)
async def get_ranking_results(
    jd_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve ranked list of candidates for a specific Job Description.
    Sorted descending by overall match score (0-100).
    """
    # 1. Verify JD exists
    jd_stmt = select(JobDescription).where(JobDescription.id == jd_id)
    jd_res = await db.execute(jd_stmt)
    jd = jd_res.scalar_one_or_none()

    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job Description with ID '{jd_id}' not found.",
        )

    # 2. Fetch MatchResults joined with Resume
    match_stmt = (
        select(MatchResult, Resume)
        .join(Resume, MatchResult.resume_id == Resume.id)
        .where(MatchResult.jd_id == jd_id)
        .order_by(MatchResult.overall_score.desc())
    )
    match_res = await db.execute(match_stmt)
    rows = match_res.all()

    candidates: list[CandidateRanking] = []
    for rank, (mr, resume) in enumerate(rows, start=1):
        candidates.append(
            CandidateRanking(
                rank=rank,
                resume_id=mr.resume_id,
                candidate_name=resume.candidate_name,
                experience_years=resume.experience_years,
                overall_score=mr.overall_score,
                skill_score=mr.skill_score,
                semantic_score=mr.semantic_score,
                experience_score=mr.experience_score,
                qualification_score=mr.qualification_score,
                matched_skills=mr.matched_skills or [],
                missing_skills=mr.missing_skills or [],
                candidate_skills=resume.skills or [],
            )
        )

    return RankingResponse(
        jd_id=jd.id,
        jd_title=jd.title,
        total_candidates=len(candidates),
        candidates=candidates,
    )


@router.get("/results/{jd_id}/candidates/{resume_id}", response_model=CandidateDetailResponse)
async def get_candidate_match_detail(
    jd_id: str,
    resume_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve in-depth matching analysis for an individual candidate.
    Includes overall score, 4-signal breakdown, matched/missing skills,
    experience comparison verdict, and generated explanation.
    """
    match_stmt = (
        select(MatchResult, Resume)
        .join(Resume, MatchResult.resume_id == Resume.id)
        .where(MatchResult.jd_id == jd_id, MatchResult.resume_id == resume_id)
    )
    match_res = await db.execute(match_stmt)
    row = match_res.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match result not found for candidate '{resume_id}' under JD '{jd_id}'. Please run matching first.",
        )

    mr, resume = row
    audit = mr.meta_audit or {}

    return CandidateDetailResponse(
        resume_id=resume.id,
        jd_id=jd_id,
        candidate_name=resume.candidate_name,
        email=resume.email,
        phone=resume.phone,
        experience_years=resume.experience_years,
        total_experience_years=audit.get("total_experience_years", resume.experience_years),
        relevant_experience_years=audit.get("relevant_experience_years", resume.experience_years),
        experience_source=audit.get("experience_source", "dates"),
        is_experience_unknown=audit.get("is_experience_unknown", False),
        education=resume.education or [],
        overall_score=mr.overall_score,
        raw_cosine=mr.raw_cosine or audit.get("raw_cosine", 0.0),
        weights_used=audit.get("weights_used", {}),
        score_breakdown={
            "semantic_similarity": mr.semantic_score,
            "skill_match": mr.skill_score,
            "experience_match": mr.experience_score,
            "qualification_match": mr.qualification_score,
        },
        matched_skills=mr.matched_skills or [],
        missing_skills=mr.missing_skills or [],
        candidate_skills=resume.skills or [],
        matched_skills_detailed=audit.get("matched_skills_detailed", []),
        experience_comparison=mr.experience_comparison or {},
        explanation=mr.explanation or "",
        warnings=audit.get("warnings", []),
        meta_audit=audit,
        created_at=mr.created_at,
    )
