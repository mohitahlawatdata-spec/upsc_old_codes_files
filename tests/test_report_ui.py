"""The report must preserve and display both sides of the essay comparison."""

import json
import uuid

from streamlit.testing.v1 import AppTest

from mainsmaster.ui.report import essay_texts, find_previous_essay


def comparison_page() -> None:
    from mainsmaster.ui.report import render_essay_comparison

    stored = {
        "original_essay": "My original paragraph.",
        "improved_essay": "My **stronger** paragraph.",
    }
    render_essay_comparison(stored, "synthetic")


def test_essay_comparison_modes() -> None:
    app = AppTest.from_function(comparison_page)
    app.run()
    assert not app.exception
    assert [item.value for item in app.subheader] == [
        "Essay comparison",
        "Your essay",
        "Improved essay",
    ]
    assert app.radio[0].value == "Side by side"
    assert any("My original paragraph." in item.value for item in app.markdown)
    assert any("My **stronger** paragraph." in item.value for item in app.markdown)

    app.radio[0].set_value("Improved essay only").run()
    assert not app.exception
    assert [item.value for item in app.subheader] == ["Essay comparison", "Improved essay"]


def test_earlier_report_has_explicit_fallback() -> None:
    assert essay_texts({"improved_essay": "Saved improvement"}) == (None, "Saved improvement")


def test_older_report_recovers_only_matching_local_essay(tmp_path) -> None:
    run_output = tmp_path / str(uuid.uuid4()) / "output"
    run_output.mkdir(parents=True)
    (run_output / "3_final_evaluation.json").write_text(
        json.dumps({"topic": "A matched report", "improved_essay": "Improved"}), encoding="utf-8"
    )
    (run_output / "2_restructured_essay.txt").write_text("Original essay", encoding="utf-8")

    assert (
        find_previous_essay({"topic": "A matched report", "improved_essay": "Improved"}, tmp_path)
        == "Original essay"
    )
    assert find_previous_essay({"topic": "A different report"}, tmp_path) is None
