import os
import aiofiles
from typing import Annotated
from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, get_resume_extractor, get_embedder
from app.models.jd import JobDescription
from app.models.resume import Resume
from app.schemas.resume import (
    ResumeUploadResponse,
    ResumeStatus,
    ResumeDetailResponse,
)
from app.nlp.parser import parse_document
from app.nlp.extractor import ResumeExtractor
from app.nlp.embedder import Embedder
from app.config import settings

router = APIRouter(prefix="/resumes", tags=["Resumes"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@router.post("", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resumes(
    request: Request,
    jd_id: Annotated[str | None, Form(description="Optional Job Description ID to link and match these resumes against")] = None,
    files: Annotated[
        list[UploadFile],
        File(description="Upload one or more candidate resumes (.pdf, .docx, .txt)"),
    ] = None,
    db: AsyncSession = Depends(get_db),
    resume_extractor: ResumeExtractor = Depends(get_resume_extractor),
    embedder: Embedder = Depends(get_embedder),
):
    """
    Batch upload candidate resumes (supports PDF, DOCX, and TXT).
    Parses documents, extracts structured data, and computes semantic vector embeddings.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resume files were provided.",
        )

    if len(files) > settings.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exceeded maximum batch limit of {settings.MAX_BATCH_SIZE} resumes.",
        )

    # Sanitize jd_id (ignore Swagger UI placeholder "string" or empty spaces)
    if jd_id and jd_id.strip() and jd_id.strip().lower() != "string":
        jd_id = jd_id.strip()
    else:
        jd_id = None

    # Verify JD exists if provided
    if jd_id:
        jd_check = await db.execute(select(JobDescription).where(JobDescription.id == jd_id))
        if not jd_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job Description with ID '{jd_id}' not found.",
            )

    target_dir = os.path.join(settings.UPLOAD_DIR, jd_id if jd_id else "unassigned")
    os.makedirs(target_dir, exist_ok=True)

    statuses: list[ResumeStatus] = []
    created_resumes: list[Resume] = []
    processed_count = 0
    failed_count = 0
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024

    for upload in files:
        filename = upload.filename or "unknown_resume"
        ext = os.path.splitext(filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            failed_count += 1
            statuses.append(
                ResumeStatus(
                    id="",
                    filename=filename,
                    status="error",
                    warnings=[f"Unsupported file format '{ext}'. Allowed: .pdf, .docx, .txt"],
                )
            )
            continue

        try:
            content = await upload.read()
            if len(content) > max_bytes:
                failed_count += 1
                statuses.append(
                    ResumeStatus(
                        id="",
                        filename=filename,
                        status="error",
                        warnings=[f"File size exceeds {settings.MAX_FILE_SIZE_MB}MB limit."],
                    )
                )
                continue

            file_path = os.path.join(target_dir, filename)
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)

            # Phase 2 Parsing: Extract clean raw text
            parse_result = parse_document(file_path, filename)

            # Fallback candidate name from filename
            fallback_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()

            candidate_name = fallback_name
            email = None
            phone = None
            experience_years = None
            skills = []
            education = []
            all_warnings = list(parse_result.warnings)

            # Phase 3 Extraction: Extract structured profile if parsing succeeded
            if parse_result.raw_text and parse_result.quality != "poor" and resume_extractor:
                extracted = resume_extractor.extract(parse_result.raw_text)
                if extracted.candidate_name:
                    candidate_name = extracted.candidate_name
                email = extracted.email
                phone = extracted.phone
                experience_years = extracted.experience_years
                skills = extracted.skills
                education = extracted.education
                all_warnings.extend(extracted.warnings)

            is_success = bool(parse_result.raw_text and parse_result.quality != "poor")
            status_str = "success" if is_success else "parse_failed"

            resume = Resume(
                jd_id=jd_id,
                filename=filename,
                candidate_name=candidate_name,
                email=email,
                phone=phone,
                experience_years=experience_years,
                raw_text=parse_result.raw_text,
                skills=skills,
                education=education,
                embedding=None,  # Populated in batch below
            )
            db.add(resume)
            await db.flush()

            if is_success:
                processed_count += 1
                created_resumes.append(resume)
            else:
                failed_count += 1

            statuses.append(
                ResumeStatus(
                    id=resume.id,
                    filename=filename,
                    candidate_name=resume.candidate_name,
                    email=resume.email,
                    phone=resume.phone,
                    experience_years=resume.experience_years,
                    skills=resume.skills,
                    education=resume.education,
                    status=status_str,
                    warnings=all_warnings,
                )
            )

        except Exception as exc:
            failed_count += 1
            statuses.append(
                ResumeStatus(
                    id="",
                    filename=filename,
                    status="error",
                    warnings=[f"Failed to process file: {str(exc)}"],
                )
            )

    # Phase 4 Batch Embedding: compute embeddings for all successfully parsed resumes
    if created_resumes and embedder:
        texts_to_embed = [r.raw_text for r in created_resumes if r.raw_text]
        if texts_to_embed:
            vectors = embedder.embed_batch(texts_to_embed)
            vec_idx = 0
            for r in created_resumes:
                if r.raw_text and vec_idx < len(vectors):
                    r.embedding = vectors[vec_idx]
                    vec_idx += 1

    await db.commit()

    return ResumeUploadResponse(
        jd_id=jd_id,
        total_received=len(files),
        processed=processed_count,
        failed=failed_count,
        resumes=statuses,
    )


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
async def get_resume(resume_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve full details of an individual candidate resume."""
    stmt = select(Resume).where(Resume.id == resume_id)
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with ID '{resume_id}' not found.",
        )

    return ResumeDetailResponse(
        id=resume.id,
        jd_id=resume.jd_id,
        filename=resume.filename,
        candidate_name=resume.candidate_name,
        email=resume.email,
        phone=resume.phone,
        experience_years=resume.experience_years,
        skills=resume.skills or [],
        education=resume.education or [],
        raw_text=resume.raw_text,
        has_embedding=(resume.embedding is not None),
        created_at=resume.created_at,
    )


@router.get("/by-jd/{jd_id}", response_model=list[ResumeDetailResponse])
async def list_resumes_for_jd(jd_id: str, db: AsyncSession = Depends(get_db)):
    """List all resumes uploaded for a given Job Description."""
    stmt = select(Resume).where(Resume.jd_id == jd_id).order_by(Resume.created_at.desc())
    result = await db.execute(stmt)
    resumes = result.scalars().all()

    return [
        ResumeDetailResponse(
            id=r.id,
            jd_id=r.jd_id,
            filename=r.filename,
            candidate_name=r.candidate_name,
            email=r.email,
            phone=r.phone,
            experience_years=r.experience_years,
            skills=r.skills or [],
            education=r.education or [],
            raw_text=r.raw_text,
            has_embedding=(r.embedding is not None),
            created_at=r.created_at,
        )
        for r in resumes
    ]


@router.get("/{resume_id}/file")
async def get_resume_file(resume_id: str, db: AsyncSession = Depends(get_db)):
    """Serve the raw uploaded resume document (PDF, DOCX, TXT) for inline browser viewing."""
    stmt = select(Resume).where(Resume.id == resume_id)
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume with ID '{resume_id}' not found.",
        )

    # Search known upload and sample locations
    possible_paths = [
        os.path.join(settings.UPLOAD_DIR, resume.jd_id if resume.jd_id else "unassigned", resume.filename),
        os.path.join(settings.UPLOAD_DIR, "unassigned", resume.filename),
        os.path.join(settings.UPLOAD_DIR, resume.filename),
        os.path.join("sample_data", resume.filename),
        os.path.join("..", "sample_data", resume.filename),
        os.path.join(r"C:\Users\3star\Downloads", resume.filename),
    ]

    found_path = None
    for p in possible_paths:
        if p and os.path.exists(p):
            found_path = p
            break

    if not found_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume file '{resume.filename}' not found on server disk.",
        )

    ext = os.path.splitext(resume.filename)[1].lower()
    media_type = "application/pdf" if ext == ".pdf" else "application/octet-stream" if ext == ".docx" else "text/plain"

    return FileResponse(
        found_path,
        media_type=media_type,
        filename=resume.filename,
        content_disposition_type="inline"
    )

