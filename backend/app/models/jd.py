import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import Column, String, Text, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=True)
    raw_text = Column(Text, nullable=False)
    required_skills = Column(JSON, default=list, nullable=False)
    preferred_skills = Column(JSON, default=list, nullable=False)
    experience_required = Column(String(100), nullable=True)
    experience_years = Column(Float, nullable=True)
    qualifications = Column(JSON, default=list, nullable=False)
    responsibilities = Column(JSON, default=list, nullable=False)
    embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    resumes = relationship("Resume", back_populates="job_description", cascade="all, delete-orphan")
    match_results = relationship("MatchResult", back_populates="job_description", cascade="all, delete-orphan")

