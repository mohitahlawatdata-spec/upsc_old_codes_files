"""Optional PostgreSQL integration check; all synthetic writes are rolled back."""

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from mainsmaster.db.models import ChatSession, Document, Message, User
from mainsmaster.db.repositories import (
    add_evaluation_bundle,
    get_chat_session,
    get_evaluation,
    list_messages,
    search_chunks,
)
from mainsmaster.db.session import session_factory
from mainsmaster.schemas import COMMENT_LABELS, SCORE_MAXIMA, EvaluationReport


@pytest.mark.skipif(os.getenv("RUN_DB_TESTS") != "1", reason="requires configured PostgreSQL")
def test_evaluation_bundle_in_one_transaction() -> None:
    comment = "\n\n".join(f"{label}\nSynthetic feedback." for label in COMMENT_LABELS)
    report = EvaluationReport.model_validate(
        {
            "metadata": {"marks_obtained": 0},
            "topic": "Synthetic transaction test",
            "scores": {
                key: {"marks": maximum // 2, "comment": comment}
                for key, maximum in SCORE_MAXIMA.items()
            },
            "overall_feedback": "Synthetic feedback only.",
            "suggestions": ["First", "Second", "Third"],
            "improved_essay": "A synthetic essay.",
        }
    )
    with session_factory()() as session:
        try:
            user = User(username=f"codex-{uuid.uuid4()}@example.invalid", password_hash="unused")
            other = User(username=f"codex-{uuid.uuid4()}@example.invalid", password_hash="unused")
            session.add_all([user, other])
            session.flush()
            eval_id = add_evaluation_bundle(
                session,
                user.id,
                report,
                "A synthetic student essay.",
                [("Synthetic feedback chunk", [0.0] * 384)],
                1,
                2,
                3,
                4,
            )
            session.flush()
            saved = get_evaluation(session, user.id, eval_id)
            assert saved is not None
            assert saved.evaluation_json["original_essay"] == "A synthetic student essay."
            assert get_evaluation(session, other.id, eval_id) is None
            assert get_chat_session(session, other.id, eval_id) is None
            assert search_chunks(session, other.id, eval_id, [0.0] * 384) == []
            assert (
                session.scalar(select(ChatSession).where(ChatSession.evaluation_id == eval_id))
                is not None
            )
            assert (
                session.scalar(select(Document).where(Document.evaluation_id == eval_id))
                is not None
            )
            chat = get_chat_session(session, user.id, eval_id)
            timestamp = datetime.now(UTC)
            session.add_all(
                [
                    Message(session_id=chat.id, sender="user", text="first", created_at=timestamp),
                    Message(session_id=chat.id, sender="ai", text="second", created_at=timestamp),
                ]
            )
            session.flush()
            assert [message.text for message in list_messages(session, user.id, chat.id)] == [
                "first",
                "second",
            ]
            session.delete(user)
            session.flush()
            assert (
                session.scalar(select(func.count()).select_from(User).where(User.id == user.id))
                == 0
            )
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(Document)
                    .where(Document.evaluation_id == eval_id)
                )
                == 0
            )
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(ChatSession)
                    .where(ChatSession.evaluation_id == eval_id)
                )
                == 0
            )
            assert (
                session.scalar(
                    select(func.count()).select_from(Message).where(Message.session_id == chat.id)
                )
                == 0
            )
        finally:
            session.rollback()
