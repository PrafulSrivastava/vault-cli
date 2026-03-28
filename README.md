# vault-cli

A CLI tool for capturing, indexing, and retrieving knowledge from an [Obsidian](https://obsidian.md) vault — designed to work as a lightweight AI context engine.

## Structure

```
vault-cli/              # CLI tool (install once, use anywhere)
<vault root>/           # Obsidian markdown notes live here
├── attachments/        # Drop PDFs and URLs here for ingestion
└── vault/              # Structured knowledge notes
```

## vault-cli

A Python CLI that runs alongside any Obsidian vault to capture, index, and retrieve knowledge.

### Install

```bash
cd vault-cli
pip install -e .
```

### Commands

| Command | Description |
|---|---|
| `vault init` | Initialise a new vault in the current directory |
| `vault index` | Rebuild the searchable index of all notes |
| `vault ingest <file\|url>` | Extract content and generate an LLM context bundle |
| `vault ingest-all` | Ingest all unprocessed files in `attachments/` |
| `vault fetch <query>` | Retrieve relevant notes by keyword |
| `vault status` | Dashboard showing node counts, stale notes, and unprocessed files |

See [`vault-cli/README.md`](vault-cli/README.md) for full usage and examples.

## Workflow

1. Drop PDFs or save URLs into `attachments/`
2. Run `vault ingest-all > context.txt`
3. Paste `context.txt` into Claude — it returns a structured edit plan
4. Create or update notes based on the plan
5. Run `vault index` to refresh the index
