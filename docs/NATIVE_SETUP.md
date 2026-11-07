# Native setup without Docker or a GPU

MainsMaster runs on ordinary CPU-only Windows, macOS, or Linux machines. Gemini performs OCR, cleanup, evaluation, embeddings, and mentor generation remotely. The local machine needs Python, Poppler, network access, and a PostgreSQL server with pgvector.

## 1. System prerequisites

- Install Python 3.12 and confirm `python --version` or `py -3.12 --version`.
- Install Poppler utilities. Confirm both `pdfinfo` and `pdftoppm` are on `PATH`, or set `POPPLER_PATH` in `.env` to the directory containing them.
- Create or obtain an empty PostgreSQL database whose server supports the `vector` extension. The Python `pgvector` package does not install the PostgreSQL server extension.
- Create a Gemini API key in Google AI Studio.

A hosted PostgreSQL/pgvector database is the simplest way to share one database between machines. A local PostgreSQL installation is also supported when pgvector is installed server-side.

## 2. Clone and install

```powershell
git clone <repository-url>
cd mainsmaster
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

On macOS or Linux, activate `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

## 3. Configure secrets

Edit the ignored `.env` file:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
GOOGLE_API_KEY=your_google_ai_studio_key
```

Percent-encode reserved characters in the database username or password. Never commit `.env`.

## 4. Initialize only a fresh database

The baseline migration creates `pgcrypto`, `vector`, five application tables, and the vector index. The database role must be allowed to create those extensions, or an administrator/provider dashboard must enable them first.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Do not run or stamp migrations against an existing database until its schema is inspected and its data is backed up.

## 5. Verify and run

```powershell
.\.venv\Scripts\python.exe scripts\preflight.py
.\.venv\Scripts\python.exe scripts\preflight.py --live-gemini
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Open `http://127.0.0.1:8501`.

## Optional S3-compatible artifact storage

Local artifact storage is the default. To use Cloudflare R2, AWS S3, or another S3-compatible store, install the optional dependency and configure the `S3_*` variables from `.env.example`:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[s3]"
```
