---
name: vault-cli
description: >
  Manage an Obsidian-compatible knowledge vault using vault-cli. Use this skill whenever
  the user mentions their vault, Obsidian notes, second brain, or knowledge base — and
  whenever they want to ingest a document or URL, search their notes, add new information,
  review what they know about a topic, or keep their notes up to date. Trigger on phrases
  like "add this to my notes", "put this in my vault", "search my notes for X", "what do
  I know about X", "ingest this PDF", "update my second brain", or anything that sounds
  like reading from or writing to a personal knowledge base.
---

# vault-cli

A CLI for managing a structured Obsidian-compatible knowledge vault. It indexes markdown
notes, ingests external sources (PDFs, URLs, text files), and produces LLM-ready context
bundles that tell you exactly what to add or update.

## Prerequisites

```bash
# Install (run once from the vault-cli repo)
cd vault-cli && pip install -e .

# Verify
vault --help
```

The tool discovers `vault.config.json` by walking up the directory tree, just like git
finds `.git`. Run all `vault` commands from inside the vault directory or any subdirectory.

## Vault structure

After `vault init`:

```
my-vault/
├── vault.config.json        # Config — auto-discovered up the tree
├── _vault_index.json        # Generated index (don't edit manually)
├── attachments/             # Drop files here to ingest later
│   └── processed/           # Files move here after ingestion
└── vault/                   # (Optional) markdown notes live here
```

Notes can live anywhere under the vault root — the indexer walks all `.md` files
recursively, excluding `attachments/`.

## Token Efficiency — Read the Index, Not the Files

**Never traverse the vault by reading individual `.md` files to understand its contents.**
Doing so reads every note in full and burns context budget unnecessarily.

The vault maintains `_vault_index.json` — a compact, pre-built summary of every node:
paths, tags, `[[wikilinks]]`, word counts, and modification timestamps. Use it as your
first (and often only) lens into the vault.

### Decision tree for vault exploration

| Goal | Do this | Not this |
|---|---|---|
| Understand vault structure / topic coverage | `vault status` + `vault fetch <topic>` | Read all `.md` files |
| Find notes related to a topic | `vault fetch "keywords"` | Glob `.md` files and read each |
| Get full content of a specific note | `Read` that one file (after identifying it via fetch) | Read all files to find it |
| Check what tags / links exist | Read `_vault_index.json` once | Walk the directory |
| Ingest a new document | `vault ingest <source>` — the output already includes the index summary | Separately read existing notes |

### When it IS appropriate to read a `.md` file directly

Only after `vault fetch` has identified it as relevant and you need its full content to
make an edit or answer a detailed question. Read that specific file — not the surrounding
directory.

### `_vault_index.json` as a direct read

If you need a structural overview without running a command, reading `_vault_index.json`
once gives you the entire vault map in a single, compact payload. It is far cheaper than
reading all notes individually and contains enough to plan any edit.

```bash
# Fastest way to see the full vault map
cat _vault_index.json   # or use the Read tool on this file
```

---

## Commands

### `vault init`
Initialise a new vault in the current directory. Creates the folder structure and
`vault.config.json`. Only needed once.

```bash
cd ~/my-vault && vault init
```

### `vault status`
Quick health check: node count, link count, unprocessed files waiting in `attachments/`,
and stale nodes (not updated within `stale_threshold_days`, default 30).

**Start here** whenever the user asks about the state of their vault.

```bash
vault status
```

### `vault index`
Walk all `.md` files and rebuild `_vault_index.json`. Extracts frontmatter tags,
`[[wikilinks]]`, word counts, and modification timestamps. Run after editing notes.

```bash
vault index
```

### `vault fetch <query>`
Keyword search across the index. Scores nodes by tag matches (2 pts each) and path
segment matches (1 pt each), returns the top 5 with full file content.

```bash
vault fetch "competitive analysis SME"
vault fetch "meeting notes Q1"
```

Use `vault fetch` before writing new notes — it surfaces related content so you can
link or merge rather than duplicate.

**This is the primary way the LLM should explore the vault.** It reads the index, not
the files, and returns only the top relevant nodes with their full content — giving you
exactly what you need without burning context on unrelated notes.

### `vault ingest <source>`
Ingest a PDF, `.md`, `.txt`, or URL. Rebuilds the index, then prints a **context
bundle** to stdout containing:

- A vault index summary (top tags, most-linked nodes)
- The full extracted document content
- An embedded LLM prompt asking for a structured edit plan

```bash
vault ingest report.pdf
vault ingest https://example.com/article
vault ingest notes/meeting.txt
```

After ingestion, local files are moved to `attachments/processed/` automatically.
Use `--force` to re-ingest a file that was already processed.

The output is designed to be read by an LLM (you). Your job after seeing it is to
produce the structured edit plan it asks for — then actually make those edits.

### `vault ingest-all`
Ingest every unprocessed file in `attachments/` in one pass. Useful after dropping
several files into the attachments folder.

```bash
vault ingest-all
```

## Typical workflows

### Absorbing a new document into the vault

1. `vault ingest <file-or-url>` — read the context bundle output
2. Identify which existing notes to update and what new notes to create
3. Edit the relevant `.md` files (use `vault fetch` to find related nodes)
4. `vault index` — refresh the index to capture your changes
5. `vault status` — confirm everything looks healthy

### Searching before writing

Before creating a new note, always check for overlap:

```bash
vault fetch "topic keywords"
```

If related nodes exist, link to them with `[[wikilink]]` syntax rather than duplicating.

### Handling a batch of attachments

```bash
# Drop files into attachments/, then:
vault ingest-all    # processes and moves each to processed/
vault index         # rebuild index
vault status        # verify
```

### Understanding the vault from scratch

```bash
vault status        # overview
vault fetch "topic" # dive into a specific area
```

## Configuration (`vault.config.json`)

| Field | Default | Notes |
|---|---|---|
| `vault_root` | init directory | Root of the vault |
| `attachments_dir` | `attachments` | Raw files waiting to be ingested |
| `processed_dir` | `attachments/processed` | Files after ingestion |
| `index_file` | `_vault_index.json` | Generated index path |
| `stale_threshold_days` | `30` | Days before a node appears as stale in `status` |

## What the ingest context bundle means

When `vault ingest` runs, it prints something like:

```
## Ingest Context
### Source: report.pdf
### Vault Index Summary
Total nodes: 42
Top tags: project(8), meeting(5), research(4) ...
Most-linked nodes: index(12), topics/map(7) ...

### Document Content
[full extracted text]

---
INSTRUCTIONS FOR LLM:
You are updating a knowledge vault. Based on the document above and the vault index summary:
1. List which existing nodes should be updated and what to add (reference by path)
2. List any new nodes to create (suggest path, tags, and content)
3. List any new [[wikilinks]] to add between nodes
Respond with a structured edit plan.
```

Your response should be a concrete edit plan:
- **Update** `path/to/existing-note.md` — what to add/change and why
- **Create** `path/to/new-note.md` — suggested frontmatter tags and content outline
- **Link** — new `[[wikilinks]]` to add in which files

Then carry out those edits directly on the markdown files.

## Common pitfalls

- **Reading all `.md` files to explore the vault**: This is the most expensive mistake. A vault with 50 notes costs ~50 Read operations and floods context with irrelevant content. Always use `vault fetch` or read `_vault_index.json` instead. Only open a specific `.md` file once `vault fetch` has identified it as the right target.
- **Index is stale**: Always run `vault index` after editing notes. `vault fetch` and `vault status` read the last-built index, not the live files.
- **File not found during ingest**: The `--force` flag only applies to already-processed files. Make sure the path is correct.
- **No matches in fetch**: Try simpler or different keywords. The scorer matches against tags and path segments, not full-text content.
- **vault.config.json not found**: You're outside the vault directory tree. `cd` into the vault or any subdirectory first.
