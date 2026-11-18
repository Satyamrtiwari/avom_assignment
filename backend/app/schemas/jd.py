from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class JDCreate(BaseModel):
    title: str | None = None
    raw_text: str = Field(..., min_length=10, description="Job description text")


class JDListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None = None
    created_at: datetime
    required_skills_count: int = 0
    resumes_count: int = 0


class JDDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None = None
    raw_text: str
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    experience_required: str | None = None
    experience_years: float | None = None
    qualifications: list[str] = []
    responsibilities: list[str] = []
    has_embedding: bool = False
    created_at: datetime

