# Database migrations

Alembic uses `env.py` and revisions in `versions/`. `0001_initial.py` creates pgvector and five application tables for a fresh PostgreSQL database. Run `alembic upgrade head` only against a fresh or reviewed database. The configured legacy database has no Alembic version marker and has not been migrated by this rebuild.
