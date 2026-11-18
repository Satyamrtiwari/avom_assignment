# 🚀 ResumeRanker — AI-Based Resume Matching & Candidate Ranking System

> **Candidate Assignment**: AI / Full Stack Developer Intern  
> **Technologies**: Python 3.11, FastAPI, sentence-transformers (`all-MiniLM-L6-v2`), spaCy (`en_core_web_sm`), PyMuPDF, python-docx, SQLite / PostgreSQL.

---

## 📌 Project Overview

ResumeRanker is an AI-powered recruitment engine that compares candidate resumes against Job Descriptions (JDs) to compute explainable matching scores (0–100), identify matched and missing skills, analyze relevant experience, and provide an interactive ranking dashboard.

### Core Modules Implemented

- **Module 1: Job Description Input** — Accept JD via raw text or document upload (`.pdf`, `.docx`, `.txt`). Extracts job title, required skills, preferred skills, experience requirements, and qualifications.
- **Module 2: Batch Resume Upload** — Support uploading batches of 10+ resumes in both PDF and DOCX formats with automatic text extraction and quality assessment.
- **Module 3: Multi-Signal AI Matching** — Combines canonical skill matching (via spaCy `PhraseMatcher`) with dense semantic vector embeddings (`all-MiniLM-L6-v2`), graduated experience curves, and degree alignment.
- **Module 4: Candidate Ranking Dashboard** — Ranks candidates in a sortable grid ordered strictly by match score, displaying experience years, match %, and matched skills.
- **Module 5: Candidate-Level Deep Dive** — Full analytical breakdown detailing the 4 component scores, matched skills, missing skills, experience comparison verdict, and plain-English scoring rationale.

---

## ⚙️ Technology Stack & Justification

| Component | Choice | Rationale |
|---|---|---|
| **API Framework** | **FastAPI** | High-performance async endpoints, automatic Pydantic validation, interactive OpenAPI/Swagger documentation at `/docs`. |
| **NLP Embeddings** | **Sentence Transformers (`all-MiniLM-L6-v2`)** | 80 MB model size, fast CPU latency (~14 ms/sentence), 384-dimensional dense vectors. Runs fully offline without external API keys or costs. |
| **Skill Extraction & NER** | **spaCy (`en_core_web_sm`)** | Fast entity recognition for candidate names, paired with a custom `PhraseMatcher` indexed against a 500+ tech skill taxonomy (`skills.json`) with synonym mapping (e.g. `k8s` $\to$ `Kubernetes`). |
| **Document Parsing** | **PyMuPDF + python-docx** | Fast extraction from native PDFs and Word documents, including table cell parsing (crucial for tabular resumes) and scanned PDF quality detection. Fallback to `pdfplumber`. |
| **Database** | **SQLite (aiosqlite) / PostgreSQL (asyncpg)** | Zero-configuration SQLite for instant local development; SQLAlchemy 2.0 ORM abstracts dialect for seamless PostgreSQL deployment. Embeddings cached in JSON columns. |

---

## 🚀 Quickstart & How to Run the Backend

### Prerequisites
- Python 3.11+
- Virtual environment tool (`uv` or `python -m venv`)

### 1. Setup & Dependencies
```bash
# Clone and enter directory
cd avom_assignment/backend

# Activate the virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies (if setting up fresh)
pip install -r requirements.txt
```

### 2. Start the Backend Server
```bash
# From the project root or backend directory:
uvicorn app.main:app --reload --port 8000
```

Once started:
- **Interactive Swagger UI**: [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **Health Check**: [`http://localhost:8000/health`](http://localhost:8000/health)

---

## 🧪 Testing the 12 Sample Resumes

We have provided a sample job description and **12 synthetic candidate resumes** (PDF & DOCX) in `sample_data/`:
- `sample_data/sample_jd.pdf` — Senior Java Backend Developer JD
- `sample_data/resumes/` — 12 candidate resumes covering strong matches, good matches, moderate matches, and weak matches.

### Option A: Via Swagger UI (`http://localhost:8000/docs`)
1. Open [`http://localhost:8000/docs`](http://localhost:8000/docs) in your browser.
2. Under **Job Descriptions**, expand `POST /api/v1/jd`, upload `sample_data/sample_jd.pdf`, and click **Execute**. Copy the returned `id`.
3. Under **Resumes**, expand `POST /api/v1/resumes`, paste the `jd_id`, select all 12 files from `sample_data/resumes/`, and click **Execute**.
4. Under **Matching & Ranking**, expand `POST /api/v1/match`, input the `jd_id`, and click **Execute**.
5. Expand `GET /api/v1/results/{jd_id}` to view the ranked candidate dashboard!
6. Expand `GET /api/v1/results/{jd_id}/candidates/{resume_id}` to view in-depth candidate analysis.

### Option B: Run Automated Test Suite
```bash
# Run all unit, integration, and edge-case tests
pytest backend/tests -v
```

---

## 📊 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/jd` | Create Job Description (accepts text or file upload `.pdf`/`.docx`) |
| `GET` | `/api/v1/jd` | List all stored Job Descriptions |
| `GET` | `/api/v1/jd/{jd_id}` | Retrieve specific Job Description with extracted requirements |
| `DELETE` | `/api/v1/jd/{jd_id}` | Delete Job Description and cascade delete all associated records |
| `POST` | `/api/v1/resumes` | Batch upload candidate resumes (supports 10+ PDF/DOCX files) |
| `GET` | `/api/v1/resumes/{resume_id}` | Retrieve individual resume details and extracted skills |
| `GET` | `/api/v1/resumes/by-jd/{jd_id}` | List all candidate resumes uploaded for a specific JD |
| `POST` | `/api/v1/match` | Run multi-signal matching algorithm and generate scores |
| `GET` | `/api/v1/results/{jd_id}` | Retrieve candidate ranking dashboard table |
| `GET` | `/api/v1/results/{jd_id}/candidates/{resume_id}` | Retrieve in-depth candidate analysis and score justification |
| `GET` | `/health` | Check system status and loaded models |

---

## 📑 Matching Methodology

For full mathematical formulas, scoring curves, and explainability logic, refer to [ALGORITHM.md](ALGORITHM.md).

---

## 🔮 Future Scope & Production Roadmap

While the current architecture provides a fast, deterministic, explainable, and zero-cost local engine, scaling this system to enterprise production (handling millions of candidates across global organizations) involves the following planned enhancements:

### 1. Dynamic Skill Taxonomy as a Service (Beyond Static `skills.json`)
- **Integration with Global Taxonomies**: Connect with industry-standard skill ontologies such as **Lightcast (EMSI)**, **ESCO (European Skills/Competences)**, and **O\*NET** (30,000+ continuously updated skills).
- **Contextual Token-Classification (Transformer NER)**: Replace dictionary `PhraseMatcher` with a fine-tuned `RoBERTa-NER` or `spaCy Transformer` model to extract emerging and domain-specific skill spans directly from context, even if never seen before.
- **Dense Entity Linking**: Map novel extracted spans (e.g., *"LangGraph multi-agent routing"*) to canonical graph entities using bi-encoder dense retrieval and cross-encoder re-ranking.
- **Continuous LLM Ingestion Pipeline**: Asynchronously cluster unrecognized terms across incoming resumes and use an LLM-in-the-loop worker to propose new taxonomy nodes for recruiter review.

### 2. Standardized Educational Ontologies (Beyond Hardcoded Tables)
- **International Degree Equivalence**: Replace the static degree hierarchy with **UNESCO ISCED-F** (International Standard Classification of Education) and **CIP** (Classification of Instructional Programs) databases to handle European Bologna degrees, French *Grandes Écoles*, Indian integrated dual degrees, and UK honours credentials.
- **Semantic Major / Field Matching**: Replace the 8-keyword `TECH_FIELDS` filter with vector similarity matching between candidate majors and JD requirements (e.g. recognizing *"Computational Neuroscience"* or *"Robotics"* as high-affinity fields for an AI role).
- **Recruiter Policy & Experience Substitution**: Allow hiring managers to designate degree requirements as *"Strict Knockout"* (e.g. licensed professions) or *"Soft Preference"* with automatic work experience substitution rules (e.g. 2 years of relevant engineering replaces 1 year of formal degree).

### 3. Dynamic & Learned Scoring Models (Beyond Static Weights)
- **Role-Specific Weight Profiles**: Enable recruiters to save role profiles (e.g. Research Scientist = 45% semantic, 35% qualification vs Full Stack Dev = 50% skills, 30% experience).
- **Learning-to-Rank (LTR)**: Train machine-learned ranking models (**LambdaMART**, **XGBoost Ranker**) on anonymized recruiter actions (shortlist, interview, offer) to continuously optimize matching weights based on real hiring outcomes.
- **Confidence Scoring & Imputation**: Replace arbitrary fallback scores (`50.0%`, `55.0%`) with explicit confidence scores and human-in-the-loop review flags when candidate resumes lack structured sections.

### 4. Enterprise Distributed Cloud Infrastructure
- **Vector Database**: Migrate cached embeddings from SQLite/PostgreSQL JSON to **PostgreSQL + pgvector** or dedicated vector search engines (**Qdrant**, **Milvus**, **Pinecone**) for sub-second similarity searches across millions of candidate profiles.
- **Asynchronous Worker Queues**: Decouple document parsing and embedding computation from the HTTP request cycle using **Celery / Redis / RabbitMQ** or AWS SQS, allowing bulk uploads of 1,000+ resumes without timeouts.
- **Cloud Object Storage**: Transition local `uploads/` directory to **AWS S3 / Google Cloud Storage / Azure Blob** with pre-signed URLs for secure, multi-tenant horizontal scaling.
- **Visual Document Understanding (VDU)**: Incorporate **LayoutLMv3** or multimodal vision-language parsers to preserve reading order and section hierarchy in complex two-column, infographic, and design resumes.


