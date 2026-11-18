import json
import os
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, get_skill_matcher
from app.models.jd import JobDescription
from app.nlp.skill_taxonomy import SkillMatcher
from app.config import settings

router = APIRouter(prefix="/skills", tags=["Skills & Taxonomy"])


@router.get("/unknown")
async def get_unknown_skills(
    db: AsyncSession = Depends(get_db),
    skill_matcher: SkillMatcher = Depends(get_skill_matcher),
):
    """
    Review uncatalogued technical terms extracted from stored Job Descriptions.
    Enables administrators to inspect newly discovered technologies and add them to taxonomy.
    """
    stmt = select(JobDescription)
    res = await db.execute(stmt)
    jds = res.scalars().all()

    discovered_terms = set()
    for jd in jds:
        # Check raw text requirements against canonical taxonomy
        if jd.required_skills:
            for s in jd.required_skills:
                if s.lower() not in skill_matcher.canonical_map:
                    discovered_terms.add(s)
        if jd.preferred_skills:
            for s in jd.preferred_skills:
                if s.lower() not in skill_matcher.canonical_map:
                    discovered_terms.add(s)

    return {
        "total_uncatalogued": len(discovered_terms),
        "uncatalogued_skills": sorted(list(discovered_terms)),
        "taxonomy_size": len(skill_matcher.skill_categories),
        "action": "Add approved terms to backend/data/skills.json and rebuild IDF snapshot."
    }


@router.get("/taxonomy")
async def get_taxonomy(skill_matcher: SkillMatcher = Depends(get_skill_matcher)):
    """Retrieve full cataloged skill taxonomy with IDF weights."""
    return {
        "total_skills": len(skill_matcher.skill_categories),
        "skills_by_category": skill_matcher.skill_categories,
        "idf_weights": skill_matcher.idf_weights,
    }
