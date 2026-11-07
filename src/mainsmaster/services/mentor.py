"""Evaluation-scoped mentor response using configurable providers."""

import time
import uuid

from mainsmaster.db.repositories import (
    get_chat_session,
    get_evaluation,
    list_messages,
    search_chunks,
)
from mainsmaster.db.session import session_scope
from mainsmaster.diagnostics import logger, stage
from mainsmaster.providers.factory import embedding_provider, mentor_provider
from mainsmaster.services.embeddings import embed
from mainsmaster.settings import Settings


def answer_question(
    user_id: uuid.UUID, eval_id: uuid.UUID, question: str, settings: Settings
) -> str:
    started = time.monotonic()
    logger.info("MENTOR START retrieval")
    with stage("Mentor index compatibility check"), session_scope() as session:
        evaluation = get_evaluation(session, user_id, eval_id)
        if evaluation is None:
            raise PermissionError("Evaluation not found for this user")
        system = evaluation.evaluation_json.get("_system", {})
        indexed_provider = system.get("embedding_provider", "local")
        indexed_model = system.get("embedding_model", "all-MiniLM-L6-v2")
        if (indexed_provider, indexed_model) != (
            settings.embedding_provider,
            settings.embedding_model,
        ):
            raise RuntimeError(
                "This report was indexed with a different embedding provider; "
                "re-index it before using mentor chat"
            )
        chat = get_chat_session(session, user_id, eval_id)
        if chat is None:
            raise PermissionError("Evaluation chat not found for this user")
        chat_id = chat.id
    embedder = embedding_provider(settings)
    with stage("Mentor question embedding"):
        query_vector = embed(question, settings, embedder)
    with stage("Mentor database retrieval"), session_scope() as session:
        documents = search_chunks(session, user_id, eval_id, query_vector)
        history = list_messages(session, user_id, chat_id, limit=6)
    logger.info(
        "MENTOR DONE retrieval in %.1fs; chunks: %d; history messages: %d",
        time.monotonic() - started,
        len(documents),
        len(history),
    )
    context = "\n\n".join(document.content for document in documents)
    previous = "\n".join(
        f"{'Student' if message.sender == 'user' else 'Mentor'}: {message.text}"
        for message in history
    )
    provider = mentor_provider(settings)
    logger.info("MENTOR START %s response", settings.mentor_provider)
    response_started = time.monotonic()
    with stage(f"Mentor {settings.mentor_provider} request"):
        answer = provider.answer(context, previous, question).strip()
    if not answer:
        raise RuntimeError("Mentor provider returned an empty response")
    logger.info("MENTOR DONE response in %.1fs", time.monotonic() - response_started)
    return answer
