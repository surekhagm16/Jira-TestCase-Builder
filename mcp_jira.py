import os
import re as _re
from jira import JIRA, JIRAError


def _adf_to_text(adf) -> str:
    """
    Convert Jira description to plain text.
    Handles 3 formats:
      1. None / empty
      2. Plain string or Jira wiki markup (Jira Server)
      3. ADF dict (Jira Cloud)
    """
    if adf is None:
        return ""

    # Handle jira library special objects
    if hasattr(adf, "__dict__") and not isinstance(adf, (dict, str, list)):
        adf = vars(adf)

    # Plain string - may be Jira wiki markup, clean it up
    if isinstance(adf, str):
        text = adf
        # Remove heading lines like "h3. User story"

        text = _re.sub(r"(?m)^h[1-6]\.[^\n]*\n?", "", text)
        text = _re.sub(r"\*([^*\n]+)\*", lambda m: m.group(1), text)
        text = _re.sub(r"_([^_\n]+)_", lambda m: m.group(1), text)
        text = _re.sub(r"(?m)^\s*\*\s+", "", text)
        text = _re.sub(r"(?m)^\s*#+\s+", "", text)
        # Strip Jira macros: {noformat}, {code}, {panel} etc
        text = _re.sub(r"\{[a-zA-Z][^}]*\}", "", text)
        # Strip any remaining curly brace content
        text = _re.sub(r"\{[^}]*\}", "", text)
        text = _re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # ADF dict (Jira Cloud)
    if isinstance(adf, dict):
        node_type = adf.get("type", "")
        if node_type == "text":
            return adf.get("text", "")
        if node_type in ("hardBreak", "rule"):
            return "\n"
        children = adf.get("content", [])
        parts = [_adf_to_text(child) for child in children]
        joined = "".join(parts)
        if node_type in (
            "paragraph",
            "heading",
            "listItem",
            "bulletList",
            "orderedList",
            "blockquote",
            "codeBlock",
            "panel",
            "doc",
        ):
            joined = joined.rstrip() + "\n"
        return joined

    if isinstance(adf, list):
        return "".join(_adf_to_text(item) for item in adf)

    return str(adf)


def get_jira_client(url: str, email: str, token: str) -> JIRA:
    return JIRA(server=url, basic_auth=(email, token))


def fetch_epic_stories(url: str, email: str, token: str, epic_key: str) -> list[dict]:
    """Fetch all child stories under a given epic key, sorted ascending by key."""
    jira = get_jira_client(url, email, token)
    issues = jira.search_issues(
        f'"Epic Link" = {epic_key} OR parent = {epic_key} ORDER BY key ASC',
        fields="summary,description,status",
        maxResults=50,
    )
    stories = [
        {
            "key": issue.key,
            "summary": issue.fields.summary,
            "description": _adf_to_text(issue.fields.description).strip(),
        }
        for issue in issues
    ]
    # Client-side sort guarantees numeric order (SP-2 before SP-10)
    stories.sort(key=lambda s: int(s["key"].split("-")[-1]))
    return stories


def fetch_epics(url: str, email: str, token: str) -> list[dict]:
    """
    Fetch all epics across all projects the user has access to.
    Returns list of {key, summary, project} dicts sorted by project then key.
    """
    jira = get_jira_client(url, email, token)
    issues = jira.search_issues(
        "issuetype = Epic ORDER BY project ASC, key ASC",
        fields="summary,project,status",
        maxResults=200,
    )
    return [
        {
            "key": issue.key,
            "summary": issue.fields.summary,
            "project": issue.fields.project.name,
            "status": issue.fields.status.name,
            "label": f"{issue.key} · {issue.fields.summary} [{issue.fields.project.name}]",
        }
        for issue in issues
    ]


def _build_description(tc: dict) -> str:
    """
    Single place that formats a TC dict into a Jira description string.
    Add/remove fields here only — nothing else needs to change.
    """
    steps = tc.get("steps", "")
    expected_result = tc.get("expected_result", "")
    priority = tc.get("priority", "?")
    tc_type = tc.get("type", "?")

    parts = [steps]
    if expected_result:
        parts.append(f"*Expected Result:*\n{expected_result}")
    parts.append(f"_Priority: {priority} | Type: {tc_type}_")
    return "\n\n".join(parts)


def _get_issue_types(jira: JIRA, project_key: str) -> list[str]:
    """Return available issue type names for a project."""
    project = jira.project(project_key)
    return [it.name for it in jira.issue_types_for_project(project.id)]


def write_test_cases_to_jira(
    url: str,
    email: str,
    token: str,
    story_key: str,
    test_cases: list[dict],
) -> tuple[list[str], list[str]]:
    """
    Create test case issues as children of a story.
    Tries 3 strategies in order to handle both company-managed
    and team-managed Jira projects.

    Returns (created_keys, errors).
    """
    jira = get_jira_client(url, email, token)
    project_key = story_key.split("-")[0]

    # Discover available issue types so we pick one that exists
    try:
        available_types = _get_issue_types(jira, project_key)
    except Exception:
        available_types = []

    # Prefer Test, fall back to Task, Story, then first available
    preferred = ["Test", "Task", "Story", "Sub-task", "Subtask"]
    issue_type = next(
        (t for t in preferred if t in available_types),
        available_types[0] if available_types else "Task",
    )

    created, errors = [], []
    for tc in test_cases:
        key, err = _create_one(jira, project_key, story_key, issue_type, tc)
        if key:
            created.append(key)
        if err:
            errors.append(f"{tc.get('title', '?')}: {err}")

    return created, errors


def update_test_case(
    url: str,
    email: str,
    token: str,
    jira_key: str,
    tc: dict,
) -> tuple[bool, str | None]:
    """
    Update an existing Jira issue with revised TC content.
    Returns (success, error).
    """
    jira = get_jira_client(url, email, token)
    try:
        issue = jira.issue(jira_key)
        issue.update(
            fields={
                "summary": tc.get("title", "Untitled test case"),
                "description": _build_description(tc),
            }
        )
        return True, None
    except JIRAError as e:
        return False, str(e)


def _create_one(
    jira: JIRA,
    project_key: str,
    story_key: str,
    issue_type: str,
    tc: dict,
) -> tuple[str | None, str | None]:
    """
    Try to create a single issue, attempting progressively simpler
    field sets if Jira rejects the request.
    """
    title = tc.get("title", "Untitled test case")
    description = _build_description(tc)

    # Strategy 1: full fields with parent + labels
    try:
        issue = jira.create_issue(
            fields={
                "project": {"key": project_key},
                "summary": title,
                "description": description,
                "issuetype": {"name": issue_type},
                "parent": {"key": story_key},
                "labels": ["ai-generated", "test-case"],
            }
        )
        return issue.key, None
    except JIRAError:
        pass

    # Strategy 2: parent without labels
    try:
        issue = jira.create_issue(
            fields={
                "project": {"key": project_key},
                "summary": title,
                "description": description,
                "issuetype": {"name": issue_type},
                "parent": {"key": story_key},
            }
        )
        return issue.key, None
    except JIRAError:
        pass

    # Strategy 3: standalone then link
    try:
        issue = jira.create_issue(
            fields={
                "project": {"key": project_key},
                "summary": title,
                "description": description,
                "issuetype": {"name": issue_type},
            }
        )
        try:
            jira.create_issue_link(
                type="relates to",
                inwardIssue=issue.key,
                outwardIssue=story_key,
            )
        except Exception:
            pass
        return issue.key, None
    except JIRAError as e:
        return None, str(e)


def fetch_test_cases_for_story(
    url: str, email: str, token: str, story_key: str
) -> list[dict]:
    """
    Fetch existing Test issues that are children of or linked to a story.
    Uses two simple JQL queries to avoid ScriptRunner dependency.
    Returns list of {key, title, steps, expected_result, priority, type}.
    """
    jira = get_jira_client(url, email, token)
    project_key = story_key.split("-")[0]

    seen_keys = set()
    all_issues = []

    # Query 1: direct children (parent = story)
    try:
        children = jira.search_issues(
            f"project = {project_key} AND issuetype = Test AND parent = {story_key}",
            fields="summary,description,priority,labels",
            maxResults=100,
        )
        for i in children:
            if i.key not in seen_keys:
                all_issues.append(i)
                seen_keys.add(i.key)
    except Exception:
        pass

    # Query 2: issues linked to the story (relates to / is child of)
    try:
        linked = jira.search_issues(
            f'project = {project_key} AND issuetype = Test AND issue in linkedIssues("{story_key}")',
            fields="summary,description,priority,labels",
            maxResults=100,
        )
        for i in linked:
            if i.key not in seen_keys:
                all_issues.append(i)
                seen_keys.add(i.key)
    except Exception:
        pass

    issues = all_issues

    results = []
    for issue in issues:
        desc = _adf_to_text(issue.fields.description).strip()
        lines = desc.splitlines()

        # Parse steps and expected_result out of stored description
        steps_lines, exp_lines, in_exp = [], [], False
        for line in lines:
            if line.strip().startswith("*Expected Result:*"):
                in_exp = True
                continue
            if line.strip().startswith("_Priority:"):
                break
            if in_exp:
                exp_lines.append(line)
            else:
                steps_lines.append(line)

        prio_field = getattr(issue.fields, "priority", None)
        prio = prio_field.name.lower() if prio_field else "medium"
        # Normalise Jira priority names -> our values
        prio_map = {
            "highest": "high",
            "high": "high",
            "medium": "medium",
            "low": "low",
            "lowest": "low",
        }
        prio = prio_map.get(prio, "medium")

        labels = getattr(issue.fields, "labels", []) or []
        tc_type = "positive"
        for lbl in labels:
            if lbl in ("positive", "negative", "edge"):
                tc_type = lbl
                break

        results.append(
            {
                "key": issue.key,
                "title": issue.fields.summary,
                "steps": "\n".join(steps_lines).strip(),
                "expected_result": "\n".join(exp_lines).strip(),
                "priority": prio,
                "type": tc_type,
                "source": "jira",  # flag: came from Jira, not LLM
            }
        )

    results.sort(key=lambda x: int(x["key"].split("-")[-1]))
    return results
