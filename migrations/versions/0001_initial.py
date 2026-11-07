"""Initial MainsMaster schema with pgvector."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "users",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_table(
        "evaluations",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("evaluation_title", sa.String(), nullable=False),
        sa.Column("evaluation_json", JSONB(), nullable=False),
        sa.Column("ocr_input_tokens", sa.Integer(), server_default="0"),
        sa.Column("ocr_output_tokens", sa.Integer(), server_default="0"),
        sa.Column("eval_input_tokens", sa.Integer(), server_default="0"),
        sa.Column("eval_output_tokens", sa.Integer(), server_default="0"),
    )
    op.create_index("ix_evaluations_user_id", "evaluations", ["user_id"])
    op.create_table(
        "documents",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evaluation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("evaluations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
    )
    op.create_index("ix_documents_user_evaluation", "documents", ["user_id", "evaluation_id"])
    op.execute(
        "CREATE INDEX ix_documents_embedding ON documents USING hnsw (embedding vector_l2_ops)"
    )
    op.create_table(
        "chat_sessions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evaluation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("evaluations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "evaluation_id", name="uq_chat_user_evaluation"),
    )
    op.create_table(
        "messages",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender", sa.String(50), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("sender IN ('user', 'ai')", name="ck_message_sender"),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("chat_sessions")
    op.drop_table("documents")
    op.drop_table("evaluations")
    op.drop_table("users")
