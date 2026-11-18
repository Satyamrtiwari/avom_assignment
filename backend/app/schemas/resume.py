from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ResumeStatus(BaseModel):
    id: str
    filename: str
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    experience_years: float | None = None
    skills: list[str] = []
    education: list[str] = []
    status: str  # "success", "parse_failed", "error"
    warnings: list[str] = []


class ResumeUploadResponse(BaseModel):
    jd_id: str | None = None
    total_received: int
    processed: int
    failed: int
    resumes: list[ResumeStatus]


class ResumeDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    jd_id: str | None = None
    filename: str
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    experience_years: float | None = None
    skills: list[str] = []
    education: list[str] = []
    raw_text: str | None = None
    has_embedding: bool = False
    created_at: datetime

