# Application package

`settings.py` validates environment-backed profiles, `schemas.py` validates the 125-mark report, `prompts.py` holds model instructions, `pipeline.py` coordinates processing, durable artifact publication, and one database commit, and `diagnostics.py` logs stages. `providers/` isolates Gemini SDK calls, `storage/` isolates local/S3-compatible artifacts, `services/` holds processing policy, `db/` owns persistence, and `ui/` presents the Streamlit workflow. Imports must not open a database connection or call a provider.
