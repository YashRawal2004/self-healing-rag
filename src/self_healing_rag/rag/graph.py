"""LangGraph assembly — nodes, edges, and routing logic."""

from langgraph.graph import END, StateGraph

from .events import emit
from .nodes import generate, grade_answer, grade_documents, retrieve, transform_query
from .state import GraphState


# ── Router functions ─────────────────────────────────────────────────────────

def route_after_doc_grade(state: GraphState) -> str:
    """Decide what to do after grading the retrieved documents."""
    if state["doc_grade"] == "relevant":
        return "generate"

    # An empty store returns nothing no matter how the query is worded, so
    # skip the rewrite loop instead of burning the whole budget on it.
    if not state["context"].strip():
        print("\n⛔ Nothing in the vector store to retrieve — skipping retries")
        return "end_fallback"

    # Documents are irrelevant — check retrieval budget
    if state["retrieval_retries"] >= state["max_retrieval_retries"]:
        print(f"\n⛔ Retrieval retries exhausted ({state['retrieval_retries']}/{state['max_retrieval_retries']})")
        return "end_fallback"

    print(f"   ↩ Retrieval retry {state['retrieval_retries'] + 1}/{state['max_retrieval_retries']}")
    return "transform_query"


def route_after_answer_grade(state: GraphState) -> str:
    """Decide what to do after grading the generated answer."""
    if state["answer_grade"] == "good":
        return "end_success"

    if state["answer_grade"] == "hallucinated":
        # Generation problem — check generation budget
        if state["generation_retries"] >= state["max_generation_retries"]:
            print(f"\n⛔ Generation retries exhausted ({state['generation_retries']}/{state['max_generation_retries']})")
            return "end_best_effort"

        print(f"   ↩ Generation retry {state['generation_retries'] + 1}/{state['max_generation_retries']}")
        return "generate"

    # Incomplete — retrieval/query problem
    if state["retrieval_retries"] >= state["max_retrieval_retries"]:
        print(f"\n⛔ Retrieval retries exhausted ({state['retrieval_retries']}/{state['max_retrieval_retries']})")
        return "end_best_effort"

    print(f"   ↩ Retrieval retry {state['retrieval_retries'] + 1}/{state['max_retrieval_retries']} (incomplete answer)")
    return "transform_query"


# ── Retry counter nodes ──────────────────────────────────────────────────────
# These are thin wrapper nodes that increment the appropriate counter
# before passing control to the next node. This keeps Transform Query clean
# since it's shared by both retrieval and generation paths.

def increment_retrieval_retry(state: GraphState) -> dict:
    """Increment retrieval retry counter before looping back."""
    used = state["retrieval_retries"] + 1
    emit(
        "retry",
        "Retrying retrieval",
        f"attempt {used} of {state['max_retrieval_retries']}",
        kind="retrieval",
    )
    return {"retrieval_retries": used}


def increment_generation_retry(state: GraphState) -> dict:
    """Increment generation retry counter before regenerating."""
    used = state["generation_retries"] + 1
    emit(
        "retry",
        "Retrying generation",
        f"attempt {used} of {state['max_generation_retries']}",
        kind="generation",
    )
    return {"generation_retries": used}


# ── Fallback / end nodes ─────────────────────────────────────────────────────

def end_fallback(state: GraphState) -> dict:
    """Produce a fallback response when retrieval retries are exhausted."""
    print(f"\n{'='*60}")
    print("🚫 END — FALLBACK (could not find relevant documents)")
    emit(
        "fallback",
        "Gave up",
        "the knowledge base looks empty"
        if not state["context"].strip()
        else "no relevant documents after every retry",
    )
    return {
        "answer": (
            "I'm sorry, I couldn't find relevant information in this chat's "
            "documents. Upload a PDF here, or try rephrasing the question."
        ),
        "answer_grade": "fallback",
    }


def end_best_effort(state: GraphState) -> dict:
    """Return the best-effort answer with a caveat."""
    print(f"\n{'='*60}")
    print("⚠️  END — BEST EFFORT (retries exhausted)")
    emit("best_effort", "Returning best effort", "retry budget exhausted")
    caveat = (
        "\n\n---\n⚠️ **Note:** This answer may not be fully accurate or complete. "
        "The system exhausted its retry budget while trying to improve the response."
    )
    return {
        "answer": state["answer"] + caveat,
        "answer_grade": "best_effort",
    }


# ── Build the graph ──────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Assemble and compile the Self-Healing RAG graph."""
    workflow = StateGraph(GraphState)

    # ── Add nodes ──
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("transform_query", transform_query)
    workflow.add_node("generate", generate)
    workflow.add_node("grade_answer", grade_answer)
    workflow.add_node("increment_retrieval_retry", increment_retrieval_retry)
    workflow.add_node("increment_generation_retry", increment_generation_retry)
    workflow.add_node("end_fallback", end_fallback)
    workflow.add_node("end_best_effort", end_best_effort)

    # ── Entry point ──
    workflow.set_entry_point("retrieve")

    # ── Fixed edges ──
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_edge("increment_retrieval_retry", "transform_query")
    workflow.add_edge("transform_query", "retrieve")
    workflow.add_edge("generate", "grade_answer")
    workflow.add_edge("increment_generation_retry", "generate")
    workflow.add_edge("end_fallback", END)
    workflow.add_edge("end_best_effort", END)

    # ── Conditional edges ──
    workflow.add_conditional_edges(
        "grade_documents",
        route_after_doc_grade,
        {
            "generate": "generate",
            "transform_query": "increment_retrieval_retry",
            "end_fallback": "end_fallback",
        },
    )

    workflow.add_conditional_edges(
        "grade_answer",
        route_after_answer_grade,
        {
            "end_success": END,
            "generate": "increment_generation_retry",
            "transform_query": "increment_retrieval_retry",
            "end_best_effort": "end_best_effort",
        },
    )

    return workflow.compile()
