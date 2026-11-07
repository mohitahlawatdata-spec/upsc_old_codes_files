"""Launch with: python -m streamlit run streamlit_app.py"""

from mainsmaster.diagnostics import configure_logging
from mainsmaster.ui.app import main

configure_logging()
main()
