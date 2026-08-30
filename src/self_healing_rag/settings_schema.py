"""Per-user settings. Code defaults are copied into user_settings on register."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from self_healing_rag.agent.prompts import MAIN_AGENT_SYSTEM_PROMPT
from self_healing_rag.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    LLM_MODEL,
    MAIN_AGENT_MODEL,
    MAX_GENERATION_RETRIES,
    MAX_RETRIEVAL_RETRIES,
    TOP_K,
)
from self_healing_rag.rag.prompts import (
    ANSWER_GRADER_PROMPT,
    DOC_GRADER_PROMPT,
    GENERATE_PROMPT,
    GENERATE_RETRY_PROMPT,
    QUERY_REWRITER_PROMPT,
)


class Models(BaseModel):
    model_config = ConfigDict(extra="ignore")

    agent: str
    grade_documents: str
    transform_query: str
    generate: str
    grade_answer: str

    @field_validator(
        "agent",
        "grade_documents",
        "transform_query",
        "generate",
        "grade_answer",
        mode="before",
    )
    @classmethod
    def strip_id(cls, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("model id cannot be empty")
        return text


class Prompts(BaseModel):
    model_config = ConfigDict(extra="ignore")

    agent_system: str
    doc_grader: str
    query_rewriter: str
    generate: str
    generate_retry: str
    answer_grader: str

    @field_validator(
        "agent_system",
        "doc_grader",
        "query_rewriter",
        "generate",
        "generate_retry",
        "answer_grader",
        mode="before",
    )
    @classmethod
    def non_empty(cls, value: Any) -> str:
        text = str(value)
        if not text.strip():
            raise ValueError("prompt cannot be empty")
        return text

    @model_validator(mode="after")
    def required_placeholders(self) -> Prompts:
        checks = {
            "doc_grader": ("{query}", "{context}"),
            "query_rewriter": ("{original_query}", "{query}", "{feedback}"),
            "generate": ("{context}", "{query}"),
            "generate_retry": ("{context}", "{query}", "{feedback}"),
            "answer_grader": ("{original_query}", "{context}", "{answer}"),
        }
        for field, tokens in checks.items():
            text = getattr(self, field)
            missing = [token for token in tokens if token not in text]
            if missing:
                raise ValueError(f"{field} must contain {', '.join(missing)}")
        return self


class Retrieval(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chunk_size: int = Field(ge=200, le=4000)
    chunk_overlap: int = Field(ge=0, le=2000)
    top_k: int = Field(ge=1, le=20)

    @model_validator(mode="after")
    def overlap_lt_size(self) -> Retrieval:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self


class Budgets(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_retrieval_retries: int = Field(ge=0, le=10)
    max_generation_retries: int = Field(ge=0, le=10)


class UserSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    models: Models
    prompts: Prompts
    retrieval: Retrieval
    budgets: Budgets


def default_settings() -> UserSettings:
    return UserSettings(
        models=Models(
            agent=MAIN_AGENT_MODEL,
            grade_documents=LLM_MODEL,
            transform_query=LLM_MODEL,
            generate=LLM_MODEL,
            grade_answer=LLM_MODEL,
        ),
        prompts=Prompts(
            agent_system=MAIN_AGENT_SYSTEM_PROMPT,
            doc_grader=DOC_GRADER_PROMPT,
            query_rewriter=QUERY_REWRITER_PROMPT,
            generate=GENERATE_PROMPT,
            generate_retry=GENERATE_RETRY_PROMPT,
            answer_grader=ANSWER_GRADER_PROMPT,
        ),
        retrieval=Retrieval(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            top_k=TOP_K,
        ),
        budgets=Budgets(
            max_retrieval_retries=MAX_RETRIEVAL_RETRIES,
            max_generation_retries=MAX_GENERATION_RETRIES,
        ),
    )


def parse_settings(raw: Any) -> UserSettings:
    """Merge raw JSON with defaults so newly added fields fill in."""
    base = default_settings().model_dump()
    incoming = raw if isinstance(raw, dict) else {}
    for key in ("models", "prompts", "retrieval", "budgets"):
        if isinstance(incoming.get(key), dict):
            base[key] = {**base[key], **incoming[key]}
    return UserSettings.model_validate(base)
