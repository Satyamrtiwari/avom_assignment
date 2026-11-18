import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./resume_ranker.db"

    # NLP Models
    SBERT_MODEL: str = "all-MiniLM-L6-v2"
    SPACY_MODEL: str = "en_core_web_sm"

    # Scoring Weights (0.35 / 0.30 / 0.20 / 0.15)
    WEIGHT_SKILL: float = 0.35
    WEIGHT_SEMANTIC: float = 0.30
    WEIGHT_EXPERIENCE: float = 0.20
    WEIGHT_QUALIFICATION: float = 0.15
    WEIGHT_PREFERRED_SKILL_RATIO: float = 0.35
    RESPONSIBILITIES_SKILL_RATIO: float = 0.25

    # Primary Skill Identification & Damping
    PRIMARY_SKILL_WEIGHT_MULTIPLIER: float = 2.0
    PRIMARY_ZERO_DAMPING: float = 0.20
    IN_PROGRESS_DEGREE_PENALTY: float = 12.0

    # Experience Reconciliation & Truth Grounding
    EXP_DISCREPANCY_THRESHOLD_YEARS: float = 1.0
    EXP_SUMMARY_DISCREPANCY_RATIO: float = 1.4
    EXP_TOLERANCE_YEARS: float = 1.0

    # Semantic Calibration (Percentile-calibrated boundaries from labelled pairs)
    SEMANTIC_COSINE_FLOOR: float = 0.50
    SEMANTIC_COSINE_CEILING: float = 0.80

    # Smooth Relevance Factor (Continuous modulation without hard caps)
    RELEVANCE_SKILL_COEFF: float = 0.70
    RELEVANCE_SEMANTIC_COEFF: float = 0.30
    RELEVANCE_MIN_THRESHOLD: float = 0.15
    RELEVANCE_FULL_THRESHOLD: float = 0.50

    # Fuzzy Matching Constraints (Never on short/ambiguous names)
    MIN_FUZZY_SKILL_LENGTH: int = 5
    FUZZY_MATCH_THRESHOLD: float = 0.90
    AMBIGUOUS_SHORT_SKILLS: list[str] = [
        "r", "c", "go", "c#", "c++", "js", "ts", "ai", "ml", "ui", "ux", "qa",
        "sql", "php", "git", "java", "ruby", "rust", "dart"
    ]

    # Data Paths & Snapshots
    DATA_DIR: str = str(BASE_DIR / "data")
    SECTION_HEADINGS_PATH: str = str(BASE_DIR / "data" / "section_headings.json")
    DEGREES_TAXONOMY_PATH: str = str(BASE_DIR / "data" / "degrees_taxonomy.json")
    IDF_SNAPSHOT_PATH: str = str(BASE_DIR / "data" / "idf_snapshot_v1.json")
    IDF_MIN_CORPUS_SIZE: int = 10
    IDF_FALLBACK_WEIGHT: float = 1.0

    # Upload Limits
    MAX_FILE_SIZE_MB: int = 5
    MAX_BATCH_SIZE: int = 30
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")

    # Application & CORS
    CORS_ORIGINS: list[str] | str = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        if isinstance(self.CORS_ORIGINS, str):
            if self.CORS_ORIGINS.strip() == "*":
                return ["*"]
            return [x.strip() for x in self.CORS_ORIGINS.split(",") if x.strip()]
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=(str(BASE_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
