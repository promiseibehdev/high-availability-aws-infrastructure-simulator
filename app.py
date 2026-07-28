"""Streamlit entry point for the offline infrastructure simulator."""

import streamlit as st

from src.ui import initialize_ui_state, render_application

PROJECT_NAME = "High-Availability AWS Infrastructure Simulator"
SIMULATION_NOTICE = (
    "Simulation only - no AWS resources are created, and no AWS account or "
    "credentials are required."
)


def main() -> None:
    """Render the interactive, completely offline simulator."""

    st.set_page_config(
        page_title=PROJECT_NAME,
        page_icon=":material/cloud:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    initialize_ui_state()
    render_application(PROJECT_NAME, SIMULATION_NOTICE)


if __name__ == "__main__":
    main()
