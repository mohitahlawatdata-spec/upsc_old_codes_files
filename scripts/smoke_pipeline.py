"""Run document processing on a test PDF without writing to PostgreSQL."""

import argparse
import asyncio
import uuid
from pathlib import Path

from mainsmaster.diagnostics import configure_logging
from mainsmaster.pipeline import process_essay
from mainsmaster.settings import get_settings


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path, help="A PDF you are authorized to process")
    args = parser.parse_args()
    settings = get_settings()
    if not args.pdf.is_file():
        parser.error("PDF does not exist")
    run_dir = settings.data_dir / "smoke" / str(uuid.uuid4())
    result = asyncio.run(process_essay(args.pdf, run_dir, settings, progress=print))
    print(f"Report: {result.report.topic}")
    print(f"Score: {result.report.metadata.marks_obtained}/125")
    print(f"RAG chunks: {len(result.chunks)}")
    print(f"Artifacts: {run_dir / 'output'}")


if __name__ == "__main__":
    main()
