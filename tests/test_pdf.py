"""Upload size and type checks do not require Poppler or a model call."""

from pathlib import Path

import pytest

from mainsmaster.services.pdf import save_uploaded_pdf
from mainsmaster.settings import Settings


def settings(tmp_path: Path) -> Settings:
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
        max_pdf_pages=2,
    )


def test_rejects_non_pdf(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a PDF"):
        save_uploaded_pdf(b"not a pdf", tmp_path / "input.pdf", settings(tmp_path))


def test_rejects_large_upload(tmp_path: Path) -> None:
    data = b"%PDF-" + b"x" * (1024 * 1024)
    with pytest.raises(ValueError, match="upload limit"):
        save_uploaded_pdf(data, tmp_path / "input.pdf", settings(tmp_path))


def test_saves_pdf_inside_run(tmp_path: Path) -> None:
    destination = tmp_path / "run" / "input.pdf"
    result = save_uploaded_pdf(b"%PDF-test", destination, settings(tmp_path))
    assert result == destination
    assert destination.read_bytes() == b"%PDF-test"
