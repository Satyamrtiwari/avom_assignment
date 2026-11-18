import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    jd_id = Column(String(36), ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=True)
    filename = Column(String(255), nullable=False)
    candidate_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(100), nullable=True)
    experience_years = Column(Float, nullable=True)
    skills = Column(JSON, default=list, nullable=False)
    education = Column(JSON, default=list, nullable=False)
    raw_text = Column(Text, nullable=True)
    embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job_description = relationship("JobDescription", back_populates="resumes")
    match_results = relationship("MatchResult", back_populates="resume", cascade="all, delete-orphan")

