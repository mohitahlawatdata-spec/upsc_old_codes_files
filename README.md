# MainsMaster clean app

MainsMaster is a clean, portable rebuild of the UPSC essay evaluator. Historical notebooks, sample essays, generated data, and credentials are not part of this application repository.

For project context and assistant guidance, start with [`AGENTS.md`](AGENTS.md). Each source, migration, script, test, and configuration directory has a short `README.md` describing its responsibility. The root `CLAUDE.md` points to the same guidance, so tools can share one project map.

## What it does

Create an account, upload a handwritten essay PDF, extract page text with Gemini, repair paragraph flow with Gemini, receive a 125-mark Gemini report, and ask a Gemini mentor questions grounded in that report. Reports and chat history are stored in PostgreSQL with pgvector. Gemini embeddings keep retrieval portable. All AI inference is API-backed.

The report shows a side-by-side comparison of the student's cleaned OCR essay and the improved essay, with single-essay display options. New evaluations save both texts in the report JSON for reopening. Earlier clean-app reports can recover the student text when their local processing artifacts exactly match the stored report. The mentor tab retains the evaluation-scoped RAG chat.

## Requirements

- Python 3.12. A standard `requirements.txt` is included for CPU-only installation with `pip`.
- PostgreSQL with the pgvector extension, either on the same machine or reachable over the network.
- Poppler utilities (`pdfinfo` and `pdftoppm`) on `PATH`, or set `POPPLER_PATH` to their directory.
- One Gemini API key for OCR, cleanup, evaluation, embeddings, and mentor chat. Create one in [Google AI Studio](https://aistudio.google.com/app/apikey).

No GPU is required. The default installation does not include PyTorch, CUDA, TensorFlow, SentenceTransformers, or Ollama. Gemini performs all model inference remotely; the local CPU handles Streamlit, PDF rendering, validation, and database access.

The database driver is Psycopg 3 (`postgresql+psycopg://`), matching the existing local configuration.

Create a new environment **inside the cloned repository**.

See [`docs/NATIVE_SETUP.md`](docs/NATIVE_SETUP.md) for the complete cross-machine setup, including PostgreSQL/pgvector and Poppler.

## Setup (PowerShell)

Create a new environment inside the project on each machine and install the pinned CPU-only dependencies:

```powershell
cd path\to\mainsmaster
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set this value; do not add quotes or commit the file:

```dotenv
GOOGLE_API_KEY=your_google_ai_studio_key
```

Set `DATABASE_URL` to your PostgreSQL/pgvector server. The remaining defaults use Gemini for every AI stage, work across machines, and do not require a downloaded model.

The database commands below apply to a **fresh local database**. If you point `DATABASE_URL` at an existing database, run preflight and compare its schema before using Alembic. Do not run `alembic upgrade head` or `alembic stamp head` on existing data without that review.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe scripts/preflight.py
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Open `http://127.0.0.1:8501`. Run the Alembic command only for a fresh database whose schema you have checked. Do not migrate or stamp an existing database without reviewing and backing it up.

Use `scripts/preflight.py --live-gemini` to test the configured Gemini models. This flag sends small requests and consumes quota. Ordinary preflight checks key presence without making provider calls.

## Files and data

- `streamlit_app.py` is the UI entry point.
- `requirements.txt` is the pinned CPU-only runtime install for ordinary Python virtual environments.
- `src/mainsmaster/` contains settings, validated report contracts, the pipeline, services, database access, and UI.
- `migrations/` is the database schema source. Run `alembic upgrade head` on a fresh database.
- `var/data/<user UUID>/<run UUID>/` is temporary/local artifact space and is Git-ignored.
- Artifact storage defaults to local files. S3-compatible production storage is available with `pip install -e ".[s3]"`.
- `.env` contains local configuration and is Git-ignored. Do not put real credentials in `.env.example`.

## Tests

Runtime users do not need test tools. Developers can install them with `pip install -e ".[dev]"` or use the locked `uv` workflow:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check src tests scripts migrations streamlit_app.py
```

The default tests do not call Gemini or PostgreSQL. Live checks remain opt-in because they consume API quota or use a configured database.

The terminal shows timestamped `START`, `DONE`, and `FAILED` events for rendering, OCR, provider-based cleanup, evaluation, embedding, artifact publication, database persistence, and mentor calls. A parent duration includes nested stages and concurrent OCR calls overlap. Logs report counts and timings without essay text, chat messages, or credentials.

The optional database integration test uses a configured PostgreSQL server, inserts synthetic rows in one transaction, and rolls them back:

```powershell
$env:RUN_DB_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_db_integration.py
Remove-Item Env:RUN_DB_TESTS
```

To check the processing stages without writing to PostgreSQL, run `python scripts/smoke_pipeline.py path/to/sample.pdf`. It uses the configured providers and writes artifacts only under ignored local workspace. After changing dependencies, run `uv lock` and commit `uv.lock`.

## Current verification status

The release gate and its latest results are recorded in `IMPLEMENTATION_STATUS.md`. It distinguishes offline checks, fresh-database verification, and opt-in live Gemini/UI checks.
