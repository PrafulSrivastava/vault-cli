"""Vault CLI — main entry point."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.table import Table
from rich.text import Text

from vault.config import VaultConfig, write_config, load_config, console

app = typer.Typer(
    name="vault",
    help="CLI tool for managing a structured knowledge base alongside an Obsidian vault.",
    no_args_is_help=True,
)


@app.command()
def init() -> None:
    """Initialise a new vault in the current directory."""
    cwd = Path.cwd()
    config = VaultConfig(vault_root=str(cwd))

    # Create directories
    (cwd / config.attachments_dir).mkdir(parents=True, exist_ok=True)
    (cwd / config.processed_dir).mkdir(parents=True, exist_ok=True)
    (cwd / "vault").mkdir(exist_ok=True)

    # Write config
    config_path = write_config(config, cwd)

    console.print("\n[bold green]Vault initialised successfully![/]\n")
    console.print(f"  Config:      [cyan]{config_path}[/]")
    console.print(f"  Vault root:  [cyan]{cwd}[/]")
    console.print(f"  Attachments: [cyan]{cwd / config.attachments_dir}[/]")
    console.print(f"  Processed:   [cyan]{cwd / config.processed_dir}[/]")
    console.print(f"  Vault dir:   [cyan]{cwd / 'vault'}[/]\n")


@app.command()
def index() -> None:
    """Build the vault index from all markdown files."""
    from vault.indexer import build_index

    build_index()


@app.command()
def ingest(
    source: str = typer.Argument(..., help="File path (.pdf, .md, .txt) or URL to ingest"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-ingest even if already processed"),
) -> None:
    """Ingest a file or URL and print a context bundle for LLM processing."""
    from vault.ingestor import ingest as do_ingest

    do_ingest(source, force=force)


@app.command()
def ingest_all() -> None:
    """Ingest all unprocessed files in the attachments directory."""
    from vault.ingestor import ingest as do_ingest

    config = load_config()
    vault_root = Path(config.vault_root)
    attachments_dir = vault_root / config.attachments_dir
    processed_dir = vault_root / config.processed_dir

    if not attachments_dir.is_dir():
        console.print(f"[bold red]Error:[/] Attachments directory not found: [cyan]{attachments_dir}[/]")
        raise typer.Exit(1)

    pending = [
        f for f in sorted(attachments_dir.iterdir())
        if f.is_file()
        and f.suffix.lower() in (".pdf", ".md", ".txt")
        and not (processed_dir / f.name).exists()
    ]

    if not pending:
        console.print("[bold yellow]No unprocessed files found in attachments/[/]")
        return

    console.print(f"\n[bold]Found {len(pending)} unprocessed file(s):[/]")
    for f in pending:
        label = Text("  - ", style="dim")
        label.append(f.name)
        console.print(label)
    console.print()

    for i, f in enumerate(pending, 1):
        header = Text(f"--- [{i}/{len(pending)}] ", style="bold cyan")
        header.append(f.name, style="bold cyan")
        header.append(" ---", style="bold cyan")
        console.print(header)
        do_ingest(str(f), config=config)
        console.print()

    console.print(f"[bold green]Done.[/] Ingested {len(pending)} file(s).\n")


@app.command()
def fetch(query: str = typer.Argument(..., help="Keyword query to search the vault")) -> None:
    """Fetch relevant vault nodes matching a keyword query."""
    from vault.fetcher import fetch as do_fetch

    do_fetch(query)


@app.command()
def status() -> None:
    """Print a dashboard showing the current vault status."""
    config = load_config()
    vault_root = Path(config.vault_root)
    index_path = vault_root / config.index_file

    if not index_path.is_file():
        console.print(
            "[bold red]Error:[/] No vault index found.\n"
            "Run [bold cyan]vault index[/] first."
        )
        raise typer.Exit(1)

    data = json.loads(index_path.read_text(encoding="utf-8"))
    nodes = data.get("nodes", {})
    generated_at = data.get("generated_at", "unknown")

    total_nodes = len(nodes)
    total_links = sum(len(m.get("links", [])) for m in nodes.values())

    # Unprocessed files in attachments/ that are not in processed/
    attachments_dir = vault_root / config.attachments_dir
    processed_dir = vault_root / config.processed_dir
    unprocessed = 0
    if attachments_dir.is_dir():
        for f in attachments_dir.iterdir():
            if f.is_file() and f.suffix.lower() in (".pdf", ".md", ".txt"):
                if not (processed_dir / f.name).exists():
                    unprocessed += 1

    # Stale nodes
    now = datetime.now(tz=timezone.utc)
    stale_threshold = config.stale_threshold_days
    stale_nodes: list[tuple[str, int]] = []
    for path, meta in nodes.items():
        last_mod = meta.get("last_modified")
        if last_mod:
            try:
                dt = datetime.fromisoformat(last_mod)
                age_days = (now - dt).days
                if age_days > stale_threshold:
                    stale_nodes.append((path, age_days))
            except (ValueError, TypeError):
                pass

    stale_nodes.sort(key=lambda x: x[1], reverse=True)

    # Format last indexed time
    try:
        indexed_dt = datetime.fromisoformat(generated_at)
        last_indexed = indexed_dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        last_indexed = str(generated_at)

    # Dashboard
    console.print()
    table = Table(title="Vault Status", show_header=False, title_style="bold")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")
    table.add_column("Note", style="dim")

    table.add_row("Total nodes", str(total_nodes), "")
    table.add_row("Total links", str(total_links), "")
    table.add_row("Unprocessed files", str(unprocessed), "files in attachments/ not yet processed")
    table.add_row("Stale nodes", str(len(stale_nodes)), f"not updated in >{stale_threshold} days")
    table.add_row("Last indexed", last_indexed, "")

    console.print(table)

    if stale_nodes:
        console.print("\n[bold]Stale nodes:[/]")
        for path, age in stale_nodes:
            console.print(f"  - {path}  [dim]({age} days old)[/]")
    console.print()
