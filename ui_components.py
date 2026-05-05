import os

"""
Reusable Streamlit UI components and HTML helpers.
"""
import streamlit as st

GLOBAL_CSS = """
<style>
/* ── Remove Streamlit default top padding ── */
.block-container { padding-top: 2rem !important; padding-bottom: 1rem !important; }

/* ── Tighten default element spacing ── */
div[data-testid="stVerticalBlock"] > div { gap: 0.3rem; }

/* ── Test case card ── */
.tc-card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 6px;
    background: #fafafa;
}
.tc-card.pushed { border-color: #17a2b8; background: #f0fbfc; }
.tc-card h4 { margin: 0 0 6px; font-size: 16px; font-weight: 600; line-height: 1.4; }

/* ── Steps / expected result box ── */
.tc-steps {
    background: #f4f4f4;
    border-radius: 5px;
    padding: 7px 10px;
    font-size: 14px;
    white-space: pre-wrap;
    margin-top: 6px;
    line-height: 1.6;
}
.tc-label {
    font-size: 14px;
    font-weight: 600;
    color: #444;
    margin-top: 6px;
    display: block;
}

/* ── Badges ── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    margin-right: 4px;
}
.badge-positive { background:#d4edda; color:#155724; }
.badge-negative { background:#f8d7da; color:#721c24; }
.badge-edge     { background:#fff3cd; color:#856404; }
.badge-high     { background:#cce5ff; color:#004085; }
.badge-medium   { background:#e2e3e5; color:#383d41; }
.badge-low      { background:#f8f9fa; color:#6c757d; border:1px solid #dee2e6; }

/* ── Pushed flag ── */
.pushed-flag {
    float: right;
    font-size: 12px;
    font-weight: 600;
    color: #0c5460;
    background: #d1ecf1;
    border: 1px solid #bee5eb;
    border-radius: 20px;
    padding: 1px 8px;
}

/* ── Story header ── */
.story-header {
    background: #eef2ff;
    border-left: 4px solid #4f46e5;
    border-radius: 0 6px 6px 0;
    padding: 8px 14px;
    margin-bottom: 8px;
    font-size: 14px;
}

/* ── Status pills ── */
.status-pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
}
.pill-approved { background:#d4edda; color:#155724; }
.pill-rejected { background:#f8d7da; color:#721c24; }
.pill-pending  { background:#fff3cd; color:#856404; }

/* ── Compact divider ── */
hr { margin: 0.5rem 0 !important; }
</style>
"""


def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def page_header(subtitle: str = ""):
    st.markdown("#### AI Test Case Generator")
    if subtitle:
        st.caption(subtitle)


def story_header_html(key: str, summary: str) -> str:
    return f"""<div class="story-header"><strong>{key}</strong> &nbsp;·&nbsp; {summary}</div>"""


def test_case_card_html(tc: dict, index: int, jira_key: str = "") -> str:
    tc_type = tc.get("type", "edge").lower()
    tc_prio = tc.get("priority", "medium").lower()
    pushed_class = "pushed" if jira_key else ""
    jira_url = os.getenv("JIRA_URL", "").rstrip("/")
    pushed_badge = (
        f'<a class="pushed-flag" href="{jira_url}/browse/{jira_key}" target="_blank">✓ {jira_key} ↗</a>'
        if jira_key
        else ""
    )
    exp = tc.get("expected_result", "")
    expected_html = (
        (
            f'<span class="tc-label">Expected Result:</span>'
            f'<div class="tc-steps">{exp}</div>'
        )
        if exp
        else ""
    )

    return f"""
    <div class="tc-card {pushed_class}">
        <h4>[{index}] {tc.get("title", "Untitled")} {pushed_badge}</h4>
        <span class="badge badge-{tc_type}">{tc_type}</span>
        <span class="badge badge-{tc_prio}">{tc_prio} priority</span>
        <div class="tc-steps">{tc.get("steps", "")}</div>
        {expected_html}
    </div>"""


def summary_row_html(key: str, summary: str, kept: int, total: int, status: str) -> str:
    return f"""
    <div style="display:flex;align-items:center;gap:12px;padding:6px 0;
                border-bottom:1px solid #eee;font-size:13px;">
        <strong>{key}</strong>
        <span style="flex:1;color:#555;">{summary[:65]}...</span>
        <span>{kept}/{total} kept</span>
        <span class="status-pill pill-{status}">{status}</span>
    </div>"""


def progress_bar(current: int, total: int, label: str = ""):
    st.progress(current / max(total, 1), text=label)
