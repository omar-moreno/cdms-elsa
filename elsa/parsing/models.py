"""Data models for parsed ELOG entries."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ElogEntry:
    """A single parsed ELOG entry.

    Attributes:
        entry_id: The ELOG message ID (from `$@MID@$:`).
        logbook: Name of the logbook (typically the parent directory name).
        source_file: Path to the .log file this entry came from.
        attributes: Raw key-value metadata headers (Author, Type, etc.).
        body: The free-text message body.
        encoding: How the body was encoded ("plain" | "HTML" | "ELCode").
        attachments: List of attachment filenames referenced by the entry.
    """

    entry_id: str
    logbook: str
    source_file: str = ""
    attributes: dict[str, str] = field(default_factory=dict)
    body: str = ""
    encoding: str = "plain"
    attachments: list[str] = field(default_factory=list)

    # --- Convenience accessors for common attributes ---

    @property
    def author(self) -> str:
        return self.attributes.get("Author", "Unknown")

    @property
    def entry_type(self) -> str:
        return self.attributes.get("Type", "")

    @property
    def category(self) -> str:
        return self.attributes.get("Category", "")

    @property
    def subject(self) -> str:
        return self.attributes.get("Subject", "")

    @property
    def raw_date(self) -> str:
        return self.attributes.get("Date", "")

    @property
    def date(self) -> datetime | None:
        """Parsed datetime, or None if unparseable.

        ELOG dates typically look like: 'Tue Mar 12 14:03:21 2024'
        """
        raw = self.raw_date
        if not raw:
            return None
        for fmt in (
            "%a %b %d %H:%M:%S %Y",   # Tue Mar 12 14:03:21 2024
            "%Y-%m-%d %H:%M:%S",      # 2024-03-12 14:03:21
            "%a, %d %b %Y %H:%M:%S",  # RFC-ish
        ):
            try:
                return datetime.strptime(raw.strip(), fmt)
            except ValueError:
                continue
        return None

    def unique_id(self) -> str:
        """Stable identifier across logbooks."""
        return f"{self.logbook}:{self.entry_id}"

    def searchable_text(self) -> str:
        """Combined metadata + body used for embedding/indexing."""
        header_parts = [
            f"{k}: {v}" for k, v in self.attributes.items() if v.strip()
        ]
        header = " | ".join(header_parts)
        return f"{header}\n\n{self.body}".strip()

    def __repr__(self) -> str:
        preview = self.body[:50].replace("\n", " ")
        return (
            f"ElogEntry(id={self.entry_id!r}, logbook={self.logbook!r}, "
            f"author={self.author!r}, body={preview!r}...)"
        )
