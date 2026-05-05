"""
Page 4 — Writing: now a pass-through only.

Jira writes happen immediately in page_review after each story approval.
This page is kept as a safety fallback in case step="writing" is set
(e.g. from an older session), and redirects straight to done.
"""

import streamlit as st


def render():
    # Writing now happens per-story in page_review — go straight to done.
    st.session_state.step = "done"
    st.rerun()
