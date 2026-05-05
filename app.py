"""
app.py — entry point.
Run with:  streamlit run app.py

NOTE: internal modules live in page_modules/ (not pages/) so Streamlit
does not auto-discover them as navigation pages.
"""

import streamlit as st

import state
from ui_components import inject_css
from page_modules import (
    page_config,
    page_stories_select,
    page_running,
    page_review,
    page_writing,
    page_done,
)

st.set_page_config(
    page_title="AI Test Case Generator",
    layout="wide",
)

state.init()
inject_css()

PAGES = {
    "config": page_config.render,
    "stories_select": page_stories_select.render,
    "running": page_running.render,
    "review": page_review.render,
    "writing": page_writing.render,
    "done": page_done.render,
}

current_step = st.session_state.get("step", "config")
render_fn = PAGES.get(current_step, page_config.render)
render_fn()
