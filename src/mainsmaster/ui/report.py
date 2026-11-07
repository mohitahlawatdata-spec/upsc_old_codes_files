"""Essay comparison and report-only presentation helpers."""

import json
import uuid
from pathlib import Path

import streamlit as st


def essay_texts(stored_report: dict) -> tuple[str | None, str]:
    """Read display text without asking the scoring model to invent the source essay."""
    original = stored_report.get("original_essay")
    improved = stored_report.get("improved_essay", "")
    return (original if isinstance(original, str) and original.strip() else None, improved)


def find_previous_essay(stored_report: dict, user_data_dir: Path) -> str | None:
    """Recover an older report's source only from an exact matching local run artifact."""
    if essay_texts(stored_report)[0] is not None or not user_data_dir.is_dir():
        return None
    root = user_data_dir.resolve()
    matches: list[str] = []
    for report_file in user_data_dir.glob("*/output/3_final_evaluation.json"):
        try:
            uuid.UUID(report_file.parent.parent.name)
            source_file = report_file.with_name("2_restructured_essay.txt")
            if not report_file.resolve().is_relative_to(root):
                continue
            if not source_file.resolve().is_relative_to(root):
                continue
            if json.loads(report_file.read_text(encoding="utf-8")) != stored_report:
                continue
            source = source_file.read_text(encoding="utf-8").strip()
            if source:
                matches.append(source)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return matches[0] if len(matches) == 1 else None


def _essay_panel(title: str, text: str) -> None:
    st.subheader(title)
    with st.container(height=560, border=True):
        st.markdown(text)


def render_essay_comparison(
    stored_report: dict, evaluation_id: str, previous_essay: str | None = None
) -> None:
    """Show the transcribed student essay beside the model's inline edits."""
    original, improved = essay_texts(stored_report)
    original = original or previous_essay
    st.subheader("Essay comparison")
    if original is None:
        st.info(
            "The transcribed essay was not saved with this earlier report. New reports include it."
        )
        _essay_panel("Improved essay", improved)
        return

    st.caption(
        "Your essay is the cleaned OCR transcription used for scoring. Bold text in the improved essay marks the model's suggested additions."
    )
    mode = st.radio(
        "View",
        ("Side by side", "Your essay only", "Improved essay only"),
        horizontal=True,
        key=f"essay_comparison_{evaluation_id}",
    )
    if mode == "Side by side":
        original_column, improved_column = st.columns(2)
        with original_column:
            _essay_panel("Your essay", original)
        with improved_column:
            _essay_panel("Improved essay", improved)
    elif mode == "Your essay only":
        _essay_panel("Your essay", original)
    else:
        _essay_panel("Improved essay", improved)
