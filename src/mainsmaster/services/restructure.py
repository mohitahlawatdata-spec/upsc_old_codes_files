"""Repair OCR paragraph flow through a replaceable provider."""

import logging
import re
from difflib import SequenceMatcher

from mainsmaster.diagnostics import stage
from mainsmaster.providers.base import CleanupProvider
from mainsmaster.providers.factory import cleanup_provider
from mainsmaster.settings import Settings

logger = logging.getLogger(__name__)


def preserves_student_text(original: str, candidate: str) -> bool:
    """Reject substantial additions, omissions, or paraphrasing by the model."""
    source_words = re.findall(r"\w+", original.casefold())
    output_words = re.findall(r"\w+", candidate.casefold())
    if not source_words or not output_words:
        return False
    if len(output_words) > len(source_words) * 1.15 + 3:
        return False
    if len(output_words) < len(source_words) * 0.85 - 3:
        return False
    return SequenceMatcher(None, source_words, output_words, autojunk=False).ratio() >= 0.85


async def restructure_essay(
    answer: str, settings: Settings, provider: CleanupProvider | None = None
) -> str:
    if not answer.strip():
        raise ValueError("OCR produced no essay text")
    selected = provider or cleanup_provider(settings)
    try:
        with stage(f"{settings.cleanup_provider} restructuring request"):
            text = (await selected.clean(answer)).strip()
    except Exception as exc:  # noqa: BLE001 - optional cleanup must not block evaluation
        logger.warning("Restructuring unavailable (%s); using OCR text", type(exc).__name__)
        return answer
    if not text:
        logger.warning("Restructuring returned empty text; using OCR text")
        return answer
    with stage("Restructured text fidelity check"):
        preserves_text = preserves_student_text(answer, text)
    if not preserves_text:
        logger.warning("Restructuring changed the essay substantially; using OCR text")
        return answer
    return text
