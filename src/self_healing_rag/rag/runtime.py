"""Per-turn RAG context. Set inside the worker thread that runs the agent."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass
class RunContext:
    user_id: str
    chat_id: str
    api_key: str
    settings: dict[str, Any]


_run: ContextVar[RunContext | None] = ContextVar("rag_run", default=None)


def current_run() -> RunContext:
    ctx = _run.get()
    if ctx is None:
        raise RuntimeError("RAG run context is not set")
    return ctx


@contextmanager
def use_run(ctx: RunContext) -> Iterator[None]:
    token = _run.set(ctx)
    try:
        yield
    finally:
        _run.reset(token)
