"""Streamlit views for the clean MainsMaster app."""

import asyncio
import shutil
import time
import uuid
from pathlib import Path

import streamlit as st

from mainsmaster.db import repositories as repo
from mainsmaster.db.session import session_scope
from mainsmaster.diagnostics import logger, stage
from mainsmaster.pipeline import run_pipeline
from mainsmaster.schemas import TOTAL_MARKS, EvaluationReport, criterion_blocks
from mainsmaster.services.mentor import answer_question
from mainsmaster.services.pdf import save_uploaded_pdf
from mainsmaster.settings import Settings, get_settings
from mainsmaster.ui.report import find_previous_essay, render_essay_comparison


def _user_id() -> uuid.UUID:
    return uuid.UUID(st.session_state.user["id"])


def _go(view: str) -> None:
    st.session_state.view = view
    st.rerun()


def login_view() -> None:
    st.title("MainsMaster")
    st.caption("UPSC essay evaluation and mentor")
    login_tab, signup_tab = st.tabs(["Log in", "Create account"])
    with login_tab, st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log in"):
            try:
                with session_scope() as session:
                    user = repo.authenticate(session, email, password)
                    identity = {"id": str(user.id), "username": user.username} if user else None
                if identity:
                    st.session_state.user = identity
                    _go("dashboard")
                else:
                    st.error("Invalid email or password")
            except Exception as exc:
                st.error(f"Database unavailable: {exc}")
    with signup_tab, st.form("signup"):
        new_email = st.text_input("New email")
        new_password = st.text_input("New password", type="password")
        if st.form_submit_button("Create account"):
            if "@" not in new_email or "." not in new_email.rsplit("@", 1)[-1]:
                st.error("Enter a valid email address")
            elif len(new_password) < 8:
                st.error("Use a password of at least 8 characters")
            else:
                try:
                    with session_scope() as session:
                        if repo.user_exists(session, new_email):
                            st.error("Account already exists")
                        else:
                            repo.create_user(session, new_email, new_password)
                            st.success("Account created. You can log in now.")
                except Exception as exc:
                    st.error(f"Could not create account: {exc}")


def dashboard_view() -> None:
    st.title(f"Welcome, {st.session_state.user['username']}")
    left, right = st.columns(2)
    if left.button("New evaluation", use_container_width=True):
        _go("upload")
    if right.button("Log out", use_container_width=True):
        st.session_state.user = None
        st.session_state.selected_eval_id = None
        _go("login")
    st.subheader("Past evaluations")
    with session_scope() as session:
        evaluations = repo.list_evaluations(session, _user_id())
        rows = [(item.id, item.evaluation_title, item.created_at) for item in evaluations]
    if not rows:
        st.info("No evaluations yet.")
    for eval_id, title, created in rows:
        with st.container(border=True):
            label, button = st.columns([4, 1])
            label.write(f"{title} · {created:%Y-%m-%d}")
            if button.button("Open", key=str(eval_id)):
                st.session_state.selected_eval_id = str(eval_id)
                _go("report")


def _remove_failed_run(run_dir: Path, settings: Settings) -> None:
    root = settings.data_dir.resolve()
    target = run_dir.resolve()
    if target.is_relative_to(root) and target != root and target.exists():
        shutil.rmtree(target)


def upload_view(settings: Settings) -> None:
    if st.button("Back to dashboard"):
        _go("dashboard")
    st.title("Upload essay PDF")
    uploaded = st.file_uploader("Choose a PDF", type="pdf")
    if uploaded is None or not st.button("Analyze essay"):
        return
    run_dir = settings.data_dir / str(_user_id()) / str(uuid.uuid4())
    current_stage = "saving the upload"
    try:
        logger.info("UPLOAD START; size: %d bytes", uploaded.size)
        pdf_path = save_uploaded_pdf(uploaded.getvalue(), run_dir / "input.pdf", settings)
        logger.info("UPLOAD DONE")
        with st.status("Processing essay", expanded=True) as status:

            def show_progress(stage: str) -> None:
                nonlocal current_stage
                current_stage = stage
                status.write(stage)

            with stage("Full evaluation run"):
                eval_id = asyncio.run(
                    run_pipeline(_user_id(), pdf_path, run_dir, settings, progress=show_progress)
                )
            status.update(label="Evaluation complete", state="complete")
    except Exception as exc:
        logger.error("UPLOAD FAILED during %s (%s)", current_stage, type(exc).__name__)
        _remove_failed_run(run_dir, settings)
        st.error(f"Evaluation failed while {current_stage}: {exc}")
        return
    st.session_state.selected_eval_id = str(eval_id)
    _go("report")


def report_view(settings: Settings) -> None:
    if st.button("Back to dashboard"):
        _go("dashboard")
    if not st.session_state.selected_eval_id:
        st.error("Choose an evaluation from the dashboard")
        return
    eval_id = uuid.UUID(st.session_state.selected_eval_id)
    with session_scope() as session:
        evaluation = repo.get_evaluation(session, _user_id(), eval_id)
        if evaluation is None:
            st.error("Evaluation not found")
            return
        stored_report = evaluation.evaluation_json
        report = EvaluationReport.model_validate(stored_report)
        chat = repo.get_chat_session(session, _user_id(), eval_id)
        messages = repo.list_messages(session, _user_id(), chat.id) if chat else []
    st.title(report.topic)
    report_tab, chat_tab = st.tabs(["Report", "Mentor chat"])
    with report_tab:
        st.metric("Total marks", f"{report.metadata.marks_obtained} / {TOTAL_MARKS}")
        st.markdown(report.overall_feedback)
        st.subheader("Criterion scores")
        for key, score in report.scores.items():
            with st.expander(f"{key.replace('_', ' ').title()}: {score.marks}"):
                for label, body in criterion_blocks(score.comment).items():
                    if body:
                        st.markdown(f"{label}\n\n{body}")
        st.subheader("Suggestions")
        for suggestion in report.suggestions:
            st.markdown(f"- {suggestion}")
        st.divider()
        previous_essay = find_previous_essay(stored_report, settings.data_dir / str(_user_id()))
        render_essay_comparison(stored_report, str(eval_id), previous_essay)
        if report.suggested_questions:
            st.subheader("Questions to explore")
            for item in report.suggested_questions:
                with st.expander(item.question):
                    st.markdown(item.answer)
    with chat_tab:
        if chat is None:
            st.warning("Mentor chat is unavailable for this evaluation")
            return
        for message in messages:
            role = "assistant" if message.sender == "ai" else "user"
            st.chat_message(role).write(message.text)
        question = st.chat_input("Ask about your feedback")
        if question:
            try:
                with st.spinner("Thinking..."):
                    answer = answer_question(_user_id(), eval_id, question, settings)
                logger.info("MENTOR START saving messages")
                save_started = time.monotonic()
                with session_scope() as session:
                    repo.add_message(session, _user_id(), chat.id, "user", question)
                    repo.add_message(session, _user_id(), chat.id, "ai", answer)
                logger.info("MENTOR DONE saving messages in %.1fs", time.monotonic() - save_started)
                st.rerun()
            except Exception as exc:
                st.error(f"Mentor unavailable: {exc}")


def main() -> None:
    st.set_page_config(page_title="MainsMaster", page_icon="✒️", layout="wide")
    settings = get_settings()
    for key, default in (("user", None), ("view", "login"), ("selected_eval_id", None)):
        if key not in st.session_state:
            st.session_state[key] = default
    if not settings.database_url:
        st.error("DATABASE_URL is missing. Copy .env.example to .env and configure it.")
        return
    if st.session_state.user is None:
        login_view()
    elif st.session_state.view == "upload":
        upload_view(settings)
    elif st.session_state.view == "report":
        report_view(settings)
    else:
        dashboard_view()
