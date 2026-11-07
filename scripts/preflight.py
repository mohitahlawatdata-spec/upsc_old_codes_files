"""Local prerequisite check with opt-in live provider calls."""

import argparse
import shutil
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from mainsmaster.db.models import Base
from mainsmaster.settings import get_settings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-gemini", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    failures = []

    if not settings.database_url:
        failures.append("DATABASE_URL is missing")
    else:
        try:
            engine = create_engine(settings.database_url, pool_pre_ping=True)
            with engine.connect() as connection:
                extensions = set(
                    connection.execute(text("SELECT extname FROM pg_extension")).scalars()
                )
                if "vector" not in extensions:
                    failures.append(
                        "PostgreSQL is running but pgvector is not enabled; run migrations"
                    )
                tables = set(inspect(connection).get_table_names())
                required = {"users", "evaluations", "documents", "chat_sessions", "messages"}
                missing_tables = required - tables
                if missing_tables:
                    failures.append(
                        f"Database tables missing: {', '.join(sorted(missing_tables))}; run migrations"
                    )
                else:
                    database_inspector = inspect(connection)
                    for table in sorted(required):
                        expected_columns = set(Base.metadata.tables[table].columns.keys())
                        actual_columns = {
                            column["name"] for column in database_inspector.get_columns(table)
                        }
                        missing_columns = expected_columns - actual_columns
                        if missing_columns:
                            failures.append(
                                f"{table} columns missing: {', '.join(sorted(missing_columns))}"
                            )
                    if "alembic_version" not in tables:
                        print(
                            "WARN: legacy schema has no Alembic version; do not stamp before review"
                        )
            engine.dispose()
            print("OK: PostgreSQL connection")
        except Exception as exc:
            failures.append(
                f"PostgreSQL connection failed ({type(exc).__name__}); check host, credentials, and network"
            )

    poppler = (
        settings.poppler_path / "pdfinfo.exe" if settings.poppler_path else shutil.which("pdfinfo")
    )
    if poppler and Path(poppler).exists():
        print("OK: Poppler pdfinfo")
    else:
        failures.append("Poppler pdfinfo was not found; set POPPLER_PATH or add it to PATH")

    if not settings.google_api_key:
        failures.append("GOOGLE_API_KEY is missing")
    elif args.live_gemini:
        from google import genai

        client = genai.Client(api_key=settings.google_api_key)
        try:
            models = {settings.ocr_model, settings.eval_model}
            if settings.cleanup_provider == "gemini":
                models.add(settings.restructure_model)
            if settings.mentor_provider == "gemini":
                models.add(settings.mentor_model)
            for model in models:
                response = client.models.generate_content(model=model, contents="Reply OK")
                if not response.text:
                    failures.append(f"Gemini model {model} returned no text")
            if settings.embedding_provider == "gemini":
                response = client.models.embed_content(
                    model=settings.embedding_model,
                    contents="UPSC essay mentor",
                )
                if not response.embeddings:
                    failures.append(
                        f"Gemini embedding model {settings.embedding_model} returned no vector"
                    )
            if not failures:
                print("OK: Gemini model access")
        except Exception as exc:
            failures.append(f"Gemini model access failed: {exc}")
        finally:
            client.close()
    else:
        print("SKIP: live Gemini access (use --live-gemini to check)")

    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
