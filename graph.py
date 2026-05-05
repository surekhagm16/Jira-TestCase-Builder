"""
LangGraph state machine — nodes, state schema, and graph builder.

LLM provider: Groq (llama3-70b-8192).
To swap provider, change only the LLM_MODEL / import in _get_llm().
The rest of the graph is provider-agnostic.
"""

import json
from typing import TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from prompts import TEST_CASE_PROMPT
from rag_pipeline import retrieve_context

# ── LLM config (change here to swap provider) ────────────────────────────────
LLM_MODEL = "llama-3.3-70b-versatile"  # or "llama3-8b-8192" / "mixtral-8x7b-32768"
LLM_TEMPERATURE = 0.2


def _get_llm(llm_key: str) -> ChatGroq:
    """
    Instantiate the LLM. Only this function needs to change when
    switching providers (e.g. swap ChatGroq for ChatOpenAI).
    """
    return ChatGroq(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=llm_key,
    )


# ── State schema ──────────────────────────────────────────────────────────────


class GraphState(TypedDict):
    # inputs
    stories: list[dict]
    llm_key: str  # single key, provider-agnostic name

    # runtime
    current_story_index: int
    current_story: dict
    retrieved_context: str
    generated_test_cases: list[dict]

    # HITL output (written by Streamlit UI before graph resumes)
    approved_test_cases: list[dict]

    # accumulator
    all_approved: dict  # story_key -> list[dict]


# ── Node functions ────────────────────────────────────────────────────────────


def select_story(state: GraphState) -> GraphState:
    """Pick the story at current_story_index."""
    idx = state.get("current_story_index", 0)
    state["current_story"] = state["stories"][idx]
    return state


def rag_retrieve(state: GraphState) -> GraphState:
    """Retrieve similar context from the vector store for the current story."""
    context = retrieve_context(query=state["current_story"]["summary"])
    state["retrieved_context"] = context
    return state


def generate_test_cases(state: GraphState) -> GraphState:
    """Call the LLM to produce test cases for the current story."""
    story = state["current_story"]
    llm = _get_llm(state["llm_key"])

    prompt = TEST_CASE_PROMPT.format(
        summary=story["summary"],
        description=story["description"] or "No description provided.",
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content.strip()

    # Strip accidental markdown fences
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1].lstrip("json").strip() if len(parts) > 1 else content

    try:
        test_cases = json.loads(content.strip())
    except json.JSONDecodeError:
        test_cases = [
            {
                "title": "LLM output could not be parsed",
                "type": "edge",
                "priority": "medium",
                "steps": response.content,
            }
        ]

    state["generated_test_cases"] = test_cases
    return state


def human_review(state: GraphState) -> GraphState:
    """
    HITL pause point.
    LangGraph interrupts before this node; the Streamlit UI handles
    approval/rejection and resumes the graph with approved_test_cases set.
    """
    return state


def save_approved(state: GraphState) -> GraphState:
    """Accumulate approved test cases keyed by story key."""
    story_key = state["current_story"]["key"]
    all_approved = state.get("all_approved", {})
    all_approved[story_key] = state.get("approved_test_cases", [])
    state["all_approved"] = all_approved
    return state


# ── Routing ───────────────────────────────────────────────────────────────────


def route_next(state: GraphState) -> str:
    """Advance to next story or end the graph."""
    next_idx = state["current_story_index"] + 1
    if next_idx < len(state["stories"]):
        state["current_story_index"] = next_idx
        return "next_story"
    return "done"


# ── Graph builder ─────────────────────────────────────────────────────────────


def build_graph() -> StateGraph:
    memory = MemorySaver()
    builder = StateGraph(GraphState)

    builder.add_node("select_story", select_story)
    builder.add_node("rag_retrieve", rag_retrieve)
    builder.add_node("generate_test_cases", generate_test_cases)
    builder.add_node("human_review", human_review)
    builder.add_node("save_approved", save_approved)

    builder.set_entry_point("select_story")
    builder.add_edge("select_story", "rag_retrieve")
    builder.add_edge("rag_retrieve", "generate_test_cases")
    builder.add_edge("generate_test_cases", "human_review")
    builder.add_edge("human_review", "save_approved")
    builder.add_conditional_edges(
        "save_approved",
        route_next,
        {"next_story": "select_story", "done": END},
    )

    return builder.compile(
        checkpointer=memory,
        interrupt_before=["human_review"],
    )
