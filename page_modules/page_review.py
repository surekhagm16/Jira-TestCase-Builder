"""Page 3 — Review: HITL approval + per-card edit/push/regenerate."""

import os
import streamlit as st
from dotenv import load_dotenv
from mcp_jira import write_test_cases_to_jira, update_test_case
from ui_components import page_header, story_header_html, progress_bar

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL", "").rstrip("/")


def _normalise_steps(text: str) -> str:
    """Strip leading whitespace and existing numbering (e.g. '1. ') from each line."""
    import re

    result = []
    for line in text.splitlines():
        line = line.lstrip()
        line = re.sub(r"^\d+\.\s*", "", line)  # strip "1. " "2. " etc
        result.append(line)
    return "\n".join(result)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _widget_key(story_key: str, i: int) -> str:
    return f"chk_{story_key}_{i}"


def _seed_widgets(story_key: str, tcs: list, decisions: dict):
    for i in range(len(tcs)):
        k = _widget_key(story_key, i)
        if k not in st.session_state:
            st.session_state[k] = decisions.get(i, True)


def _bulk_set(story_key: str, tcs: list, decisions: dict, value: bool):
    for i in range(len(tcs)):
        decisions[i] = value
        st.session_state[_widget_key(story_key, i)] = value
    st.rerun()


def _pushed_map(story_key: str) -> dict:
    return st.session_state.setdefault("pushed_tcs", {}).setdefault(story_key, {})


def _edit_key(story_key: str, i: int) -> str:
    return f"editing_{story_key}_{i}"


def _edited_tc(story_key: str, i: int, original: dict) -> dict:
    """Return the current (possibly edited) version of a TC."""
    edits = st.session_state.get(f"edit_data_{story_key}_{i}", {})
    return {**original, **edits}


def _type_color(tc_type: str) -> str:
    return {"positive": "#155724", "negative": "#721c24", "edge": "#856404"}.get(
        tc_type.lower(), "#383d41"
    )


def _type_bg(tc_type: str) -> str:
    return {"positive": "#d4edda", "negative": "#f8d7da", "edge": "#fff3cd"}.get(
        tc_type.lower(), "#e2e3e5"
    )


def _prio_color(prio: str) -> str:
    return {"high": "#004085", "medium": "#383d41", "low": "#6c757d"}.get(
        prio.lower(), "#383d41"
    )


def _prio_bg(prio: str) -> str:
    return {"high": "#cce5ff", "medium": "#e2e3e5", "low": "#f8f9fa"}.get(
        prio.lower(), "#e2e3e5"
    )


def _render_card_view(story_key: str, i: int, tc: dict, jira_key: str):
    """Read-only card with action buttons."""
    tc_type = tc.get("type", "edge")
    tc_prio = tc.get("priority", "medium")
    exp = tc.get("expected_result", "")

    pushed_badge = (
        (
            f'<a href="{JIRA_URL}/browse/{jira_key}" target="_blank" '
            f'style="float:right;font-size:11px;font-weight:600;color:#0c5460;'
            f"background:#d1ecf1;border:1px solid #bee5eb;border-radius:20px;"
            f'padding:2px 8px;text-decoration:none;">✓ {jira_key} ↗</a>'
        )
        if jira_key
        else ""
    )

    expected_html = (
        (
            f'<div style="margin-top:8px;">'
            f'<span style="font-size:13px;font-weight:600;">Expected Result:</span>'
            f'<div style="background:#f4f4f4;border-radius:5px;padding:7px 10px;'
            f'font-size:14px;margin-top:4px;white-space:pre-wrap;">{_normalise_steps(exp)}</div></div>'
        )
        if exp
        else ""
    )

    border_color = "#17a2b8" if jira_key else "#e0e0e0"
    bg_color = "#f0fbfc" if jira_key else "#fafafa"

    st.markdown(
        f"""
    <div style="border:1px solid {border_color};border-radius:8px;
                padding:10px 14px;background:{bg_color};margin-bottom:4px;">
        <h4 style="margin:0 0 6px;font-size:16px;font-weight:600;">
            [{i + 1}] {tc.get("title", "Untitled")} {pushed_badge}
        </h4>
        <span style="display:inline-block;padding:2px 10px;border-radius:20px;
                     font-size:13px;font-weight:600;margin-right:4px;
                     background:{_type_bg(tc_type)};color:{_type_color(tc_type)};">
            {tc_type}
        </span>
        <span style="display:inline-block;padding:2px 10px;border-radius:20px;
                     font-size:13px;font-weight:600;
                     background:{_prio_bg(tc_prio)};color:{_prio_color(tc_prio)};">
            {tc_prio} priority
        </span>
        <div style="background:#f4f4f4;border-radius:5px;padding:7px 10px 7px 30px;
                    font-size:14px;margin-top:6px;">
            <ol style="margin:0;padding:0;">
                {
            "".join(
                f'<li style="margin-bottom:3px;">{line}</li>'
                for line in _normalise_steps(tc.get("steps", "")).splitlines()
                if line.strip()
            )
        }
            </ol>
        </div>
        {expected_html}
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Per-card action buttons + inline priority selector
    b1, b2, b3, b4, b5 = st.columns([1, 1.2, 1, 1, 1])
    with b1:
        if st.button(
            "✏️ Edit", key=f"btn_edit_{story_key}_{i}", use_container_width=True
        ):
            st.session_state[_edit_key(story_key, i)] = True
            st.rerun()
    with b2:
        PRIORITIES = ["high", "medium", "low"]
        current_prio = tc.get("priority", "medium").lower()
        prio_idx = PRIORITIES.index(current_prio) if current_prio in PRIORITIES else 1
        new_prio = st.selectbox(
            "⬆️ Priority",
            options=PRIORITIES,
            index=prio_idx,
            key=f"prio_{story_key}_{i}",
        )
        if new_prio != current_prio:
            st.session_state.all_generated[story_key][i]["priority"] = new_prio
            st.rerun()
    with b3:
        push_label = "✅ Pushed" if jira_key else "🚀 Push to Jira"
        if st.button(
            push_label,
            key=f"btn_push_{story_key}_{i}",
            use_container_width=True,
            disabled=bool(jira_key),
            type="primary" if not jira_key else "secondary",
        ):
            _push_single(story_key, i, tc)
            st.rerun()
    with b4:
        if jira_key:
            if st.button(
                "🔄 Re-push",
                key=f"btn_repush_{story_key}_{i}",
                use_container_width=True,
            ):
                _repush_single(story_key, i, tc, jira_key)
                st.rerun()


def _render_card_edit(story_key: str, i: int, tc: dict, jira_key: str):
    """Editable card with Save / Cancel."""
    st.markdown(
        f"""
    <div style="border:2px solid #4f46e5;border-radius:8px;
                padding:10px 14px;background:#f5f5ff;margin-bottom:4px;">
        <span style="font-size:13px;font-weight:600;color:#4f46e5;">
            ✏️ Editing [{i + 1}]
        </span>
    </div>""",
        unsafe_allow_html=True,
    )

    new_title = st.text_input(
        "Title", value=tc.get("title", ""), key=f"inp_title_{story_key}_{i}"
    )
    new_steps = st.text_area(
        "Steps", value=tc.get("steps", ""), key=f"inp_steps_{story_key}_{i}", height=120
    )
    new_expected = st.text_area(
        "Expected Result",
        value=tc.get("expected_result", ""),
        key=f"inp_exp_{story_key}_{i}",
        height=80,
    )

    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        if st.button(
            "💾 Save",
            key=f"btn_save_{story_key}_{i}",
            type="primary",
            use_container_width=True,
        ):
            # Persist edits back into all_generated
            tcs = st.session_state.all_generated[story_key]
            tcs[i] = {
                **tcs[i],
                "title": new_title,
                "steps": new_steps,
                "expected_result": new_expected,
            }
            st.session_state.all_generated[story_key] = tcs
            st.session_state[_edit_key(story_key, i)] = False
            st.rerun()
    with c2:
        if st.button(
            "✖ Cancel", key=f"btn_cancel_{story_key}_{i}", use_container_width=True
        ):
            st.session_state[_edit_key(story_key, i)] = False
            st.rerun()


def _push_single(story_key: str, i: int, tc: dict):
    pushed = _pushed_map(story_key)
    with st.spinner(f"Pushing [{i + 1}] to Jira..."):
        created, errors = write_test_cases_to_jira(
            url=os.getenv("JIRA_URL"),
            email=os.getenv("JIRA_EMAIL"),
            token=os.getenv("JIRA_API_TOKEN"),
            story_key=story_key,
            test_cases=[tc],
        )
    if created:
        pushed[i] = created[0]
        st.session_state.total_written = st.session_state.get("total_written", 0) + 1
        st.success(f"✅ Created {created[0]} in Jira")
    for e in errors:
        st.error(f"❌ {e}")


def _repush_single(story_key: str, i: int, tc: dict, jira_key: str):
    with st.spinner(f"Updating {jira_key} in Jira..."):
        success, error = update_test_case(
            url=os.getenv("JIRA_URL"),
            email=os.getenv("JIRA_EMAIL"),
            token=os.getenv("JIRA_API_TOKEN"),
            jira_key=jira_key,
            tc=tc,
        )
    if success:
        st.success(f"✅ {jira_key} updated in Jira")
    else:
        st.error(f"❌ {error}")


def _render_existing_tcs(story_key: str, existing: list[dict]):
    """Show existing Jira TCs with inline edit and re-push capability."""
    with st.expander(
        f"📋 {len(existing)} existing test case(s) already in Jira — click to view / edit",
        expanded=False,
    ):
        for idx, tc in enumerate(existing):
            jira_key = tc.get("key", "")
            edit_key = f"ex_edit_{story_key}_{idx}"
            is_editing = st.session_state.get(edit_key, False)

            if is_editing:
                # ── Edit mode ─────────────────────────────────────────────
                st.markdown(
                    f'<div style="border:2px solid #4f46e5;border-radius:8px;'
                    f'padding:8px 14px;background:#f5f5ff;margin-bottom:4px;">'
                    f'<strong style="color:#4f46e5;">✏️ Editing {jira_key}</strong></div>',
                    unsafe_allow_html=True,
                )
                new_title = st.text_input(
                    "Title",
                    value=tc.get("title", ""),
                    key=f"ex_title_{story_key}_{idx}",
                )
                new_steps = st.text_area(
                    "Steps",
                    value=tc.get("steps", ""),
                    key=f"ex_steps_{story_key}_{idx}",
                    height=100,
                )
                new_exp = st.text_area(
                    "Expected Result",
                    value=tc.get("expected_result", ""),
                    key=f"ex_exp_{story_key}_{idx}",
                    height=70,
                )

                PRIORITIES = ["high", "medium", "low"]
                cur_prio = tc.get("priority", "medium")
                new_prio = st.selectbox(
                    "⬆️ Priority",
                    PRIORITIES,
                    index=PRIORITIES.index(cur_prio) if cur_prio in PRIORITIES else 1,
                    key=f"ex_prio_{story_key}_{idx}",
                )

                c1, c2, c3 = st.columns([1, 1, 3])
                with c1:
                    if st.button(
                        "💾 Save & update Jira",
                        key=f"ex_save_{story_key}_{idx}",
                        type="primary",
                        use_container_width=True,
                    ):
                        updated_tc = {
                            **tc,
                            "title": new_title,
                            "steps": new_steps,
                            "expected_result": new_exp,
                            "priority": new_prio,
                        }
                        with st.spinner(f"Updating {jira_key}..."):
                            success, error = update_test_case(
                                url=os.getenv("JIRA_URL"),
                                email=os.getenv("JIRA_EMAIL"),
                                token=os.getenv("JIRA_API_TOKEN"),
                                jira_key=jira_key,
                                tc=updated_tc,
                            )
                        if success:
                            # Update local copy in session state
                            st.session_state["existing_tcs"][story_key][idx] = (
                                updated_tc
                            )
                            st.session_state[edit_key] = False
                            st.success(f"✅ {jira_key} updated in Jira")
                        else:
                            st.error(f"❌ {error}")
                        st.rerun()
                with c2:
                    if st.button(
                        "✖ Cancel",
                        key=f"ex_cancel_{story_key}_{idx}",
                        use_container_width=True,
                    ):
                        st.session_state[edit_key] = False
                        st.rerun()

            else:
                # ── View mode ─────────────────────────────────────────────
                tc_type = tc.get("type", "edge")
                tc_prio = tc.get("priority", "medium")
                exp = tc.get("expected_result", "")
                steps = _normalise_steps(tc.get("steps", ""))

                steps_html = (
                    "<ol style='margin:0;padding-left:20px;'>"
                    + "".join(
                        f"<li style='margin-bottom:3px;'>{l}</li>"
                        for l in steps.splitlines()
                        if l.strip()
                    )
                    + "</ol>"
                )
                exp_html = (
                    (
                        f'<div style="margin-top:6px;">'
                        f'<span style="font-size:13px;font-weight:600;">Expected Result:</span>'
                        f'<div style="background:#f4f4f4;border-radius:5px;padding:7px 10px;'
                        f'font-size:14px;margin-top:4px;white-space:pre-wrap;">{exp}</div></div>'
                    )
                    if exp
                    else ""
                )

                jira_link = (
                    f'<a href="{JIRA_URL}/browse/{jira_key}" target="_blank" '
                    f'style="float:right;font-size:11px;font-weight:600;color:#0c5460;'
                    f"background:#d1ecf1;border:1px solid #bee5eb;border-radius:20px;"
                    f'padding:2px 8px;text-decoration:none;">↗ {jira_key}</a>'
                )
                st.markdown(
                    f'<div style="border:1px solid #17a2b8;border-radius:8px;'
                    f'padding:10px 14px;background:#f0fbfc;margin-bottom:4px;">'
                    f'<h4 style="margin:0 0 6px;font-size:16px;font-weight:600;">'
                    f"{jira_link}{tc.get('title', 'Untitled')}</h4>"
                    f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;'
                    f"font-size:13px;font-weight:600;margin-right:4px;"
                    f'background:{_type_bg(tc_type)};color:{_type_color(tc_type)};">{tc_type}</span>'
                    f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;'
                    f"font-size:13px;font-weight:600;"
                    f'background:{_prio_bg(tc_prio)};color:{_prio_color(tc_prio)};">'
                    f"{tc_prio} priority</span>"
                    f'<div style="background:#f4f4f4;border-radius:5px;padding:7px 10px;'
                    f'font-size:14px;margin-top:6px;">{steps_html}</div>'
                    f"{exp_html}</div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    f"✏️ Edit {jira_key}",
                    key=f"ex_edit_btn_{story_key}_{idx}",
                    use_container_width=False,
                ):
                    st.session_state[edit_key] = True
                    st.rerun()

            st.markdown(
                "<hr style='margin:4px 0;border-color:#f0f0f0;'>",
                unsafe_allow_html=True,
            )


# ── Main render ───────────────────────────────────────────────────────────────


def render():
    page_header()
    stories = st.session_state.stories
    idx = st.session_state.story_index
    story = stories[idx]
    tcs = st.session_state.all_generated.get(story["key"], [])
    decisions = st.session_state.review_decisions.setdefault(
        story["key"], {i: True for i in range(len(tcs))}
    )
    is_last = idx + 1 >= len(stories)
    pushed = _pushed_map(story["key"])

    _seed_widgets(story["key"], tcs, decisions)

    # ── Progress & story header ───────────────────────────────────────────────
    progress_bar(
        idx + 0.5,
        len(stories),
        f"Review — Story {idx + 1} of {len(stories)}: **{story['key']}**",
    )
    st.divider()
    st.markdown(
        story_header_html(story["key"], story["summary"]), unsafe_allow_html=True
    )

    # ── Existing Jira TCs ────────────────────────────────────────────────────
    existing = st.session_state.get("existing_tcs", {}).get(story["key"], [])
    fetch_log = st.session_state.get("fetch_log", [])
    story_log = next((l for l in fetch_log if l.startswith(story["key"])), "")
    if existing:
        _render_existing_tcs(story["key"], existing)
    else:
        with st.expander(
            f"📋 No existing test cases found in Jira for {story['key']}",
            expanded=False,
        ):
            st.caption(story_log or "Nothing fetched.")
            st.caption(
                "Test cases must use issue type **Test** and be "
                "children (parent =) of this story to appear here."
            )

    # ── Bulk select buttons ───────────────────────────────────────────────────
    col_a, col_b, _ = st.columns([1, 1, 4])
    with col_a:
        if st.button("✅ Select all"):
            _bulk_set(story["key"], tcs, decisions, True)
    with col_b:
        if st.button("❌ Deselect all"):
            _bulk_set(story["key"], tcs, decisions, False)

    for i in range(len(tcs)):
        decisions[i] = st.session_state.get(_widget_key(story["key"], i), True)

    approved_count = sum(1 for v in decisions.values() if v)
    pushed_count = len(pushed)
    st.caption(
        f"Generated **{len(tcs)}** · "
        f"**{approved_count}** selected · "
        f"**{pushed_count}** pushed to Jira"
    )

    # ── Test case cards ───────────────────────────────────────────────────────
    for i, tc in enumerate(tcs):
        jira_key = pushed.get(i, "")
        is_editing = st.session_state.get(_edit_key(story["key"], i), False)

        col_check, col_card = st.columns([0.05, 0.95])
        with col_check:
            val = st.checkbox(
                label="keep",
                key=_widget_key(story["key"], i),
                label_visibility="collapsed",
            )
            decisions[i] = val

        with col_card:
            if is_editing:
                _render_card_edit(story["key"], i, tc, jira_key)
            else:
                _render_card_view(story["key"], i, tc, jira_key)

        st.markdown(
            "<hr style='margin:4px 0;border-color:#f0f0f0;'>", unsafe_allow_html=True
        )

    # ── Story-level actions ───────────────────────────────────────────────────
    st.divider()

    # Recompute unpushed approved TCs for bulk push button label
    approved_count = sum(decisions[i] for i in range(len(tcs)))
    unpushed = [
        (i, tcs[i])
        for i in range(len(tcs))
        if decisions.get(i, True) and i not in pushed
    ]
    unpushed_count = len(unpushed)

    col1, col2, col3 = st.columns([1.2, 1.2, 1])

    # Button 1 — Regenerate all
    with col1:
        if st.button("🔄 Regenerate all for this story", use_container_width=True):
            for i in range(len(tcs)):
                st.session_state.pop(_widget_key(story["key"], i), None)
                st.session_state.pop(_edit_key(story["key"], i), None)
            del st.session_state.all_generated[story["key"]]
            st.session_state.setdefault("pushed_tcs", {}).pop(story["key"], None)
            st.session_state.step = "running"
            st.rerun()

    # Button 2 — Push all selected (bulk)
    with col2:
        # Three distinct states:
        # 1. nothing selected at all       -> "Nothing selected" (disabled)
        # 2. some selected, none pushed    -> "Push all N selected" (enabled)
        # 3. all selected already pushed   -> "All selected pushed" (disabled)
        nothing_selected = approved_count == 0
        all_already_pushed = approved_count > 0 and unpushed_count == 0

        if nothing_selected:
            bulk_label = "Nothing selected"
            bulk_disabled = True
            bulk_type = "secondary"
        elif all_already_pushed:
            bulk_label = "✅ All selected pushed"
            bulk_disabled = True
            bulk_type = "secondary"
        else:
            bulk_label = f"🚀 Push all {unpushed_count} selected to Jira"
            bulk_disabled = False
            bulk_type = "primary"

        if st.button(
            bulk_label,
            use_container_width=True,
            disabled=bulk_disabled,
            type=bulk_type,
        ):
            with st.spinner(
                f"Pushing {unpushed_count} test case(s) to {story['key']}..."
            ):
                created, errors = write_test_cases_to_jira(
                    url=os.getenv("JIRA_URL"),
                    email=os.getenv("JIRA_EMAIL"),
                    token=os.getenv("JIRA_API_TOKEN"),
                    story_key=story["key"],
                    test_cases=[tc for _, tc in unpushed],
                )
            # Map created keys back to tc indices
            for (tc_idx, _), jira_key in zip(unpushed, created):
                pushed[tc_idx] = jira_key
            st.session_state.total_written = st.session_state.get(
                "total_written", 0
            ) + len(created)
            if errors:
                st.session_state.setdefault("write_errors", []).extend(
                    [f"{story['key']}: {e}" for e in errors]
                )
                for e in errors:
                    st.error(f"❌ {e}")
            if created:
                st.session_state.all_approved[story["key"]] = [
                    tcs[i] for i in range(len(tcs)) if decisions.get(i, True)
                ]
                st.success(f"✅ Pushed to Jira: **{', '.join(created)}**")
            st.rerun()

    # Button 3 — Next story / Finish
    with col3:
        next_label = "🏁 Finish" if is_last else f"Next → {stories[idx + 1]['key']}"
        if st.button(next_label, use_container_width=True):
            st.session_state.all_approved[story["key"]] = [
                tcs[i] for i in range(len(tcs)) if decisions.get(i, True)
            ]
            if is_last:
                st.session_state.step = "done"
            else:
                st.session_state.story_index = idx + 1
                st.session_state.step = "running"
            st.rerun()
