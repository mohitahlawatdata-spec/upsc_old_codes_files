"""The restructuring stage must preserve the student's words and ideas."""

import asyncio

from mainsmaster.services.restructure import preserves_student_text
from mainsmaster.settings import get_settings


def test_allows_paragraph_joining_and_small_typo_fix() -> None:
    original = "People should work together.\n\nThis helps solve hard problmes."
    candidate = "People should work together. This helps solve hard problems."
    assert preserves_student_text(original, candidate)


def test_rejects_added_examples() -> None:
    original = "People should work together. This helps solve hard problems."
    candidate = (
        original + " For example, engineers and scientists can share skills and solve "
        "complex global challenges through teamwork."
    )
    assert not preserves_student_text(original, candidate)


def test_provider_failure_uses_ocr_text() -> None:
    class FailingClient:
        async def clean(self, text: str) -> str:
            raise TimeoutError("model took too long")

    original = "The student's OCR text must remain available."
    from mainsmaster.services.restructure import restructure_essay

    assert asyncio.run(restructure_essay(original, get_settings(), FailingClient())) == original
