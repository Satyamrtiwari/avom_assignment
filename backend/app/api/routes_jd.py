import os
import aiofiles
from typing import Annotated
from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.deps import get_db, get_jd_extractor, get_embedder
from app.models.jd import JobDescription
from app.models.resume import Resume
from app.schemas.jd import JDDetailResponse, JDListResponse
from app.nlp.parser import parse_document
from app.nlp.jd_extractor import JDExtractor
from app.nlp.embedder import Embedder
from app.config import settings

router = APIRouter(prefix="/jd", tags=["Job Descriptions"])


@router.post("", response_model=JDDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_job_description(
    request: Request,
    title: Annotated[str | None, Form(description="Job title (optional, auto-extracted if omitted)")] = None,
    text: Annotated[str | None, Form(description="Raw JD text. Provide either text OR upload a file, not both.")] = None,
    file: Annotated[UploadFile | None, File(description="Job description document (.pdf, .docx, .txt). Provide either a file OR text, not both.")] = None,
    db: AsyncSession = Depends(get_db),
    jd_extractor: JDExtractor = Depends(get_jd_extractor),
    embedder: Embedder = Depends(get_embedder),
):
    """
    Create a new Job Description.
    Accepts raw text or an uploaded document (.txt, .pdf, .docx).
    At a time, either a file OR text must be provided.
    Extracts criteria and computes semantic embedding vector.
    """
    raw_content = ""

    # Check for presence of file and text (ignoring Swagger UI dummy "string")
    has_file = file is not None and bool(file.filename)
    has_text = bool(text and text.strip() and text.strip().lower() != "string")

    if has_file and has_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ambiguous input: Please provide either a Job Description document file or text, not both.",
        )

    if not has_file and not has_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Job Description provided. Please provide either a document file (.pdf, .docx, .txt) or enter text.",
        )

    if has_file:
        filename = file.filename or "job_description.txt"
        file_ext = os.path.splitext(filename)[1].lower()

        if file_ext not in [".pdf", ".docx", ".txt", ".md"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{file_ext}'. Allowed formats: .pdf, .docx, .txt",
            )

        saved_dir = os.path.join(settings.UPLOAD_DIR, "jds")
        os.makedirs(saved_dir, exist_ok=True)
        saved_path = os.path.join(saved_dir, filename)

        content_bytes = await file.read()
        async with aiofiles.open(saved_path, "wb") as f:
            await f.write(content_bytes)

        # Parse document
        parse_result = parse_document(saved_path, filename)

        if not parse_result.raw_text:
            warning_msg = (
                "; ".join(parse_result.warnings)
                if parse_result.warnings
                else "Unable to extract readable text from document."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to extract text from '{filename}': {warning_msg}",
            )

        raw_content = parse_result.raw_text
    else:
        raw_content = text.strip()

    if len(raw_content) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job Description content is too short (minimum 10 characters required).",
        )

    # Phase 3 Extraction: Extract structured criteria using JDExtractor
    extracted_title = None
    req_skills = []
    pref_skills = []
    exp_req = None
    exp_years = None
    quals = []
    resps = []

    if jd_extractor:
        jd_data = jd_extractor.extract(raw_content)
        extracted_title = jd_data.title
        req_skills = jd_data.required_skills
        pref_skills = jd_data.preferred_skills
        exp_req = jd_data.experience_required
        exp_years = jd_data.experience_years
        quals = jd_data.qualifications
        resps = jd_data.responsibilities

    final_title = title or extracted_title or "Job Description"

    # Phase 4 Embedding: Generate semantic vector
    embedding = None
    if embedder:
        embedding = embedder.embed(raw_content)

    jd = JobDescription(
        title=final_title,
        raw_text=raw_content,
        required_skills=req_skills,
        preferred_skills=pref_skills,
        experience_required=exp_req,
        experience_years=exp_years,
        qualifications=quals,
        responsibilities=resps,
        embedding=embedding,
    )

    db.add(jd)
    await db.commit()
    await db.refresh(jd)

    return JDDetailResponse(
        id=jd.id,
        title=jd.title,
        raw_text=jd.raw_text,
        required_skills=jd.required_skills or [],
        preferred_skills=jd.preferred_skills or [],
        experience_required=jd.experience_required,
        experience_years=jd.experience_years,
        qualifications=jd.qualifications or [],
        responsibilities=jd.responsibilities or [],
        has_embedding=(jd.embedding is not None),
        created_at=jd.created_at,
    )


@router.get("", response_model=list[JDListResponse])
async def list_job_descriptions(db: AsyncSession = Depends(get_db)):
    """List all stored job descriptions."""
    stmt = (
        select(
            JobDescription.id,
            JobDescription.title,
            JobDescription.created_at,
            JobDescription.required_skills,
            func.count(Resume.id).label("resumes_count"),
        )
        .outerjoin(Resume, Resume.jd_id == JobDescription.id)
        .group_by(JobDescription.id)
        .order_by(JobDescription.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        JDListResponse(
            id=row[0],
            title=row[1],
            created_at=row[2],
            required_skills_count=len(row[3]) if row[3] else 0,
            resumes_count=row[4] or 0,
        )
        for row in rows
    ]


@router.get("/{jd_id}", response_model=JDDetailResponse)
async def get_job_description(jd_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve full details of a specific Job Description."""
    stmt = select(JobDescription).where(JobDescription.id == jd_id)
    result = await db.execute(stmt)
    jd = result.scalar_one_or_none()

    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job Description with ID '{jd_id}' not found.",
        )

    return JDDetailResponse(
        id=jd.id,
        title=jd.title,
        raw_text=jd.raw_text,
        required_skills=jd.required_skills or [],
        preferred_skills=jd.preferred_skills or [],
        experience_required=jd.experience_required,
        experience_years=jd.experience_years,
        qualifications=jd.qualifications or [],
        responsibilities=jd.responsibilities or [],
        has_embedding=(jd.embedding is not None),
        created_at=jd.created_at,
    )


@router.delete("/{jd_id}", status_code=status.HTTP_200_OK)
async def delete_job_description(jd_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a Job Description along with its associated resumes and match results."""
    stmt = select(JobDescription).where(JobDescription.id == jd_id)
    result = await db.execute(stmt)
    jd = result.scalar_one_or_none()

    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job Description with ID '{jd_id}' not found.",
        )

    await db.delete(jd)
    await db.commit()
    return {"message": f"Job Description '{jd_id}' and all associated records deleted."}


@router.post("/reset-all", status_code=status.HTTP_200_OK)
async def reset_all_data(db: AsyncSession = Depends(get_db)):
    """Reset all job descriptions, resumes, and match results to start completely fresh."""
    from app.models.match_result import MatchResult
    from sqlalchemy import delete
    await db.execute(delete(MatchResult))
    await db.execute(delete(Resume))
    await db.execute(delete(JobDescription))
    await db.commit()
    return {"message": "All workspace data cleared successfully."}

