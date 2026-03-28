"""Fetch relevant vault nodes by keyword query."""

from __future__ import annotations

import json
import re
from pathlib import Path

from rich.text import Text

from vault.config import VaultConfig, load_config, console

# Characters that separate path segments into tokens
_PATH_SEP_RE = re.compile(r"[/_\-.]")


def _tokenize(text: str) -> set[str]:
    """Split text into lowercase keyword tokens."""
    return {t for t in re.split(r"[\s/_\-.,]+", text.lower()) if t}


def _score_node(query_tokens: set[str], path: str, tags: list[str]) -> int:
    """Score a node by counting how many query tokens appear in its tags and path segments."""
    path_tokens = _tokenize(path)
    tag_tokens = {t.lower() for t in tags}

    score = 0
    for qt in query_tokens:
        # Check exact matches in tags
        if qt in tag_tokens:
            score += 2
        # Check partial matches in path tokens
        for pt in path_tokens:
            if qt in pt:
                score += 1
                break
    return score


def fetch(query: str, config: VaultConfig | None = None, top_n: int = 5) -> None:
    """Fetch and display the most relevant vault nodes for a query."""
    if config is None:
        config = load_config()

    vault_root = Path(config.vault_root)
    index_path = vault_root / config.index_file

    if not index_path.is_file():
        console.print(
            "[bold red]Error:[/] No vault index found.\n"
            "Run [bold cyan]vault index[/] first to build the index."
        )
        raise SystemExit(1)

    data = json.loads(index_path.read_text(encoding="utf-8"))
    nodes = data.get("nodes", {})

    query_tokens = _tokenize(query)
    if not query_tokens:
        console.print("[bold red]Error:[/] Empty query.")
        raise SystemExit(1)

    # Score all nodes
    scored = []
    for path, meta in nodes.items():
        s = _score_node(query_tokens, path, meta.get("tags", []))
        if s > 0:
            scored.append((s, path, meta))

    if not scored:
        console.print(
            f"[bold yellow]Warning:[/] No nodes matched the query [cyan]{query!r}[/].\n"
            "Try running [bold cyan]vault index[/] to refresh, or use different keywords."
        )
        return

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_n]

    # Header
    console.print(f'\n## Fetch Results for: "{query}"')
    console.print(f"### Relevant nodes ({len(top)}):")
    for _score, path, meta in top:
        tags = ", ".join(meta.get("tags", []))
        console.print(f"  - {path} (tags: {tags})")

    # Content
    console.print("\n--- CONTENT ---")
    for _score, path, _meta in top:
        full_path = vault_root / path
        console.print(f"\n### {path}")
        if full_path.is_file():
            console.print(Text(full_path.read_text(encoding="utf-8")))
        else:
            console.print(f"[dim](file not found on disk)[/]")
