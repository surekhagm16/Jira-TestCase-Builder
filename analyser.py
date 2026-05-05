"""
analyser.py — Requirements quality analyser.

Uses the LLM to evaluate each story across:
  clarity, ambiguity, consistency, readability
Returns structured scores and suggestions.
"""

import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from prompts import REQUIREMENTS_ANALYSIS_PROMPT

load_dotenv()


def analyse_story(story: dict) -> dict:
    """
    Analyse a single story for requirements quality.
    Returns parsed analysis dict or an error dict.
    """
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        api_key=os.getenv("LLM_KEY", ""),
    )

    prompt = REQUIREMENTS_ANALYSIS_PROMPT.format(
        key=story.get("key", ""),
        summary=story.get("summary", ""),
        description=story.get("description", "No description provided."),
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content.strip()

    # Strip accidental markdown fences
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1].lstrip("json").strip() if len(parts) > 1 else content

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": f"Could not parse LLM response: {content[:200]}"}
