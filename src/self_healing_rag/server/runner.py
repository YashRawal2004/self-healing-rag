"""Runs one conversational turn and streams its progress as SSE."""

from __future__ import annotations

import json
import queue
import threading
from typing import Any, Iterator

from self_healing_rag.agent import build_main_agent
from self_healing_rag.rag.events import collect
from self_healing_rag.rag.runtime import RunContext, use_run
from self_healing_rag.settings_schema import UserSettings

from . import db

_DONE = object()


def _text_of(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content)


def _frame(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def stream_turn(
    user_id: str,
    chat_id: str,
    user_message: str,
    settings: UserSettings,
    api_key: str,
) -> Iterator[str]:
    saved_user = db.add_message(user_id, chat_id, "user", user_message)
    yield _frame({"type": "user", "message": saved_user})

    new_title = db.set_auto_title(user_id, chat_id, user_message)
    if new_title:
        yield _frame({"type": "title", "title": new_title})

    history = [
        {"role": message["role"], "content": message["content"]}
        for message in db.get_messages(user_id, chat_id)
    ]

    events: queue.Queue = queue.Queue()
    outcome: dict[str, Any] = {}
    run_ctx = RunContext(
        user_id=user_id,
        chat_id=chat_id,
        api_key=api_key,
        settings=settings.model_dump(),
    )

    def worker() -> None:
        try:
            agent = build_main_agent(settings, api_key)
            with collect(events.put), use_run(run_ctx):
                result = agent.invoke({"messages": history})
            outcome["answer"] = _text_of(result["messages"][-1])
        except Exception as exc:
            outcome["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            events.put(_DONE)

    thread = threading.Thread(target=worker, name=f"turn-{chat_id[:8]}", daemon=True)
    thread.start()

    trace: list[dict] = []
    while True:
        event = events.get()
        if event is _DONE:
            break
        trace.append(event)
        yield _frame({"type": "step", "step": event})

    thread.join()

    if "error" in outcome:
        db.delete_message(user_id, saved_user["id"])
        yield _frame({"type": "error", "error": outcome["error"]})
        yield _frame({"type": "done"})
        return

    saved_answer = db.add_message(user_id, chat_id, "assistant", outcome["answer"], trace)
    db.touch_chat(user_id, chat_id)
    yield _frame({"type": "answer", "message": saved_answer})
    yield _frame({"type": "done"})
