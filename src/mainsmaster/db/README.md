# Database layer

`models.py` defines five ORM entities, `session.py` owns connections and transaction scope, and `repositories.py` contains queries and writes. Scope evaluation, chat, message, and vector access by the user. Chat queries return the latest messages in chronological display order; new messages receive distinct application timestamps. `add_evaluation_bundle` writes the validated report, the student's cleaned OCR essay as `evaluation_json.original_essay`, chunks, and chat session in one transaction. New database schema lives in `migrations/`.
