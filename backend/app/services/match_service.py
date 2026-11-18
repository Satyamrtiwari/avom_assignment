import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException, status
from app.models.jd import JobDescription
from app.models.resume import Resume
from app.models.match_result import MatchResult
from app.nlp.scorer import ResumeScorer
from app.nlp.embedder import Embedder

logger = logging.getLogger("resumeranker.match_service")


class MatchService:
    """
    Service layer orchestrating the end-to-end matching pipeline:
    - Verifies JD and candidate resumes exist
    - Ensures cached embeddings are up to date
    - Executes multi-signal scoring per candidate
    - Persists MatchResult records into the database
    - Returns ranked candidate list
    """

    async def run_matching(
        self,
        jd_id: str,
        db: AsyncSession,
        scorer: ResumeScorer,
        embedder: Embedder,
        jd_extractor: Any = None,
        resume_extractor: Any = None,
    ) -> list[MatchResult]:
        """Execute matching for all resumes uploaded for a specific JD."""
        # 1. Fetch Job Description
        jd_res = await db.execute(select(JobDescription).where(JobDescription.id == jd_id))
        jd = jd_res.scalar_one_or_none()

        if not jd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job Description with ID '{jd_id}' not found.",
            )

        # 2. Extract advanced JD criteria if jd_extractor is present
        primary_skills = []
        or_groups = []
        responsibilities_skills = []
        if jd_extractor and jd.raw_text:
            jd_data = jd_extractor.extract(jd.raw_text)
            primary_skills = jd_data.primary_skills
            or_groups = jd_data.or_groups
            responsibilities_skills = jd_data.responsibilities_skills

        # 3. Ensure JD has an embedding
        if not jd.embedding and jd.raw_text:
            logger.info(f"Generating missing embedding for JD '{jd.id}'...")
            jd.embedding = embedder.embed(jd.raw_text)
            db.add(jd)
            await db.flush()

        # 4. Fetch Candidate Resumes
        res_stmt = select(Resume).where(Resume.jd_id == jd_id).order_by(Resume.created_at.asc())
        res_result = await db.execute(res_stmt)
        resumes = res_result.scalars().all()

        if not resumes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No resumes have been uploaded for Job Description '{jd_id}'. Please upload resumes first.",
            )

        # 5. Batch compute any missing resume embeddings
        resumes_needing_emb = [r for r in resumes if not r.embedding and r.raw_text]
        if resumes_needing_emb:
            logger.info(f"Generating missing embeddings for {len(resumes_needing_emb)} resumes in batch...")
            texts = [r.raw_text for r in resumes_needing_emb]
            vectors = embedder.embed_batch(texts)
            for r, vec in zip(resumes_needing_emb, vectors):
                r.embedding = vec
                db.add(r)
            await db.flush()

        # 6. Clear previous match results for this JD to allow re-runs
        await db.execute(delete(MatchResult).where(MatchResult.jd_id == jd_id))

        # 7. Score each candidate resume
        created_results: list[MatchResult] = []

        for resume in resumes:
            roles = None
            degree_details = None
            experience_source = getattr(resume, "experience_source", "dates")
            is_experience_unknown = getattr(resume, "is_experience_unknown", False)
            warnings = []

            if resume_extractor and resume.raw_text:
                res_data = resume_extractor.extract(resume.raw_text)
                roles = res_data.role_blocks
                degree_details = res_data.degree_details
                experience_source = res_data.experience_source
                is_experience_unknown = res_data.is_experience_unknown
                warnings = res_data.warnings

            breakdown = scorer.score(
                candidate_name=resume.candidate_name,
                jd_skills=jd.required_skills or [],
                preferred_skills=jd.preferred_skills or [],
                primary_skills=primary_skills,
                responsibilities_skills=responsibilities_skills,
                or_groups=or_groups,
                resume_skills=resume.skills or [],
                jd_embedding=jd.embedding,
                resume_embedding=resume.embedding,
                jd_exp_years=jd.experience_years,
                resume_exp_years=resume.experience_years,
                jd_exp_str=jd.experience_required,
                jd_qualifications=jd.qualifications or [],
                resume_education=resume.education or [],
                roles=roles,
                degree_details=degree_details,
                jd_text=jd.raw_text,
                resume_text=resume.raw_text,
                experience_source=experience_source,
                is_experience_unknown=is_experience_unknown,
                warnings=warnings,
            )

            mr = MatchResult(
                jd_id=jd.id,
                resume_id=resume.id,
                overall_score=breakdown.overall_score,
                semantic_score=breakdown.semantic_score,
                skill_score=breakdown.skill_score,
                experience_score=breakdown.experience_score,
                qualification_score=breakdown.qualification_score,
                raw_cosine=breakdown.raw_cosine,
                matched_skills=breakdown.matched_skills,
                missing_skills=breakdown.missing_skills,
                experience_comparison=breakdown.experience_comparison,
                meta_audit={
                    "weights_used": breakdown.weights_used,
                    "raw_cosine": breakdown.raw_cosine,
                    "experience_source": breakdown.experience_source,
                    "is_experience_unknown": breakdown.is_experience_unknown,
                    "total_experience_years": breakdown.total_experience_years,
                    "relevant_experience_years": breakdown.relevant_experience_years,
                    "matched_skills_detailed": breakdown.matched_skills_detailed,
                    "qualification_audit": breakdown.qualification_audit,
                    "warnings": breakdown.warnings,
                },
                explanation=breakdown.explanation,
            )
            db.add(mr)
            created_results.append(mr)

        await db.commit()

        # Sort descending by overall score
        created_results.sort(key=lambda x: x.overall_score, reverse=True)
        logger.info(f"Successfully matched and ranked {len(created_results)} candidates for JD '{jd.id}'.")
        return created_results

