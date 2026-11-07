# AI providers

`base.py` defines the cleanup, embedding, and mentor contracts used by the pipeline. `factory.py` selects implementations from validated settings. `gemini.py` supplies portable API-backed cleanup, embeddings, and mentor responses using the same Google API key as OCR and evaluation. `noop.py` preserves OCR text when cleanup is intentionally disabled. No local model runtime is required or supported.

Provider modules translate SDK responses. Fidelity checks, retrieval policy, report validation, and business rules stay in `services/` and `schemas.py` so another API can be benchmarked without rewriting the pipeline.
