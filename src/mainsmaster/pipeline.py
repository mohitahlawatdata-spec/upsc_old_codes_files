"""End-to-end essay processing with one database commit."""

import asyncio
import json
import shutil
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mainsmaster.db.repositories import add_evaluation_bundle
from mainsmaster.db.session import session_scope
from mainsmaster.diagnostics import logger, stage
from mainsmaster.providers.factory import embedding_provider
from mainsmaster.schemas import EvaluationReport, rag_chunks
from mainsmaster.services.embeddings import embed
from mainsmaster.services.evaluate import evaluate_essay
from mainsmaster.services.ocr import extract_pages
from mainsmaster.services.pdf import render_pdf_pages
from mainsmaster.services.restructure import restructure_essay
from mainsmaster.settings import Settings
from mainsmaster.storage.factory import artifact_store


@dataclass(frozen=True)
class ProcessedEssay:
    report: EvaluationReport
    original_essay: str
    chunks: list[tuple[str, list[float]]]
    ocr_input_tokens: int
    ocr_output_tokens: int
    eval_input_tokens: int
    eval_output_tokens: int


async def process_essay(
    pdf_path: Path, run_dir: Path, settings: Settings, progress: Callable[[str], None] | None = None
) -> ProcessedEssay:
    """Build artifacts and a validated report without touching the database."""
    output_dir = run_dir / "output"
    with stage("Rendering PDF pages", progress):
        image_paths = await asyncio.to_thread(
            render_pdf_pages, pdf_path, output_dir / "images", settings
        )
        logger.info("PDF pages: %d", len(image_paths))
    with stage(f"Reading {len(image_paths)} pages with OCR", progress):
        ocr = await extract_pages(image_paths, settings)
        logger.info(
            "OCR pages: %d; input tokens: %d; output tokens: %d",
            len(ocr.page_texts),
            ocr.input_tokens,
            ocr.output_tokens,
        )
    (output_dir / "1_raw_ocr_output.txt").write_text(
        f"Question\n{ocr.question}\n\nAnswer\n{ocr.answer}", encoding="utf-8"
    )
    with stage(f"Cleaning OCR text with {settings.cleanup_provider}", progress):
        answer = await restructure_essay(ocr.answer, settings)
    (output_dir / "2_restructured_essay.txt").write_text(answer, encoding="utf-8")
    (output_dir / "2_restructured_essay.json").write_text(
        json.dumps({"question": ocr.question, "answer": answer}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with stage("Generating evaluation with Gemini", progress):
        evaluated = await asyncio.to_thread(evaluate_essay, ocr.question, answer, settings)
        logger.info(
            "Evaluation input tokens: %d; output tokens: %d",
            evaluated.input_tokens,
            evaluated.output_tokens,
        )
    report = evaluated.report
    (output_dir / "3_final_evaluation.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    with stage("Preparing mentor search index", progress):
        source_chunks = rag_chunks(report)
        chunks = []
        embedder = embedding_provider(settings)
        for number, text in enumerate(source_chunks, start=1):
            with stage(f"Mentor chunk {number}/{len(source_chunks)}"):
                chunks.append((text, embed(text, settings, embedder)))
        logger.info("Mentor chunks: %d", len(chunks))
    return ProcessedEssay(
        report,
        answer,
        chunks,
        ocr.input_tokens,
        ocr.output_tokens,
        evaluated.input_tokens,
        evaluated.output_tokens,
    )


async def run_pipeline(
    user_id: uuid.UUID,
    pdf_path: Path,
    run_dir: Path,
    settings: Settings,
    progress: Callable[[str], None] | None = None,
) -> uuid.UUID:
    """Process an upload and commit its complete report, index, and chat session."""
    processed = await process_essay(pdf_path, run_dir, settings, progress)
    artifact_prefix = f"users/{user_id}/runs/{run_dir.name}"
    if settings.artifact_store == "s3":
        rendered_pages = run_dir / "output" / "images"
        if rendered_pages.exists():
            await asyncio.to_thread(shutil.rmtree, rendered_pages)
    store = artifact_store(settings)
    with stage("Publishing artifacts", progress):
        uploaded = await asyncio.to_thread(
            store.upload_tree,
            run_dir,
            artifact_prefix,
        )
        logger.info("Published artifacts: %d", len(uploaded))
    try:
        with stage("Saving report", progress), session_scope() as session:
            evaluation_id = add_evaluation_bundle(
                session,
                user_id,
                processed.report,
                processed.original_essay,
                processed.chunks,
                processed.ocr_input_tokens,
                processed.ocr_output_tokens,
                processed.eval_input_tokens,
                processed.eval_output_tokens,
                system_metadata={
                    "artifact_prefix": artifact_prefix,
                    "ocr_model": settings.ocr_model,
                    "cleanup_provider": settings.cleanup_provider,
                    "cleanup_model": settings.restructure_model,
                    "evaluation_model": settings.eval_model,
                    "embedding_provider": settings.embedding_provider,
                    "embedding_model": settings.embedding_model,
                    "embedding_dimensions": settings.embedding_dim,
                    "mentor_provider": settings.mentor_provider,
                    "mentor_model": settings.mentor_model,
                },
            )
    except Exception:
        if settings.artifact_store == "s3":
            await asyncio.to_thread(store.delete_prefix, artifact_prefix)
        raise
    if settings.artifact_store == "s3" and not settings.retain_local_artifacts:
        await asyncio.to_thread(shutil.rmtree, run_dir)
    return evaluation_id
