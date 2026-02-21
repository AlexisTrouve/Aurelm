"""Markdown file loader — parses civjdr Background/*.md files into raw messages.

Supports two formats:
- Format A (older files): Raw Discord dump — `Author\\n—\\nDD/MM/YYYY HH:MM\\n[content]`
- Format B (newer files): Structured markdown — `## Post narratif - Author`, `## Réponse - Author`
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .db import get_connection
from .ingestion import RawMessage


@dataclass
class ParsedMessage:
    """A message parsed from a markdown file, not yet in the database."""
    author_name: str
    content: str
    timestamp: str  # ISO format
    source_file: str


# Regex for Format A: "Author\n—\nDD/MM/YYYY HH:MM"
FORMAT_A_HEADER = re.compile(
    r"^(.+?)\n—\n(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})\s*$", re.MULTILINE
)

# Regex for Format B section headers
FORMAT_B_HEADER = re.compile(
    r"^##\s+(?:Post narratif|Message du MJ|Réponse(?:\s+du joueur)?|Note HRP)"
    r"\s*(?:-|—|\()\s*(.+?)\s*(?:\((\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})\))?\s*$",
    re.MULTILINE,
)


def detect_format(text: str) -> str:
    """Detect whether a file is Format A or Format B."""
    if FORMAT_B_HEADER.search(text):
        return "B"
    if FORMAT_A_HEADER.search(text):
        return "A"
    # Fallback: if it starts with a markdown heading, treat as B
    if text.lstrip().startswith("#"):
        return "B"
    return "A"


def parse_format_a(text: str, source_file: str) -> list[ParsedMessage]:
    """Parse Format A: raw Discord dump with Author/—/Date blocks."""
    messages: list[ParsedMessage] = []
    splits = FORMAT_A_HEADER.split(text)

    # splits: [preamble, author1, date1, content1, author2, date2, content2, ...]
    if len(splits) < 4:
        return messages

    i = 1  # skip preamble
    while i + 2 < len(splits):
        author = splits[i].strip()
        date_str = splits[i + 1].strip()
        content = splits[i + 2].strip()
        i += 3

        timestamp = _parse_date(date_str)
        # Clean up Discord artifacts from content
        content = _clean_format_a_content(content)
        if content:
            messages.append(ParsedMessage(
                author_name=author,
                content=content,
                timestamp=timestamp,
                source_file=source_file,
            ))

    return messages


def parse_format_b(text: str, source_file: str) -> list[ParsedMessage]:
    """Parse Format B: structured markdown with ## section headers."""
    messages: list[ParsedMessage] = []

    # Extract date from filename or header metadata
    file_date = _extract_date_from_filename(source_file)

    # Split by section headers
    sections = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        match = FORMAT_B_HEADER.match(section)
        if not match:
            continue

        author = match.group(1).strip()
        date_part = match.group(2)
        time_part = match.group(3)

        if date_part and time_part:
            timestamp = _parse_date(f"{date_part} {time_part}")
        elif file_date:
            timestamp = file_date
        else:
            timestamp = datetime.now().isoformat()

        # Skip HRP/OOC notes — they're metadata, not game content
        header_line = section.split("\n", 1)[0]
        if "Note HRP" in header_line:
            continue

        content = section[match.end():].strip()
        # Remove horizontal rules
        content = re.sub(r"^---+\s*$", "", content, flags=re.MULTILINE).strip()
        if content:
            messages.append(ParsedMessage(
                author_name=author,
                content=content,
                timestamp=timestamp,
                source_file=source_file,
            ))

    return messages


def parse_file(filepath: Path) -> list[ParsedMessage]:
    """Parse a markdown file, auto-detecting format."""
    text = filepath.read_text(encoding="utf-8")
    source = filepath.name
    fmt = detect_format(text)

    if fmt == "A":
        return parse_format_a(text, source)
    else:
        return parse_format_b(text, source)


def load_directory(data_dir: str, db_path: str, channel_id: str = "file-import") -> int:
    """Load all .md files from a directory into the database. Returns count of messages inserted."""
    data_path = Path(data_dir)
    if not data_path.is_dir():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    md_files = sorted(data_path.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No .md files found in {data_dir}")

    conn = get_connection(db_path)
    inserted = 0
    try:
        for filepath in md_files:
            # Skip Archive/ subdirectory files
            if "Archive" in filepath.parts:
                continue
            messages = parse_file(filepath)
            for msg in messages:
                # Generate a stable fake discord_message_id from content hash
                msg_id = _make_message_id(msg)
                try:
                    cursor = conn.execute(
                        """INSERT OR IGNORE INTO turn_raw_messages
                           (discord_message_id, discord_channel_id, author_id, author_name,
                            content, timestamp)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (msg_id, channel_id, _author_id(msg.author_name),
                         msg.author_name, msg.content, msg.timestamp),
                    )
                    if cursor.rowcount > 0:
                        inserted += 1
                except Exception:
                    pass  # UNIQUE constraint — skip duplicates
        conn.commit()
    finally:
        conn.close()

    return inserted


def _parse_date(date_str: str) -> str:
    """Parse DD/MM/YYYY HH:MM to ISO format."""
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.isoformat()
        except ValueError:
            continue
    return date_str


def _extract_date_from_filename(filename: str) -> str | None:
    """Extract YYYY-MM-DD from a filename like '2024-09-03-premier-age.md'."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})", Path(filename).stem)
    if match:
        try:
            dt = datetime.strptime(match.group(1), "%Y-%m-%d")
            return dt.isoformat()
        except ValueError:
            pass
    return None


def _clean_format_a_content(content: str) -> str:
    """Clean Discord-specific artifacts from Format A content."""
    lines = content.splitlines()
    cleaned: list[str] = []
    skip_youtube = False

    for line in lines:
        stripped = line.strip()
        # Skip YouTube embeds
        if stripped.startswith("https://www.youtube.com") or stripped.startswith("https://youtu.be"):
            skip_youtube = True
            continue
        if skip_youtube and stripped in ("YouTube", "") or (skip_youtube and not stripped):
            continue
        if skip_youtube and stripped and stripped != "YouTube":
            skip_youtube = False
        # Skip "(modifié)" markers
        if stripped == "(modifié)":
            continue
        # Skip standalone YouTube metadata lines
        if skip_youtube:
            skip_youtube = False
            continue
        cleaned.append(line)

    result = "\n".join(cleaned).strip()
    # Remove timestamp markers like [04:10] or [00:10]
    result = re.sub(r"^\[[\d:]+\]\s*", "", result, flags=re.MULTILINE)
    return result.strip()


def _make_message_id(msg: ParsedMessage) -> str:
    """Generate a stable ID from message content for deduplication."""
    raw = f"{msg.source_file}:{msg.author_name}:{msg.timestamp}:{msg.content[:100]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _author_id(author_name: str) -> str:
    """Generate a stable author ID from name."""
    return hashlib.md5(author_name.encode()).hexdigest()[:8]
