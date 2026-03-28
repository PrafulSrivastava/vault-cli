"""Configuration loading and validation for vault CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import io
import sys

from pydantic import BaseModel, Field
from rich.console import Console


def _make_console() -> Console:
    """Console with UTF-8 output — avoids cp1252 crashes on Windows terminals."""
    if hasattr(sys.stdout, "buffer"):
        safe_stdout = io.TextIOWrapper(
            sys.stdout.buffer,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )
        return Console(file=safe_stdout)
    return Console()


console = _make_console()

CONFIG_FILENAME = "vault.config.json"


class VaultConfig(BaseModel):
    """Schema for vault.config.json."""

    vault_root: str
    attachments_dir: str = "attachments"
    processed_dir: str = "attachments/processed"
    index_file: str = "_vault_index.json"
    stale_threshold_days: int = Field(default=30, description="Days before a node is considered stale")


def find_config_file(start: Optional[Path] = None) -> Path:
    """Walk up the directory tree to find vault.config.json, similar to how git finds .git."""
    current = start or Path.cwd()
    while True:
        candidate = current / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    console.print(
        f"[bold red]Error:[/] Could not find {CONFIG_FILENAME} in any parent directory.\n"
        "Run [bold cyan]vault init[/] to create a new vault."
    )
    raise SystemExit(1)


def load_config(start: Optional[Path] = None) -> VaultConfig:
    """Load and validate the vault configuration."""
    config_path = find_config_file(start)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return VaultConfig(**data)


def write_config(config: VaultConfig, target_dir: Path) -> Path:
    """Write vault.config.json to the target directory."""
    config_path = target_dir / CONFIG_FILENAME
    config_path.write_text(
        json.dumps(config.model_dump(), indent=2) + "\n",
        encoding="utf-8",
    )
    return config_path
