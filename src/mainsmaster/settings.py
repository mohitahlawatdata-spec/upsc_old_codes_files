"""Validated, environment-backed application settings."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / ".env")

ENVIRONMENTS = {"development", "test", "production"}
CLEANUP_PROVIDERS = {"gemini", "none"}
MENTOR_PROVIDERS = {"gemini"}
EMBEDDING_PROVIDERS = {"gemini"}
ARTIFACT_STORES = {"local", "s3"}


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def _boolean(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).strip().casefold()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def _choice(name: str, default: str, allowed: set[str]) -> str:
    value = os.getenv(name, default).strip().casefold()
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{name} must be one of: {choices}")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    google_api_key: str
    ocr_model: str
    eval_model: str
    restructure_model: str
    mentor_model: str
    data_dir: Path
    poppler_path: Path | None
    max_upload_mb: int
    max_pdf_pages: int
    app_env: str = "development"
    cleanup_provider: str = "gemini"
    mentor_provider: str = "gemini"
    embedding_provider: str = "gemini"
    embedding_model: str = "gemini-embedding-2"
    embedding_dim: int = 384
    artifact_store: str = "local"
    s3_endpoint_url: str = ""
    s3_region: str = "auto"
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_create_bucket: bool = False
    retain_local_artifacts: bool = True

    def validate(self) -> "Settings":
        """Validate settings that are independent of external service availability."""
        if self.app_env not in ENVIRONMENTS:
            raise ValueError(f"APP_ENV must be one of: {', '.join(sorted(ENVIRONMENTS))}")
        if self.cleanup_provider not in CLEANUP_PROVIDERS:
            raise ValueError("Unsupported CLEANUP_PROVIDER")
        if self.mentor_provider not in MENTOR_PROVIDERS:
            raise ValueError("Unsupported MENTOR_PROVIDER")
        if self.embedding_provider not in EMBEDDING_PROVIDERS:
            raise ValueError("Unsupported EMBEDDING_PROVIDER")
        if self.artifact_store not in ARTIFACT_STORES:
            raise ValueError("Unsupported ARTIFACT_STORE")
        if self.embedding_dim < 1:
            raise ValueError("EMBEDDING_DIM must be positive")
        if self.artifact_store == "s3":
            missing = [
                name
                for name, value in (
                    ("S3_ENDPOINT_URL", self.s3_endpoint_url),
                    ("S3_BUCKET", self.s3_bucket),
                    ("S3_ACCESS_KEY_ID", self.s3_access_key_id),
                    ("S3_SECRET_ACCESS_KEY", self.s3_secret_access_key),
                )
                if not value
            ]
            if missing:
                raise ValueError(f"S3 artifact storage requires: {', '.join(missing)}")
        if self.app_env == "production":
            if not self.database_url:
                raise ValueError("DATABASE_URL is required in production")
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY is required for OCR and evaluation")
            if self.artifact_store != "s3":
                raise ValueError("Production must use durable S3-compatible artifact storage")
        return self


def get_settings() -> Settings:
    data_value = Path(os.getenv("DATA_DIR", "var/data"))
    data_dir = data_value if data_value.is_absolute() else PROJECT_DIR / data_value
    poppler_value = os.getenv("POPPLER_PATH", "").strip()
    cleanup = _choice("CLEANUP_PROVIDER", "gemini", CLEANUP_PROVIDERS)
    mentor = _choice("MENTOR_PROVIDER", "gemini", MENTOR_PROVIDERS)
    embeddings = _choice("EMBEDDING_PROVIDER", "gemini", EMBEDDING_PROVIDERS)
    settings = Settings(
        database_url=os.getenv("DATABASE_URL", "").strip(),
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
        ocr_model=os.getenv("OCR_MODEL", "gemini-3.5-flash-lite").strip(),
        eval_model=os.getenv("EVAL_MODEL", "gemini-3.5-flash-lite").strip(),
        restructure_model=os.getenv(
            "RESTRUCTURE_MODEL",
            {
                "gemini": "gemini-3.5-flash-lite",
                "none": "none",
            }[cleanup],
        ).strip(),
        mentor_model=os.getenv(
            "MENTOR_MODEL",
            {
                "gemini": "gemini-3.5-flash-lite",
            }[mentor],
        ).strip(),
        data_dir=data_dir.resolve(),
        poppler_path=Path(poppler_value).resolve() if poppler_value else None,
        max_upload_mb=_positive_int("MAX_UPLOAD_MB", 20),
        max_pdf_pages=_positive_int("MAX_PDF_PAGES", 30),
        app_env=_choice("APP_ENV", "development", ENVIRONMENTS),
        cleanup_provider=cleanup,
        mentor_provider=mentor,
        embedding_provider=embeddings,
        embedding_model=os.getenv(
            "EMBEDDING_MODEL",
            "gemini-embedding-2",
        ).strip(),
        embedding_dim=_positive_int("EMBEDDING_DIM", 384),
        artifact_store=_choice("ARTIFACT_STORE", "local", ARTIFACT_STORES),
        s3_endpoint_url=os.getenv("S3_ENDPOINT_URL", "").strip(),
        s3_region=os.getenv("S3_REGION", "auto").strip(),
        s3_bucket=os.getenv("S3_BUCKET", "").strip(),
        s3_access_key_id=os.getenv("S3_ACCESS_KEY_ID", "").strip(),
        s3_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY", "").strip(),
        s3_create_bucket=_boolean("S3_CREATE_BUCKET", False),
        retain_local_artifacts=_boolean("RETAIN_LOCAL_ARTIFACTS", True),
    )
    return settings.validate()
