"""Validated output contracts for essay evaluation."""

from typing import Any

from pydantic import BaseModel, Field, model_validator

SCORE_MAXIMA = {
    "understanding": 15,
    "examples": 20,
    "language_clarity": 10,
    "introduction": 15,
    "structure_flow": 10,
    "conclusion": 10,
    "relevance": 15,
    "multiple_perspectives": 20,
    "creativity_presentation": 10,
}
TOTAL_MARKS = sum(SCORE_MAXIMA.values())
COMMENT_LABELS = (
    "**What was good:**",
    "**Area for Development:**",
    "**Old Line:**",
    "**Improved Line:**",
    "**Why it matters:**",
    "**Actionable next step:**",
)


class CriterionScore(BaseModel):
    marks: int = Field(ge=0)
    comment: str = Field(min_length=1)


class ScoreCard(BaseModel):
    understanding: CriterionScore
    examples: CriterionScore
    language_clarity: CriterionScore
    introduction: CriterionScore
    structure_flow: CriterionScore
    conclusion: CriterionScore
    relevance: CriterionScore
    multiple_perspectives: CriterionScore
    creativity_presentation: CriterionScore

    def items(self):
        return ((key, getattr(self, key)) for key in SCORE_MAXIMA)

    def values(self):
        return (getattr(self, key) for key in SCORE_MAXIMA)


class ReportMetadata(BaseModel):
    marks_obtained: int = 0
    total_marks: int = TOTAL_MARKS
    exam_year: int | None = None
    language: str | None = None
    topic: str | None = None
    word_count: int | None = None
    paragraph_count: int | None = None
    category: str | None = None
    difficulty_level: str | None = None
    context: list[str] = Field(default_factory=list)
    feedback_readability_score: int | None = None
    feedback_length: int | None = None


class SuggestedQuestion(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class EvaluationReport(BaseModel):
    metadata: ReportMetadata
    topic: str = Field(min_length=1)
    scores: ScoreCard
    overall_feedback: str = Field(min_length=1)
    suggestions: list[str] = Field(min_length=3, max_length=3)
    improved_essay: str = Field(min_length=1)
    category: str | None = None
    suggested_questions: list[SuggestedQuestion] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scores(self) -> "EvaluationReport":
        for key, maximum in SCORE_MAXIMA.items():
            score = getattr(self.scores, key)
            if score.marks > maximum:
                raise ValueError(f"{key} exceeds {maximum} marks")
            missing_labels = [label for label in COMMENT_LABELS if label not in score.comment]
            if missing_labels:
                raise ValueError(f"{key} is missing feedback section(s): {missing_labels}")
        self.metadata.marks_obtained = sum(score.marks for score in self.scores.values())
        self.metadata.total_marks = TOTAL_MARKS
        self.metadata.topic = self.topic
        return self


def criterion_blocks(comment: str) -> dict[str, str]:
    """Split the existing six-section feedback format for the report and RAG."""
    result: dict[str, str] = {}
    for index, label in enumerate(COMMENT_LABELS):
        start = comment.find(label)
        if start < 0:
            result[label] = ""
            continue
        value_start = start + len(label)
        next_starts = [
            comment.find(next_label, value_start) for next_label in COMMENT_LABELS[index + 1 :]
        ]
        valid_ends = [position for position in next_starts if position >= 0]
        result[label] = comment[value_start : min(valid_ends) if valid_ends else None].strip()
    return result


def rag_chunks(report: EvaluationReport) -> list[str]:
    chunks = [
        f"Topic: {report.topic}",
        f"Overall score: {report.metadata.marks_obtained}/{TOTAL_MARKS}",
        f"Overall feedback: {report.overall_feedback}",
    ]
    chunks.extend(f"Suggestion: {suggestion}" for suggestion in report.suggestions)
    for key, score in report.scores.items():
        blocks = criterion_blocks(score.comment)
        for label in ("**Area for Development:**", "**Actionable next step:**"):
            if blocks[label]:
                chunks.append(f"{key} {label.strip('*:')}: {blocks[label]}")
    return chunks


def report_dict(report: EvaluationReport) -> dict[str, Any]:
    return report.model_dump(mode="json")
