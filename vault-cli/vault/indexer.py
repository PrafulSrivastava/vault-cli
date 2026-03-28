"""Index all markdown nodes in the vault."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import frontmatter

from vault.config import VaultConfig, load_config, console

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def _extract_node(md_path: Path, vault_root: Path) -> dict[str, Any]:
    """Extract metadata from a single markdown file."""
    post = frontmatter.load(str(md_path))
    text: str = post.content

    # Tags from frontmatter — normalise to list of strings
    raw_tags = post.get("tags", [])
    if isinstance(raw_tags, str):
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
    elif isinstance(raw_tags, list):
        tags = [str(t) for t in raw_tags]
    else:
        tags = []

    # Wikilinks
    links = WIKILINK_RE.findall(text)

    # Word count (simple whitespace split)
    word_count = len(text.split())

    # Timestamps
    stat = md_path.stat()
    last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

    created = post.get("created")
    if created is not None:
        if isinstance(created, datetime):
            created = created.isoformat()
        else:
            created = str(created)

    return {
        "tags": tags,
        "links": links,
        "word_count": word_count,
        "last_modified": last_modified,
        "created": created,
    }


def build_index(config: VaultConfig | None = None, verbose: bool = True) -> dict[str, Any]:
    """Walk the vault and build the full index."""
    if config is None:
        config = load_config()

    vault_root = Path(config.vault_root)
    attachments = Path(config.attachments_dir)
    # Resolve the attachments directory relative to vault root for exclusion
    attachments_abs = (vault_root / attachments).resolve()

    start = time.perf_counter()
    nodes: dict[str, Any] = {}
    total_links = 0

    for md_path in sorted(vault_root.rglob("*.md")):
        # Skip anything inside the attachments directory
        try:
            md_path.resolve().relative_to(attachments_abs)
            continue
        except ValueError:
            pass

        rel = md_path.relative_to(vault_root).as_posix()
        node = _extract_node(md_path, vault_root)
        nodes[rel] = node
        total_links += len(node["links"])

    elapsed = time.perf_counter() - start

    index = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "nodes": nodes,
    }

    # Write index
    index_path = vault_root / config.index_file
    index_path.write_text(json.dumps(index, indent=2, default=str) + "\n", encoding="utf-8")

    if verbose:
        console.print(f"\n[bold green]Index built successfully.[/]")
        console.print(f"  Total nodes indexed: [cyan]{len(nodes)}[/]")
        console.print(f"  Total links found:   [cyan]{total_links}[/]")
        console.print(f"  Time taken:          [cyan]{elapsed:.2f}s[/]")
        console.print(f"  Written to:          [dim]{index_path}[/]\n")

    return index
