# Clean app implementation status

Updated 2026-11-07. This directory is the standalone, publishable MainsMaster application. Historical workspace files outside it are not application source and must not be included in its Git repository.

## Implemented

- One portable AI credential: `GOOGLE_API_KEY`. Gemini performs OCR, optional fidelity-checked cleanup, structured evaluation, 384-dimensional embeddings, and mentor responses.
- No local model runtime, Ollama, SentenceTransformers, Torch, CUDA, TensorFlow, or GPU dependency.
- Bounded exponential retries for transient Gemini cleanup, evaluation, embedding, and mentor failures. OCR retains its per-page bounded retry policy.
- A validated nine-criterion 125-mark report whose total is calculated and checked in Python.
- PostgreSQL/pgvector persistence with user-scoped report, chat, message, and vector queries.
- Atomic evaluation, document-chunk, and chat-session persistence. SQLAlchemy relationships use database cascades correctly for user/evaluation cleanup.
- Bounded PDF size/page rendering, ordered OCR, unique run paths, cleanup fidelity protection, and failed-run cleanup.
- Local artifact storage by default and optional S3-compatible storage through the `s3` package extra.
- Native CPU-only installation through pinned `requirements.txt`; cross-platform dependency resolution remains in `uv.lock`.
- Native setup documentation for Python, Poppler, PostgreSQL/pgvector, migrations, Gemini, and startup.
- GitHub Actions checks for formatting, lint, offline tests, and dependency vulnerabilities, plus Dependabot configuration.
- Source formatting, secret boundaries, ignored runtime data, and a standalone repository structure.

## Verified release gate

| Check | Result |
| --- | --- |
| Fresh Python 3.12 pip environment | Passed from `requirements.txt`; package imports and `pip check` passed with Pillow 13.0.0 |
| GPU/local-model exclusion | Confirmed absent from runtime environment and lockfile |
| Offline tests | 22 passed; 1 opt-in database test skipped by default |
| Database integration | Passed against configured PostgreSQL; ownership, atomic bundle, message order, vector search, and ORM cascade cleanup verified inside a rollback |
| Ruff | Lint and format checks passed for source, tests, scripts, migrations, and entry point |
| Python compilation | Passed |
| Dependency audit | `pip-audit` found no known vulnerabilities |
| Static security scan | Bandit found no issues |
| Secret scan | No embedded API keys or private keys found; `.env` and runtime data are ignored |
| Alembic | History/offline SQL passed; a temporary fresh database migrated to `0001_initial` with pgcrypto, pgvector, all tables, and HNSW index, then was removed |
| Existing database safety | Schema inspected; it remains an unstamped legacy database and was not migrated or stamped |
| Poppler | Preflight passed |
| Live Gemini access | Generation models and `gemini-embedding-2` passed preflight |
| Full live Streamlit journey | Signup → login → synthetic PDF upload → OCR → cleanup → evaluation → 24 embeddings → atomic save → report → mentor → dashboard → reopen passed |
| Saved bundle | Exactly 1 evaluation, 24 chunks, 1 chat session, and 2 ordered messages; disposable user and artifacts were removed afterward |
| Streamlit process | Fresh pip environment started successfully; health endpoint returned HTTP 200 |

The complete live journey used a generated, non-personal synthetic essay. No historical student essay was transmitted during verification.

## Publishing

The application is ready for a Git remote. Before the first push, add the chosen GitHub remote and optionally add a license selected by the repository owner. Do not stage or publish files from the historical parent workspace.
