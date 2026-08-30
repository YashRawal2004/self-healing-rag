"""Optional trace sink for the self-healing loop.

The graph's nodes narrate themselves with `print` for CLI use. A UI needs the
same narration as structured data, but only while a request is in flight — so
the sink is a context variable rather than a module global. With no sink
installed `emit` does nothing, which is what keeps the agent CLI and
`self-healing-rag-loop` behaving exactly as they did before.

The sink is per-context, not per-process, so two concurrent requests each see
only their own steps. Install it inside whichever thread runs the graph —
a fresh thread does not inherit the caller's context.
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Any, Callable, Iterator

Event = dict[str, Any]
Sink = Callable[[Event], None]

_sink: contextvars.ContextVar[Sink | None] = contextvars.ContextVar(
    "rag_trace_sink", default=None
)


def emit(node: str, label: str, detail: str = "", **extra: Any) -> None:
    """Report one step of the loop to the active sink, if there is one.

    Args:
        node:   Stable machine name of the step, e.g. "retrieve". The UI keys
                its icons off this, so keep the vocabulary small.
        label:  Short human-readable heading, e.g. "Retrieving".
        detail: One-line specifics, e.g. "4 chunks (3812 chars)".
        extra:  Any further fields to pass through verbatim.
    """
    sink = _sink.get()
    if sink is None:
        return

    event: Event = {"node": node, "label": label, "detail": detail}
    event.update(extra)

    # A broken consumer must not take the graph down with it — the answer is
    # still worth returning even if nobody is listening to the narration.
    try:
        sink(event)
    except Exception:  # pragma: no cover - defensive
        pass


@contextmanager
def collect(sink: Sink) -> Iterator[None]:
    """Route `emit` calls to `sink` for the duration of the block."""
    token = _sink.set(sink)
    try:
        yield
    finally:
        _sink.reset(token)
