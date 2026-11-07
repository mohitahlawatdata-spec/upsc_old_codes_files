"""Report scoring must not trust arithmetic supplied by the model."""

import pytest
from pydantic import ValidationError

from mainsmaster.schemas import (
    SCORE_MAXIMA,
    TOTAL_MARKS,
    EvaluationReport,
    criterion_blocks,
    rag_chunks,
)

COMMENT = (
    "**What was good:**\nClear opening.\n\n"
    "**Area for Development:**\nThe argument needs a stronger link.\n\n"
    "**Old Line:**\nAn old sentence.\n\n"
    "**Improved Line:**\nA clearer sentence.\n\n"
    "**Why it matters:**\nThe examiner needs a clear claim.\n\n"
    "**Actionable next step:**\nWrite a link sentence."
)


def sample_report() -> dict:
    return {
        "metadata": {"marks_obtained": 1, "total_marks": 100},
        "topic": "A synthetic topic",
        "scores": {
            key: {"marks": maximum, "comment": COMMENT} for key, maximum in SCORE_MAXIMA.items()
        },
        "overall_feedback": "A clear essay with room to improve.",
        "suggestions": ["Improve the opening", "Add evidence", "Tighten the conclusion"],
        "improved_essay": "A short improved essay.",
        "suggested_questions": [],
    }


def test_total_is_computed_from_criteria() -> None:
    report = EvaluationReport.model_validate(sample_report())
    assert report.metadata.marks_obtained == TOTAL_MARKS == 125
    assert report.metadata.total_marks == 125
    assert "additionalProperties" not in str(EvaluationReport.model_json_schema())


def test_rejects_missing_or_excessive_scores() -> None:
    missing = sample_report()
    del missing["scores"]["understanding"]
    with pytest.raises(ValidationError):
        EvaluationReport.model_validate(missing)

    excessive = sample_report()
    excessive["scores"]["examples"]["marks"] = 21
    with pytest.raises(ValidationError):
        EvaluationReport.model_validate(excessive)


def test_comment_blocks_and_rag_chunks() -> None:
    blocks = criterion_blocks(COMMENT)
    assert blocks["**Area for Development:**"] == "The argument needs a stronger link."
    chunks = rag_chunks(EvaluationReport.model_validate(sample_report()))
    assert any("Actionable next step" in chunk for chunk in chunks)
