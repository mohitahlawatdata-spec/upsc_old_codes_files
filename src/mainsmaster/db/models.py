"""SQLAlchemy tables shared by the app and Alembic."""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    evaluation_title: Mapped[str] = mapped_column(String)
    evaluation_json: Mapped[dict] = mapped_column(JSONB)
    ocr_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    ocr_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    eval_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    eval_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    user: Mapped[User] = relationship(back_populates="evaluations")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="evaluation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chat_session: Mapped["ChatSession"] = relationship(
        back_populates="evaluation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(String)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    evaluation: Mapped[Evaluation] = relationship(back_populates="documents")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (UniqueConstraint("user_id", "evaluation_id", name="uq_chat_user_evaluation"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE")
    )
    session_name: Mapped[str] = mapped_column(String)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    evaluation: Mapped[Evaluation] = relationship(back_populates="chat_session")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (CheckConstraint("sender IN ('user', 'ai')", name="ck_message_sender"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    sender: Mapped[str] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(String)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    chat_session: Mapped[ChatSession] = relationship(back_populates="messages")
