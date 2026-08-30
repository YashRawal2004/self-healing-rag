"""CLI entry — the web UI is the supported product."""


def main() -> None:
    print(
        "The terminal agent is retired. Run the web UI:\n"
        "  uv run self-healing-rag-server\n"
        "  cd web && npm run dev"
    )
