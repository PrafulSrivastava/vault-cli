# vault-cli

CLI tool for managing a structured knowledge base that runs alongside an Obsidian vault.

## Install

```bash
cd vault-cli
pip install -e .
```

## Commands

### `vault init`

Initialise a new vault in the current directory. Creates `attachments/`, `attachments/processed/`, `vault/`, and `vault.config.json`.

```bash
cd ~/my-vault
vault init
```

### `vault index`

Walk all `.md` files in the vault and build `_vault_index.json` with tags, wikilinks, word counts, and timestamps.

```bash
vault index
# Index built successfully.
#   Total nodes indexed: 42
#   Total links found:   138
#   Time taken:          0.12s
```

### `vault ingest <file_or_url>`

Ingest a PDF, markdown, text file, or web URL. Prints a formatted context bundle to stdout (designed to be piped to an LLM). Local files are moved to `attachments/processed/` after ingestion.

```bash
vault ingest report.pdf
vault ingest https://example.com/article
```

### `vault fetch <query>`

Search the vault index by keyword and print the full content of the top matching nodes.

```bash
vault fetch "competitive SME"
```

### `vault status`

Print a dashboard with node counts, link counts, unprocessed files, and stale nodes.

```bash
vault status
```

## Configuration

`vault.config.json` is created by `vault init` and found by walking up the directory tree (like `.git`). Fields:

| Field | Default | Description |
|---|---|---|
| `vault_root` | current dir | Root of the vault |
| `attachments_dir` | `attachments` | Where raw files are stored |
| `processed_dir` | `attachments/processed` | Where ingested files are moved |
| `index_file` | `_vault_index.json` | Path to the generated index |
| `stale_threshold_days` | `30` | Days before a node is flagged stale |
