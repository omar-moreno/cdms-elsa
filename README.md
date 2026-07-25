# cdms-elsa

**ELog Search Assistant** -- LLM-powered semantic search for CDMS ELOG.

ELSA lets you search the CDMS ELog using natural language. Instead of
guessing the exact keywords a colleague used, just describe what you're looking
for — ELSA finds conceptually related entries using vector embeddings, and can
optionally synthesize grounded answers with citations back to the original logs.

## Features

- 🔍 **Semantic search** — find entries by meaning, not just keywords
- 🔗 **Source fidelity** — every result links back to the original ELOG entry
- 🔒 **Fully self-hosted** — open-source models, no data leaves your infrastructure
- 🧩 **Non-invasive** — runs as a sidecar; no changes to ELOG itself
- 💬 **Optional RAG** — natural-language answers with citations

## Quick Start

```bash
# Install dependencies
pip install -e .

# Validate parsing against your ELOG data (Phase 0)
python scripts/inspect_elog.py /usr/local/elog/logbooks

# Build the search index
python scripts/ingest.py /usr/local/elog/logbooks

# Search from the CLI
python scripts/search_cli.py "were there any power supply failures?"
```
