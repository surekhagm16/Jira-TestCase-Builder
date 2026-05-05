"""Page 5 — Done: summary of what was written and links back to Jira."""

import os
import streamlit as st
from dotenv import load_dotenv
from ui_components import page_header, summary_row_html
import state

load_dotenv()


def render():
    page_header()
    st.divider()

    written = st.session_state.get("total_written", 0)
    errors = st.session_state.get("write_errors", [])

    # ── Result banner ─────────────────────────────────────────────────────────
    if not errors:
        st.success(f"✅ Done! **{written}** test case(s) written to Jira successfully.")
    else:
        st.warning(f"⚠️ {written} written, but {len(errors)} error(s) occurred.")
        with st.expander("Show errors"):
            for e in errors:
                st.error(e)

    # ── Per-story summary table ───────────────────────────────────────────────
    st.subheader("Summary")
    stories = st.session_state.stories
    all_approved = st.session_state.all_approved
    all_generated = st.session_state.all_generated

    for story in stories:
        key = story["key"]
        approved = all_approved.get(key, [])
        generated = all_generated.get(key, [])
        status = "approved" if approved else "rejected"
        st.markdown(
            summary_row_html(
                key=key,
                summary=story["summary"],
                kept=len(approved),
                total=len(generated),
                status=status,
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Actions ───────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔁 Run another epic", use_container_width=True):
            state.reset()
            st.rerun()

    with col2:
        project_key = st.session_state.epic_key.split("-")[0]
        jira_url = os.getenv("JIRA_URL", "")
        jira_board_url = f"{jira_url}/jira/software/projects/{project_key}/boards/2"
        st.link_button("🔗 Open Jira board", jira_board_url, use_container_width=True)
