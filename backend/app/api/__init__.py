from fastapi import APIRouter
from app.api.routes_jd import router as jd_router
from app.api.routes_resume import router as resume_router
from app.api.routes_match import router as match_router
from app.api.routes_skills import router as skills_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(jd_router)
api_router.include_router(resume_router)
api_router.include_router(match_router)
api_router.include_router(skills_router)

__all__ = ["api_router"]

