"""Configuration errors should fail before external services are called."""

from dataclasses import replace
from pathlib import Path

import pytest

from mainsmaster.settings import Settings


def base_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url="",
        google_api_key="",
        ocr_model="test",
        eval_model="test",
        restructure_model="test",
        mentor_model="test",
        data_dir=tmp_path,
        poppler_path=None,
        max_upload_mb=1,
        max_pdf_pages=1,
    )


def test_s3_requires_complete_credentials(tmp_path: Path) -> None:
    settings = replace(base_settings(tmp_path), artifact_store="s3")
    with pytest.raises(ValueError, match="S3 artifact storage requires"):
        settings.validate()


def test_production_rejects_local_artifacts(tmp_path: Path) -> None:
    settings = replace(
        base_settings(tmp_path),
        app_env="production",
        database_url="postgresql+psycopg://example",
        google_api_key="configured",
        cleanup_provider="gemini",
        mentor_provider="gemini",
        embedding_provider="gemini",
    )
    with pytest.raises(ValueError, match="durable S3-compatible"):
        settings.validate()
