# Clean application guidance

This folder is a standalone application repository. Its runtime and verification instructions must not depend on files outside this directory.

## Map

- `streamlit_app.py`: Streamlit entry point.
- `src/mainsmaster/`: application package; see READMEs in `db/`, `services/`, and `ui/`.
- `migrations/`: Alembic schema for fresh PostgreSQL/pgvector.
- `scripts/`: preflight and optional live checks.
- `tests/`: offline tests and an opt-in database test.
- `.streamlit/`: Streamlit runtime settings.
- `var/`, `.venv/`, `.env`: ignored local runtime state.

## Change and verify

1. Read `README.md` for setup and `IMPLEMENTATION_STATUS.md` for proven versus pending work.
2. Keep provider SDK calls in `providers/`, processing policy in `services/`, artifact implementations in `storage/`, persistence in `db/`, flow coordination in `pipeline.py`, report validation in `schemas.py`, and presentation in `ui/`.
3. Keep configuration in `settings.py` and `.env.example`. Never add real credentials to examples, tests, logs, or docs.
4. Validate reports with `EvaluationReport`; its score total comes from nine criterion scores. Require `user_id` for evaluation, chat, and vector queries. Commit each evaluation bundle in one transaction.
5. Run `uv run pytest -q`, `uv run ruff check src scripts tests migrations streamlit_app.py`, and `uv pip check` from this folder's locked environment.
6. Do not claim release readiness until offline checks, a fresh database migration, and the full interactive signup-to-chat journey have been verified after the latest functional change.
