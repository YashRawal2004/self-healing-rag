"""Main agent — decides when to consult the documents and when to answer directly."""

from __future__ import annotations

from typing import Any

__all__ = ["build_main_agent", "ask_documents"]


def __getattr__(name: str) -> Any:
    if name == "build_main_agent":
        from .graph import build_main_agent

        return build_main_agent
    if name == "ask_documents":
        from .tools import ask_documents

        return ask_documents
    raise AttributeError(name)
