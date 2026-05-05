"""Page 1 — Config: password gate + epic selection from Jira."""

import os
import streamlit as st
from dotenv import load_dotenv
from mcp_jira import fetch_epics, fetch_epic_stories
from ui_components import page_header

load_dotenv()

APP_PASSWORD = os.getenv("APP_PASSWORD", "")


def render():
    page_header(
        "Powered by LangChain · LangGraph · Groq · HuggingFace RAG · HITL\n\n Built by SM"
    )
    st.divider()

    if not st.session_state.get("authenticated"):
        _render_login()
        return

    _render_epic_selector()


def _render_login():
    col_l, col_m, col_r = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown("### 🔐 Sign in")
        pwd = st.text_input("Password", type="password", key="login_pwd")
        if st.button("Sign in", type="primary", use_container_width=True):
            if not APP_PASSWORD:
                st.error("APP_PASSWORD is not set in .env")
            elif pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")


def _render_epic_selector():
    st.success("✅ Signed in")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Active configuration")
        st.markdown(f"**Jira URL:** `{os.getenv('JIRA_URL', '—')}`")
        st.markdown(f"**Email:** `{os.getenv('JIRA_EMAIL', '—')}`")

    with col2:
        st.subheader("Select an epic")

        # Load epics (cached in session state so we don't re-fetch on every rerun)
        if "available_epics" not in st.session_state:
            with st.spinner("Fetching epics from Jira..."):
                try:
                    epics = fetch_epics(
                        url=os.getenv("JIRA_URL"),
                        email=os.getenv("JIRA_EMAIL"),
                        token=os.getenv("JIRA_API_TOKEN"),
                    )
                    st.session_state.available_epics = epics
                except Exception as e:
                    st.error(f"Could not fetch epics: {e}")
                    st.session_state.available_epics = []

        epics = st.session_state.get("available_epics", [])

        if not epics:
            st.warning("No epics found. Check your Jira connection.")
            if st.button("🔄 Retry"):
                st.session_state.pop("available_epics", None)
                st.rerun()
            return

        # Group by project for display
        options = [e["label"] for e in epics]
        keys = [e["key"] for e in epics]

        # Default to previously selected epic if available
        default_idx = 0
        prev_key = st.session_state.get("epic_key", "")
        if prev_key in keys:
            default_idx = keys.index(prev_key)

        selected_idx = st.selectbox(
            "Epic",
            options=range(len(options)),
            format_func=lambda i: options[i],
            index=default_idx,
            key="epic_selectbox",
        )

        selected_epic = epics[selected_idx]
        st.session_state.epic_key = selected_epic["key"]

        # Show status badge
        status = selected_epic.get("status", "")
        status_color = {
            "To Do": "#856404",
            "In Progress": "#004085",
            "Done": "#155724",
        }.get(status, "#383d41")
        status_bg = {
            "To Do": "#fff3cd",
            "In Progress": "#cce5ff",
            "Done": "#d4edda",
        }.get(status, "#e2e3e5")
        st.markdown(
            f'<span style="background:{status_bg};color:{status_color};'
            f"padding:2px 10px;border-radius:20px;font-size:12px;"
            f'font-weight:600;">{status}</span>',
            unsafe_allow_html=True,
        )

        col_refresh, col_start = st.columns([1, 2])
        with col_refresh:
            if st.button("🔄 Refresh epics", use_container_width=True):
                st.session_state.pop("available_epics", None)
                st.rerun()
        with col_start:
            if st.button(
                "🚀 Fetch stories & start", type="primary", use_container_width=True
            ):
                _start(selected_epic)


def _start(epic: dict):
    with st.spinner(f"Fetching stories from {epic['key']}..."):
        try:
            stories = fetch_epic_stories(
                url=os.getenv("JIRA_URL"),
                email=os.getenv("JIRA_EMAIL"),
                token=os.getenv("JIRA_API_TOKEN"),
                epic_key=epic["key"],
            )
        except Exception as e:
            st.error(f"Failed to fetch stories: {e}")
            return

    if not stories:
        st.warning(
            f"No stories found under **{epic['key']}**. "
            "Make sure child stories exist in Jira."
        )
        return

    # Store all fetched stories and go to selection screen
    st.session_state.available_stories = stories
    st.session_state.story_index = 0
    st.session_state.step = "stories_select"
    st.rerun()
