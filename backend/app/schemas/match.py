from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class MatchRequest(BaseModel):
    jd_id: str = Field(..., description="ID of the Job Description to match against")


class MatchResponse(BaseModel):
    jd_id: str
    status: str
    message: str
    candidates_matched: int = 0


class CandidateRanking(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    resume_id: str
    candidate_name: str | None = None
    experience_years: float | None = None
    overall_score: float
    skill_score: float | None = None
    semantic_score: float | None = None
    experience_score: float | None = None
    qualification_score: float | None = None
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    candidate_skills: list[str] = []


class RankingResponse(BaseModel):
    jd_id: str
    jd_title: str | None = None
    total_candidates: int
    candidates: list[CandidateRanking]


class CandidateDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resume_id: str
    jd_id: str
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    experience_years: float | None = None
    total_experience_years: float | None = None
    relevant_experience_years: float | None = None
    experience_source: str = "dates"
    is_experience_unknown: bool = False
    education: list[str] = []
    overall_score: float
    raw_cosine: float | None = 0.0
    weights_used: dict[str, float] = {}
    score_breakdown: dict[str, float]
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    candidate_skills: list[str] = []
    matched_skills_detailed: list[dict] = []
    experience_comparison: dict = {}
    explanation: str = ""
    warnings: list[str] = []
    meta_audit: dict = {}
    created_at: datetime
