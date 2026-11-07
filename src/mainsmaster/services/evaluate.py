"""Gemini essay evaluation and local report validation."""

from dataclasses import dataclass

from google import genai
from google.genai import types

from mainsmaster.diagnostics import stage
from mainsmaster.prompts import EVALUATION_PROMPT
from mainsmaster.providers.retry import retry_provider_call
from mainsmaster.schemas import EvaluationReport
from mainsmaster.settings import Settings


@dataclass(frozen=True)
class EvaluationResult:
    report: EvaluationReport
    input_tokens: int
    output_tokens: int


def evaluate_essay(question: str, answer: str, settings: Settings) -> EvaluationResult:
    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is missing")
    client = genai.Client(api_key=settings.google_api_key)
    try:
        with stage("Gemini evaluation request"):
            response = retry_provider_call(
                lambda: client.models.generate_content(
                    model=settings.eval_model,
                    contents=EVALUATION_PROMPT.format(topic=question, essay_text=answer),
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=EvaluationReport,
                        temperature=0.2,
                        max_output_tokens=16000,
                    ),
                ),
                "Gemini evaluation",
            )
    finally:
        client.close()
    if not response.text:
        raise RuntimeError("Gemini returned an empty evaluation")
    with stage("Evaluation JSON validation"):
        report = EvaluationReport.model_validate_json(response.text)
    usage = response.usage_metadata
    return EvaluationResult(
        report=report,
        input_tokens=int(getattr(usage, "prompt_token_count", 0) or 0),
        output_tokens=int(getattr(usage, "candidates_token_count", 0) or 0),
    )
