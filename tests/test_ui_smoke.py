"""The Streamlit login page should render without a database connection."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_login_page_renders_without_connecting(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@127.0.0.1:65432/unused")
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"))
    app.run(timeout=60)
    assert not app.exception
    assert any("MainsMaster" in title.value for title in app.title)
