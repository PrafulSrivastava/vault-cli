"""Ingest external files or URLs into the vault context."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from rich.text import Text

from vault.config import VaultConfig, load_config, console


def _is_url(source: str) -> bool:
    """Check if the source looks like a URL."""
    parsed = urlparse(source)
    return parsed.scheme in ("http", "https")


def _extract_pdf(path: Path) -> str:
    """Convert PDF to markdown using pymupdf4llm."""
    import pymupdf4llm  # lazy import — heavy dependency

    return pymupdf4llm.to_markdown(str(path))


def _extract_url(url: str) -> str:
    """Extract main content from a URL using trafilatura."""
    import trafilatura  # lazy import

    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        console.print(f"[bold red]Error:[/] Failed to download content from [cyan]{url}[/]")
        raise SystemExit(1)
    text = trafilatura.extract(downloaded)
    if text is None:
        console.print(f"[bold red]Error:[/] Could not extract readable content from [cyan]{url}[/]")
        raise SystemExit(1)
    return text


def _read_text_file(path: Path) -> str:
    """Read a .md or .txt file directly."""
    return path.read_text(encoding="utf-8")


def _load_index_summary(config: VaultConfig) -> str:
    """Load the vault index and produce a compact summary."""
    index_path = Path(config.vault_root) / config.index_file
    if not index_path.is_file():
        return "(No index found — run `vault index` first)"

    data = json.loads(index_path.read_text(encoding="utf-8"))
    nodes = data.get("nodes", {})
    total = len(nodes)

    # Tag distribution
    tag_counter: Counter[str] = Counter()
    link_counter: Counter[str] = Counter()
    for path_key, meta in nodes.items():
        for t in meta.get("tags", []):
            tag_counter[t] += 1
        for link in meta.get("links", []):
            link_counter[link] += 1

    top_tags = tag_counter.most_common(10)
    top_linked = link_counter.most_common(5)

    lines = [
        f"Total nodes: {total}",
        f"Top tags: {', '.join(f'{t}({c})' for t, c in top_tags)}" if top_tags else "No tags found",
    ]
    if top_linked:
        lines.append(f"Most-linked nodes: {', '.join(f'{n}({c})' for n, c in top_linked)}")

    return "\n".join(lines)


def ingest(source: str, config: VaultConfig | None = None, force: bool = False) -> None:
    """Ingest a file or URL and print a formatted context bundle."""
    from vault.indexer import build_index

    if config is None:
        config = load_config()

    vault_root = Path(config.vault_root)
    is_url = _is_url(source)
    source_label = source

    # Extract content
    if is_url:
        content = _extract_url(source)
    else:
        path = Path(source)
        if not path.is_file():
            console.print(f"[bold red]Error:[/] File not found: [cyan]{source}[/]")
            raise SystemExit(1)

        # Guard: warn if already processed
        processed_dir = vault_root / config.processed_dir
        already_processed = processed_dir / path.name
        if already_processed.exists() and not force:
            console.print(
                f"[bold yellow]Skipped:[/] [cyan]{path.name}[/] was already processed.\n"
                f"  It exists at: [dim]{already_processed}[/]\n"
                f"  Use [bold]--force[/] to ingest again."
            )
            return

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            content = _extract_pdf(path)
        elif suffix in (".md", ".txt"):
            content = _read_text_file(path)
        else:
            console.print(f"[bold red]Error:[/] Unsupported file type: [cyan]{suffix}[/]")
            raise SystemExit(1)

        source_label = path.name

    # Always rebuild the index before generating the context bundle so the
    # vault summary reflects the current state of all notes.
    console.print("[dim]Re-indexing vault...[/]")
    build_index(config, verbose=False)

    # Build the context bundle
    index_summary = _load_index_summary(config)

    output = f"""## Ingest Context
### Source: {source_label}
### Vault Index Summary
{index_summary}

### Document Content
{content}

---
INSTRUCTIONS FOR LLM:
You are updating a knowledge vault. Based on the document above and the vault index summary:
1. List which existing nodes should be updated and what to add (reference by path)
2. List any new nodes to create (suggest path, tags, and content)
3. List any new [[wikilinks]] to add between nodes
Respond with a structured edit plan."""

    console.print(Text(output))

    # Move local file to processed
    if not is_url:
        processed_dir = vault_root / config.processed_dir
        processed_dir.mkdir(parents=True, exist_ok=True)
        dest = processed_dir / Path(source).name
        shutil.move(str(Path(source)), str(dest))
        console.print(f"\n[dim]Moved source file to {dest}[/]")
