from typing import TypedDict


class GraphState(TypedDict):
    """State schema for the Self-Healing RAG graph.

    Fields:
        original_query: Immutable — the user's original question, used for final grading.
        query:          Mutable — working query that gets rewritten on retries.
        context:        Retrieved document chunks (concatenated text).
        answer:         Latest generated answer.
        feedback:       Reason the last grading step failed, guides the next rewrite.
        doc_grade:      "relevant" | "irrelevant"
        answer_grade:   "good" | "hallucinated" | "incomplete"
        retrieval_retries:      Counter for retrieval loop.
        generation_retries:     Counter for generation loop.
        max_retrieval_retries:  Hard cap for retrieval retries.
        max_generation_retries: Hard cap for generation retries.
    """

    original_query: str
    query: str
    context: str
    answer: str
    feedback: str
    doc_grade: str
    answer_grade: str
    retrieval_retries: int
    generation_retries: int
    max_retrieval_retries: int
    max_generation_retries: int
