"""Page 2 — Story selection with per-story requirements analysis."""

import os
import streamlit as st
from dotenv import load_dotenv
from mcp_jira import fetch_test_cases_for_story
from analyser import analyse_story
from ui_components import page_header


load_dotenv()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _story_card(s: dict) -> str:
    desc = s.get("description", "")
    preview = (desc[:120] + "...") if len(desc) > 120 else desc
    desc_html = (
        '<br><span style="font-size:12px;color:#888;">' + preview + "</span>"
        if preview
        else ""
    )

    return (
        '<div style="border:1px solid #e0e0e0;border-radius:6px;'
        'padding:8px 12px;margin-bottom:2px;background:#fafafa;">'
        '<span style="font-size:14px;font-weight:600;">' + s["key"] + "</span>"
        '&nbsp;&nbsp;<span style="font-size:14px;">'
        + s["summary"]
        + "</span>"
        + desc_html
        + "</div>"
    )


VERDICT_STYLE = {
    "pass": ("✅", "#155724", "#d4edda"),
    "warn": ("⚠️", "#856404", "#fff3cd"),
    "fail": ("❌", "#721c24", "#f8d7da"),
}

DIMENSIONS = ["clarity", "ambiguity", "consistency", "readability"]
DIM_LABELS = {
    "clarity": "Clarity",
    "ambiguity": "Ambiguity",
    "consistency": "Consistency",
    "readability": "Readability",
}


def _render_analysis(key: str, analysis: dict):
    """Render the analysis results for a story."""
    if "error" in analysis:
        st.error(f"Analysis failed: {analysis['error']}")
        return

    overall = analysis.get("overall", {})
    o_verdict = overall.get("verdict", "warn")
    icon, color, bg = VERDICT_STYLE.get(o_verdict, ("⚠️", "#856404", "#fff3cd"))

    st.markdown(
        f'<div style="background:{bg};border-radius:6px;padding:8px 14px;'
        f'margin-bottom:8px;font-size:13px;color:{color};">'
        f"<strong>{icon} Overall — {o_verdict.upper()} "
        f"({overall.get('score', '?')}/5)</strong><br>"
        f"{overall.get('summary', '')}</div>",
        unsafe_allow_html=True,
    )

    # Dimension scores in a grid
    cols = st.columns(4)
    for col, dim in zip(cols, DIMENSIONS):
        data = analysis.get(dim, {})
        score = data.get("score", "?")
        verdict = data.get("verdict", "warn")
        d_icon, d_color, d_bg = VERDICT_STYLE.get(verdict, ("⚠️", "#856404", "#fff3cd"))
        with col:
            st.markdown(
                f'<div style="background:{d_bg};border-radius:6px;'
                f'padding:8px 10px;text-align:center;">'
                f'<div style="font-size:18px;">{d_icon}</div>'
                f'<div style="font-size:13px;font-weight:600;color:{d_color};">'
                f"{DIM_LABELS[dim]}</div>"
                f'<div style="font-size:20px;font-weight:700;color:{d_color};">'
                f'{score}<span style="font-size:12px;">/5</span></div>'
                f"</div>",
                unsafe_allow_html=True,
            )

    st.write("")

    # Issues and suggestions per dimension
    for dim in DIMENSIONS:
        data = analysis.get(dim, {})
        issues = data.get("issues", [])
        suggestion = data.get("suggestion", "")
        verdict = data.get("verdict", "warn")
        d_icon, d_color, _ = VERDICT_STYLE.get(verdict, ("⚠️", "#856404", "#fff3cd"))

        if issues or suggestion:
            with st.expander(
                f"{d_icon} {DIM_LABELS[dim]} — {data.get('score', '?')}/5",
                expanded=verdict == "fail",
            ):
                if issues:
                    st.markdown("**Issues found:**")
                    for issue in issues:
                        st.markdown(f"- {issue}")
                if suggestion:
                    st.markdown(
                        f'<div style="background:#eef2ff;border-radius:5px;'
                        f'padding:6px 10px;font-size:13px;margin-top:6px;">'
                        f"💡 <strong>Suggestion:</strong> {suggestion}</div>",
                        unsafe_allow_html=True,
                    )


# ── Main render ───────────────────────────────────────────────────────────────


def render():
    page_header()
    stories = st.session_state.get("available_stories", [])
    epic_key = st.session_state.get("epic_key", "")

    if not stories:
        st.warning("No stories found. Go back and select an epic.")
        if st.button("← Back to epic selection"):
            st.session_state.step = "config"
            st.rerun()
        return

    st.divider()

    st.markdown(
        '<div style="background:#eef2ff;border-left:4px solid #4f46e5;'
        "border-radius:0 6px 6px 0;padding:8px 14px;margin-bottom:12px;"
        'font-size:14px;"><strong>' + epic_key + "</strong>"
        " — Select stories to generate test cases for</div>",
        unsafe_allow_html=True,
    )

    # ── Bulk buttons ──────────────────────────────────────────────────────────
    col_a, col_b, col_c, _ = st.columns([1, 1, 1.5, 2])
    with col_a:
        if st.button("✅ Select all"):
            for s in stories:
                st.session_state["sel_" + s["key"]] = True
            st.rerun()
    with col_b:
        if st.button("❌ Deselect all"):
            for s in stories:
                st.session_state["sel_" + s["key"]] = False
            st.rerun()
    with col_c:
        if st.button("🔍 Analyse all stories"):
            analyses = {}
            progress = st.progress(0.0)
            for i, s in enumerate(stories):
                with st.spinner(f"Analysing {s['key']}..."):
                    analyses[s["key"]] = analyse_story(s)
                progress.progress((i + 1) / len(stories))
            st.session_state.analyses = analyses
            st.rerun()

    # Seed defaults
    for s in stories:
        if ("sel_" + s["key"]) not in st.session_state:
            st.session_state["sel_" + s["key"]] = True

    st.markdown(
        f"<p style='font-size:13px;color:#666;margin:4px 0 8px;'>"
        f"Found <strong>{len(stories)}</strong> stories:</p>",
        unsafe_allow_html=True,
    )

    # ── Story list ────────────────────────────────────────────────────────────
    analyses = st.session_state.get("analyses", {})

    for s in stories:
        col_check, col_info = st.columns([0.05, 0.95])
        with col_check:
            st.checkbox(
                label="select",
                key="sel_" + s["key"],
                label_visibility="collapsed",
            )
        with col_info:
            st.markdown(_story_card(s), unsafe_allow_html=True)

            # Per-story analyse button + results
            btn_col, _ = st.columns([1, 5])
            with btn_col:
                if st.button(
                    "🔍 Analyse",
                    key="analyse_" + s["key"],
                    use_container_width=True,
                ):
                    with st.spinner(f"Analysing {s['key']}..."):
                        result = analyse_story(s)
                    all_analyses = st.session_state.get("analyses", {})
                    all_analyses[s["key"]] = result
                    st.session_state.analyses = all_analyses
                    st.rerun()

            if s["key"] in analyses:
                with st.container():
                    _render_analysis(s["key"], analyses[s["key"]])

        st.markdown(
            "<hr style='margin:4px 0;border-color:#f0f0f0;'>",
            unsafe_allow_html=True,
        )

    # ── Count & actions ───────────────────────────────────────────────────────
    selected = [s for s in stories if st.session_state.get("sel_" + s["key"], True)]
    count = len(selected)

    st.divider()
    st.caption(f"**{count}** of {len(stories)} stories selected")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back to epic selection", use_container_width=True):
            st.session_state.step = "config"
            st.rerun()
    with col2:
        if st.button(
            f"🚀 Generate test cases for {count} stories",
            type="primary",
            use_container_width=True,
            disabled=count == 0,
        ):
            st.session_state.stories = selected
            st.session_state.story_index = 0

            existing, fetch_log = {}, []
            with st.spinner("Checking Jira for existing test cases..."):
                for s in selected:
                    try:
                        tcs = fetch_test_cases_for_story(
                            url=os.getenv("JIRA_URL"),
                            email=os.getenv("JIRA_EMAIL"),
                            token=os.getenv("JIRA_API_TOKEN"),
                            story_key=s["key"],
                        )
                        existing[s["key"]] = tcs
                        fetch_log.append(f"{s['key']}: {len(tcs)} existing TC(s) found")
                    except Exception as ex:
                        fetch_log.append(f"{s['key']}: error — {ex}")

            st.session_state.existing_tcs = existing
            st.session_state.fetch_log = fetch_log
            st.session_state.step = "running"
            st.rerun()
