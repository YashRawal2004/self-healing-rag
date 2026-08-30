from typing import Literal

from pydantic import BaseModel, Field


class DocGradeResponse(BaseModel):
    """Structured response from the document relevance grader."""

    evidence: str = Field(
        default="",
        description=(
            "Verbatim span from the documents that could contribute to an answer. "
            "Empty only if nothing in the documents relates to the query. Filled "
            "in before grading, so the grade follows the evidence."
        ),
    )
    grade: Literal["relevant", "irrelevant"] = Field(
        description="Whether the retrieved documents are relevant to the query"
    )
    feedback: str = Field(
        default="",
        description="Explanation of why documents are irrelevant. Empty string if relevant.",
    )


class AnswerGradeResponse(BaseModel):
    """Structured response from the answer grader."""

    grade: Literal["good", "hallucinated", "incomplete"] = Field(
        description="Quality grade of the generated answer"
    )
    feedback: str = Field(
        default="",
        description="Explanation of what is wrong with the answer. Empty string if good.",
    )


class RewrittenQuery(BaseModel):
    """Structured response from the query rewriter."""

    query: str = Field(
        description="The rewritten query optimized for better retrieval results"
    )
