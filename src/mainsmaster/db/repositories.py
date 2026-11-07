"""Database operations that enforce user ownership."""

import uuid
from datetime import UTC, datetime

from passlib.context import CryptContext
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from mainsmaster.db.models import ChatSession, Document, Evaluation, Message, User
from mainsmaster.diagnostics import logger, stage
from mainsmaster.schemas import EvaluationReport, report_dict

password_context = CryptContext(schemes=["argon2"], deprecated="auto")


def create_user(session: Session, username: str, password: str) -> User:
    user = User(username=username.strip().lower(), password_hash=password_context.hash(password))
    session.add(user)
    session.flush()
    return user


def authenticate(session: Session, username: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.username == username.strip().lower()))
    if user and password_context.verify(password, user.password_hash):
        return user
    return None


def user_exists(session: Session, username: str) -> bool:
    return (
        session.scalar(select(User.id).where(User.username == username.strip().lower())) is not None
    )


def list_evaluations(session: Session, user_id: uuid.UUID) -> list[Evaluation]:
    return list(
        session.scalars(
            select(Evaluation)
            .where(Evaluation.user_id == user_id)
            .order_by(Evaluation.created_at.desc())
        )
    )


def get_evaluation(session: Session, user_id: uuid.UUID, eval_id: uuid.UUID) -> Evaluation | None:
    return session.scalar(
        select(Evaluation).where(Evaluation.id == eval_id, Evaluation.user_id == user_id)
    )


def get_chat_session(
    session: Session, user_id: uuid.UUID, eval_id: uuid.UUID
) -> ChatSession | None:
    return session.scalar(
        select(ChatSession).where(
            ChatSession.user_id == user_id, ChatSession.evaluation_id == eval_id
        )
    )


def list_messages(
    session: Session, user_id: uuid.UUID, chat_id: uuid.UUID, limit: int = 20
) -> list[Message]:
    chat = session.scalar(
        select(ChatSession.id).where(ChatSession.id == chat_id, ChatSession.user_id == user_id)
    )
    if chat is None:
        raise PermissionError("Chat session not found for this user")
    # Reverse the latest N messages for display. Existing user/AI pairs share a
    # transaction timestamp, so put AI first in descending order before reversing.
    items = session.scalars(
        select(Message)
        .where(Message.session_id == chat_id)
        .order_by(
            Message.created_at.desc(),
            case((Message.sender == "ai", 1), else_=0).desc(),
        )
        .limit(limit)
    )
    return list(items)[::-1]


def add_message(
    session: Session, user_id: uuid.UUID, chat_id: uuid.UUID, sender: str, text: str
) -> Message:
    chat = session.scalar(
        select(ChatSession.id).where(ChatSession.id == chat_id, ChatSession.user_id == user_id)
    )
    if chat is None:
        raise PermissionError("Chat session not found for this user")
    if sender not in {"user", "ai"}:
        raise ValueError("Invalid sender")
    message = Message(
        session_id=chat_id,
        sender=sender,
        text=text,
        created_at=datetime.now(UTC),
    )
    session.add(message)
    session.flush()
    return message


def search_chunks(
    session: Session,
    user_id: uuid.UUID,
    eval_id: uuid.UUID,
    query_embedding: list[float],
    limit: int = 4,
) -> list[Document]:
    return list(
        session.scalars(
            select(Document)
            .where(Document.user_id == user_id, Document.evaluation_id == eval_id)
            .order_by(Document.embedding.l2_distance(query_embedding))
            .limit(limit)
        )
    )


def add_evaluation_bundle(
    session: Session,
    user_id: uuid.UUID,
    report: EvaluationReport,
    original_essay: str,
    chunks: list[tuple[str, list[float]]],
    ocr_input_tokens: int,
    ocr_output_tokens: int,
    eval_input_tokens: int,
    eval_output_tokens: int,
    system_metadata: dict | None = None,
) -> uuid.UUID:
    stored_report = report_dict(report)
    stored_report["original_essay"] = original_essay
    if system_metadata:
        stored_report["_system"] = system_metadata
    evaluation = Evaluation(
        user_id=user_id,
        evaluation_title=report.topic,
        evaluation_json=stored_report,
        ocr_input_tokens=ocr_input_tokens,
        ocr_output_tokens=ocr_output_tokens,
        eval_input_tokens=eval_input_tokens,
        eval_output_tokens=eval_output_tokens,
    )
    with stage("Database insert evaluation"):
        session.add(evaluation)
        session.flush()
    with stage("Database insert mentor chunks"):
        session.add_all(
            Document(
                user_id=user_id, evaluation_id=evaluation.id, content=content, embedding=vector
            )
            for content, vector in chunks
        )
        session.flush()
        logger.info("Database chunks inserted: %d", len(chunks))
    with stage("Database insert chat session"):
        session.add(
            ChatSession(user_id=user_id, evaluation_id=evaluation.id, session_name=report.topic)
        )
        session.flush()
    return evaluation.id
