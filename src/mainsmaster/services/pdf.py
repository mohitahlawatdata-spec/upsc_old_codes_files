"""Bounded PDF input and page rendering."""

from pathlib import Path

from pdf2image import convert_from_path, pdfinfo_from_path

from mainsmaster.diagnostics import stage
from mainsmaster.settings import Settings


def save_uploaded_pdf(content: bytes, destination: Path, settings: Settings) -> Path:
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise ValueError(f"PDF exceeds the {settings.max_upload_mb} MB upload limit")
    if not content.lstrip().startswith(b"%PDF-"):
        raise ValueError("Uploaded file is not a PDF")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return destination


def render_pdf_pages(pdf_path: Path, image_dir: Path, settings: Settings) -> list[Path]:
    options = {"poppler_path": str(settings.poppler_path)} if settings.poppler_path else {}
    with stage("PDF inspect metadata"):
        info = pdfinfo_from_path(str(pdf_path), **options)
    page_count = int(info.get("Pages", 0))
    if page_count < 1 or page_count > settings.max_pdf_pages:
        raise ValueError(f"PDF must have 1 to {settings.max_pdf_pages} pages; found {page_count}")
    image_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for page_number in range(1, page_count + 1):
        with stage(f"PDF render page {page_number}/{page_count}"):
            pages = convert_from_path(
                str(pdf_path), dpi=200, first_page=page_number, last_page=page_number, **options
            )
            if len(pages) != 1:
                raise RuntimeError(f"Could not render page {page_number}")
            path = image_dir / f"page_{page_number}.jpg"
            pages[0].save(path, "JPEG")
            pages[0].close()
            paths.append(path)
    return paths
