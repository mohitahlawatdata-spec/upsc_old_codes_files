# Operational scripts

`preflight.py` checks configuration, PostgreSQL/pgvector, Poppler, and only the providers selected in settings. `--live-gemini` calls configured Gemini generation and embedding models. `smoke_pipeline.py` runs PDF through report generation without a database write and stores output under ignored local workspace. Live checks require configured services and may consume API quota.
