import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    jd_id = Column(String(36), ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(Float, nullable=False)
    semantic_score = Column(Float, nullable=False)
    skill_score = Column(Float, nullable=False)
    experience_score = Column(Float, nullable=False)
    qualification_score = Column(Float, nullable=False)
    raw_cosine = Column(Float, nullable=True, default=0.0)
    matched_skills = Column(JSON, default=list, nullable=False)
    missing_skills = Column(JSON, default=list, nullable=False)
    experience_comparison = Column(JSON, default=dict, nullable=False)
    meta_audit = Column(JSON, default=dict, nullable=True)
    explanation = Column(Text, default="", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job_description = relationship("JobDescription", back_populates="match_results")
    resume = relationship("Resume", back_populates="match_results")
