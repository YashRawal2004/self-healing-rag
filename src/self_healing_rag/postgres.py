"""Pooled psycopg connections to Neon. Used by the Flask API and the retriever.

Neon closes idle SSL sockets. The pool pings before checkout and recycles
often; DB helpers retry on OperationalError so a sleeping compute does not 500.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from functools import wraps
from typing import Callable, Iterator, TypeVar

from psycopg import OperationalError
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector

from self_healing_rag.config import DATABASE_URL

_pool: ConnectionPool | None = None

F = TypeVar("F", bound=Callable)


def _configure(conn) -> None:
    register_vector(conn)
    conn.row_factory = dict_row


def init_pool() -> ConnectionPool:
    global _pool
    if _pool is not None:
        return _pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Add the Neon pooled URI to .env")
    _pool = ConnectionPool(
        conninfo=DATABASE_URL,
        min_size=0,
        max_size=10,
        max_idle=60,
        max_lifetime=600,
        timeout=30,
        kwargs={
            "autocommit": False,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 3,
        },
        configure=_configure,
        check=ConnectionPool.check_connection,
        open=True,
    )
    return _pool


def get_pool() -> ConnectionPool:
    if _pool is None:
        return init_pool()
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def retry_on_disconnect(fn: F) -> F:
    """Retry a DB helper when Neon drops the SSL socket."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        delay = 0.25
        last: Exception | None = None
        for _attempt in range(4):
            try:
                return fn(*args, **kwargs)
            except OperationalError as exc:
                last = exc
                time.sleep(delay)
                delay *= 2
        assert last is not None
        raise last

    return wrapper  # type: ignore[return-value]


@contextmanager
def connection() -> Iterator:
    pool = get_pool()
    with pool.connection() as conn:
        try:
            yield conn
            if not conn.closed:
                conn.commit()
        except Exception:
            if not conn.closed:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
