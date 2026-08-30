"""The Self-Healing RAG graph exposed as a tool for the main agent."""

from langchain_core.tools import tool
from langgraph.errors import GraphRecursionError

from self_healing_rag.config import RAG_RECURSION_LIMIT
from self_healing_rag.rag import build_graph
from self_healing_rag.rag.events import emit
from self_healing_rag.rag.runtime import current_run

_RAG_APP = build_graph()


def _initial_state(question: str) -> dict:
    budgets = current_run().settings["budgets"]
    return {
        "original_query": question,
        "query": question,
        "context": "",
        "answer": "",
        "feedback": "",
        "doc_grade": "",
        "answer_grade": "",
        "retrieval_retries": 0,
        "generation_retries": 0,
        "max_retrieval_retries": budgets["max_retrieval_retries"],
        "max_generation_retries": budgets["max_generation_retries"],
    }


@tool
def ask_documents(question: str) -> dict:
    """Search this chat's document knowledge base and return a grounded answer.

    Use this for any question about content, facts, or details that could
    plausibly be found in the documents uploaded to this chat. Pass a complete,
    standalone question — this tool cannot see the conversation, so resolve any
    pronouns or references before calling it.

    Returns a dict with:
      answer            — the grounded answer, or a message saying nothing
                          relevant was found in the documents
      original_query    — the question as it was passed in
      transformed_query — the rewritten question, if the internal retrieval
                          loop had to reword it to find results; otherwise None
    """
    print(f"\n{'-'*60}")
    print(f"  [RAG TOOL] entering self-healing loop: \"{question}\"")
    emit("tool_start", "Consulting the knowledge base", f"“{question}”", question=question)

    try:
        final = _RAG_APP.invoke(
            _initial_state(question),
            config={"recursion_limit": RAG_RECURSION_LIMIT},
        )
    except GraphRecursionError:
        print(f"{'-'*60}\n")
        emit("tool_error", "Search did not converge", "step limit reached")
        return {
            "answer": (
                "The document search did not converge — it exceeded its step "
                "limit before producing an answer."
            ),
            "original_query": question,
            "transformed_query": None,
        }
    except Exception as exc:
        print(f"{'-'*60}\n")
        emit("tool_error", "Search failed", str(exc))
        return {
            "answer": f"The document search failed with an error: {exc}",
            "original_query": question,
            "transformed_query": None,
        }

    print(f"  [RAG TOOL] done — grade: {final['answer_grade']}")
    print(f"{'-'*60}\n")

    rewritten = final["query"] if final["query"] != final["original_query"] else None
    return {
        "answer": final["answer"],
        "original_query": final["original_query"],
        "transformed_query": rewritten,
    }
