"""
Centralised session-state management.

Credentials (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, LLM_KEY) are loaded
directly from .env at the point of use — never stored in session state.
Session state only holds UI/pipeline data and the auth flag.
"""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DEFAULTS: dict = {
    # auth
    "authenticated": False,
    # navigation
    "step": "config",  # config | stories_select | running | review | writing | done
    # user-supplied at runtime
    "epic_key": os.getenv("JIRA_EPIC_KEY", ""),
    # fetched from Jira
    "available_stories": [],  # all stories under selected epic
    "stories": [],  # stories selected by user for processing
    "story_index": 0,
    # pipeline data
    "all_generated": {},  # story_key -> list[dict]
    "existing_tcs": {},  # story_key -> list[dict] from Jira
    "all_approved": {},  # story_key -> list[dict]
    "review_decisions": {},  # story_key -> {tc_index: bool}
    # write-back results
    "total_written": 0,
    "write_errors": [],
}


def init():
    """Initialise all session-state keys that are not yet set."""
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def reset():
    """Clear pipeline data so a new epic can be processed. Keeps auth."""
    pipeline_keys = [
        "step",
        "available_stories",
        "stories",
        "story_index",
        "all_generated",
        "all_approved",
        "review_decisions",
        "total_written",
        "write_errors",
        "vector_store_built",
        "pushed_tcs",
        "existing_tcs",
    ]
    for k in pipeline_keys:
        st.session_state.pop(k, None)
    init()
