"""Page 2 — Running: generate test cases for the current story via LLM."""

import os
import streamlit as st
from dotenv import load_dotenv
from rag_pipeline import build_vector_store
from ui_components import page_header, progress_bar

load_dotenv()


def render():
    page_header()
    stories = st.session_state.stories
    idx = st.session_state.story_index
    story = stories[idx]

    progress_bar(
        idx, len(stories), f"Story {idx + 1} of {len(stories)}: **{story['key']}**"
    )
    st.divider()

    # Build vector store once on the first story (no API key needed)
    if idx == 0 and "vector_store_built" not in st.session_state:
        with st.spinner("Loading, please wait..."):
            build_vector_store(stories)
            st.session_state.vector_store_built = True

    # Generate test cases if not already done for this story
    if story["key"] not in st.session_state.all_generated:
        with st.spinner(
            f"Generating test cases for **{story['key']}** — {story['summary']}..."
        ):
            tcs = _generate(story)
            st.session_state.all_generated[story["key"]] = tcs
            st.session_state.review_decisions[story["key"]] = {
                i: True for i in range(len(tcs))
            }

    st.session_state.step = "review"
    st.rerun()


def _generate(story: dict) -> list[dict]:
    """Invoke the LangGraph generate_test_cases node for one story."""
    from graph import generate_test_cases as gen_node

    node_state = {
        "stories": st.session_state.stories,
        "llm_key": os.getenv("LLM_KEY", ""),  # from env, never UI
        "current_story_index": st.session_state.story_index,
        "current_story": story,
        "retrieved_context": "",
        "generated_test_cases": [],
        "approved_test_cases": [],
        "all_approved": st.session_state.all_approved,
    }
    result = gen_node(node_state)
    return result["generated_test_cases"]
