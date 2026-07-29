"""Parser for ELOG plain-text .log files.

ELOG stores multiple entries per .log file. Each entry begins with a marker
line of the form:

    $@MID@$: <id>

followed by header lines (`Key: value`), then a separator, then the body.

NOTE: The exact format varies by ELOG version and per-logbook config.
Run this against real data (Phase 0) and adjust as needed.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from collections.abc import Iterator
from .models import ElogEntry

logger = logging.getLogger(__name__)

# Marker that begins each entry: "$@MID@$: 123"
_ENTRY_MARKER = re.compile(r"^\$@MID@\$:\s*(\d+)\s*$", re.MULTILINE)

# Header line: "Key: value"  (keys are alnum + space/underscore)
_HEADER_LINE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_ ]*?):\s?(.*)$")

# The separator ELOG writes between headers and body (length can vary).
_SEPARATOR = re.compile(r"^=+\s*$")


def parse_elog_file(filepath: str | Path) -> list[ElogEntry]:
    """Parse a single ELOG .log file into a list of ElogEntry objects."""
    path = Path(filepath)
    logbook = path.parent.name

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.warning("Could not read %s: %s", path, e)
        return []

    entries: list[ElogEntry] = []
    for entry_id, block in _split_entries(raw):
        try:
            entry = _parse_block(entry_id, block, logbook, str(path))
            if entry is not None:
                entries.append(entry)
        except Exception as e:  # noqa: BLE001 - one bad entry must not kill the file
            logger.warning(
                "Failed to parse entry %s in %s: %s", entry_id, path, e
            )
    return entries


def _split_entries(raw: str) -> Iterator[tuple[str, str]]:
    """Yield (entry_id, block_text) pairs from a raw file."""
    matches = list(_ENTRY_MARKER.finditer(raw))
    if not matches:
        return

    for i, match in enumerate(matches):
        entry_id = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        block = raw[start:end]
        yield entry_id, block


def _parse_block(
    entry_id: str, block: str, logbook: str, source_file: str
) -> ElogEntry | None:
    """Parse a single entry block (headers + body)."""
    lines = block.splitlines()

    attributes: dict[str, str] = {}
    body_lines: list[str] = []
    in_body = False

    for line in lines:
        if in_body:
            body_lines.append(line)
            continue

        if _SEPARATOR.match(line):
            in_body = True
            continue

        if line.strip() == "" and attributes:
            in_body = True
            continue

        if line.strip() == "" and not attributes:
            continue

        m = _HEADER_LINE.match(line)
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip()
            attributes[key] = val
        else:
            in_body = True
            body_lines.append(line)

    body = "\n".join(body_lines).strip()

    if not body and not attributes:
        logger.debug("Skipping empty entry %s in %s", entry_id, source_file)
        return None

    encoding = attributes.get("Encoding", "plain")
    attachments = _extract_attachments(attributes)

    if encoding.upper() == "HTML":
        body = _strip_html(body)

    return ElogEntry(
        entry_id=entry_id,
        logbook=logbook,
        source_file=source_file,
        attributes=attributes,
        body=body,
        encoding=encoding,
        attachments=attachments,
    )


def _extract_attachments(attributes: dict[str, str]) -> list[str]:
    """Pull attachment filenames from header attributes."""
    attachments: list[str] = []
    for key, val in attributes.items():
        if key.lower().startswith("attachment") and val.strip():
            attachments.extend(p.strip() for p in val.split(",") if p.strip())
    return attachments


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")


def _strip_html(text: str) -> str:
    """Very light HTML-to-text for HTML-encoded entries."""
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|tr|h[1-6])>", "\n", text)
    text = _TAG_RE.sub("", text)
    for entity, char in (
        ("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
        ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"),
    ):
        text = text.replace(entity, char)
    text = _WS_RE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_elog_dir(
    directory: str | Path, pattern: str = "*.log"
) -> list[ElogEntry]:
    """Recursively parse all ELOG log files under a directory."""
    root = Path(directory)
    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root}")

    all_entries: list[ElogEntry] = []
    files = sorted(root.rglob(pattern))
    logger.info("Found %d log file(s) under %s", len(files), root)

    for path in files:
        entries = parse_elog_file(path)
        logger.debug("Parsed %d entries from %s", len(entries), path)
        all_entries.extend(entries)

    logger.info("Parsed %d total entries", len(all_entries))
    return all_entries


def iter_elog_files(
    directory: str | Path, pattern: str = "*.log"
) -> Iterator[Path]:
    """Yield log file paths under a directory (useful for incremental indexing)."""
    yield from sorted(Path(directory).rglob(pattern))
