# Processing services

`pdf.py` validates and renders bounded uploads. `ocr.py` extracts ordered page text with Gemini. `restructure.py`, `embeddings.py`, and `mentor.py` consume provider interfaces backed by Gemini. `evaluate.py` requests a structured Gemini report. Keep processing policy and retry/error handling here; provider SDK details belong in `providers/`.
