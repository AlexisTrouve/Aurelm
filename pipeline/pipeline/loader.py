"""Markdown file loader — parses civjdr Background/*.md files into raw messages.

Supports two file layouts:

Old layout (mixed files):
  One or more .md files containing interleaved GM and player posts.
  Turn boundaries detected by the chunker via GM-after-player pattern.
  Formats:
  - Format A: Raw Discord dump — `Author\\n—\\nDD/MM/YYYY HH:MM\\n[content]`
  - Format B: Structured markdown — `## Post narratif - Author`, `## Réponse - Author`

New layout (split files, detected automatically):
  Pairs of files per turn: `YYYY-MM-DD--mj-T##-*.md` (GM) + `pj-T##-*.md` (player).
  BOTH files are loaded — the pj file contains player roleplay decisions that
  introduce major entities (institutions, technologies, governance structures).
  Load order per turn:
    1. Synthetic __player__ placeholder  → triggers chunker boundary
    2. mj-T## content (GM posts)
    3. pj-T## content (player posts, if present)  → signals end of GM streak
  The pj posts act as the natural "player after GM" signal that the chunker
  uses to detect the end of a turn, making room for the next turn's boundary.
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


# Regex to detect new-layout MJ files: "YYYY-MM-DD--mj-T##-..." in stem
_NEW_LAYOUT_MJ = re.compile(r"\d{4}-\d{2}-\d{2}--mj-T(\d+)-")

# Synthetic author used as player placeholder in new-layout loading.
# Must differ from any real GM author so the chunker can detect the boundary.
_SYNTHETIC_PLAYER_NAME = "__player__"
_SYNTHETIC_PLAYER_ID = "00000000"


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

# Regex for Format C: H1 title + italic author line
# e.g. "# Post MJ — T19 — Title\n*Arthur Ignatus — 2026-03-03*"
FORMAT_C_AUTHOR = re.compile(
    r"^\*([^*]+?)\s*[—\-]\s*(\d{4}-\d{2}-\d{2})\*\s*$",
    re.MULTILINE,
)


def detect_format(text: str) -> str:
    """Detect whether a file is Format A, B, or C.

    Format C: H1 title + italic '*Author — YYYY-MM-DD*' line (new simplified format).
    """
    if FORMAT_B_HEADER.search(text):
        return "B"
    if FORMAT_C_AUTHOR.search(text):
        return "C"
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
        # Remove YouTube embeds
        content = _strip_youtube_embeds(content)
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


def parse_format_c(text: str, source_file: str) -> list[ParsedMessage]:
    """Parse Format C: H1 title + italic '*Author — YYYY-MM-DD*' line.

    Content runs from after the first '---' separator until '## Choix' or EOF.
    """
    match = FORMAT_C_AUTHOR.search(text)
    if not match:
        return []

    author = match.group(1).strip()
    date_iso = match.group(2).strip()  # already YYYY-MM-DD
    timestamp = f"{date_iso}T00:00:00"

    # Content: everything after the author line
    after_author = text[match.end():]
    # Strip leading separators
    after_author = re.sub(r"^\s*---+\s*", "", after_author).strip()
    # Keep all content — ## headings inside are narrative sections, not format delimiters
    content_part = after_author
    content = _strip_youtube_embeds(content_part)
    content = re.sub(r"^---+\s*$", "", content, flags=re.MULTILINE).strip()

    if not content:
        return []

    return [ParsedMessage(
        author_name=author,
        content=content,
        timestamp=timestamp,
        source_file=source_file,
    )]


def parse_file(filepath: Path) -> list[ParsedMessage]:
    """Parse a markdown file, auto-detecting format."""
    text = filepath.read_text(encoding="utf-8")
    source = filepath.name
    fmt = detect_format(text)

    if fmt == "A":
        return parse_format_a(text, source)
    elif fmt == "C":
        return parse_format_c(text, source)
    else:
        return parse_format_b(text, source)


def load_directory(data_dir: str, db_path: str, channel_id: str = "file-import") -> int:
    """Load .md files from a directory into the database.

    Auto-detects the file layout:
    - New layout (mj-T##/pj-T## pairs): loads only GM files, one turn each.
    - Old layout (mixed files): loads all files, chunker detects turn boundaries.

    Returns count of messages inserted.
    """
    data_path = Path(data_dir)
    if not data_path.is_dir():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    md_files = sorted(data_path.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No .md files found in {data_dir}")

    # Detect layout by checking if any file matches the new mj-T## naming convention
    mj_files = sorted(
        (f for f in md_files if _NEW_LAYOUT_MJ.search(f.stem)),
        key=lambda f: int(_NEW_LAYOUT_MJ.search(f.stem).group(1)),
    )

    if mj_files:
        return _load_new_layout(mj_files, db_path, channel_id)
    else:
        return _load_old_layout(md_files, db_path, channel_id)


def _load_new_layout(mj_files: list[Path], db_path: str, channel_id: str) -> int:
    """Load new-layout mj-T## + pj-T## file pairs as individual turns.

    For each turn:
      1. Insert a synthetic __player__ placeholder (triggers chunker boundary)
      2. Insert all messages from mj-T## (GM narrative)
      3. Insert all messages from pj-T## if it exists (player roleplay — contains
         major lore: institutions, technologies, governance decisions)
    """
    conn = get_connection(db_path)
    inserted = 0
    try:
        for mj_filepath in mj_files:
            turn_num = int(_NEW_LAYOUT_MJ.search(mj_filepath.stem).group(1))
            file_date = _extract_date_from_filename(mj_filepath.name)
            base_ts = file_date or datetime.now().isoformat()

            # 1. Synthetic player placeholder — triggers chunker boundary detection.
            placeholder_id = f"synth-player-T{turn_num:03d}"
            conn.execute(
                """INSERT OR IGNORE INTO turn_raw_messages
                   (discord_message_id, discord_channel_id, author_id, author_name,
                    content, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (placeholder_id, channel_id, _SYNTHETIC_PLAYER_ID,
                 _SYNTHETIC_PLAYER_NAME, f"[Tour {turn_num}]", base_ts),
            )

            # 2. GM content from the mj file
            for filepath in [mj_filepath]:
                for msg in parse_file(filepath):
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

            # 3. Player content from the matching pj-T## file (same dir, same turn num).
            # Replace "mj" with "pj" in the stem to find the partner file.
            pj_stem_pattern = mj_filepath.stem.replace("--mj-", "--pj-")
            pj_candidates = list(mj_filepath.parent.glob(f"{pj_stem_pattern}*"))
            # Fallback: search by pj-T## pattern in the same directory
            if not pj_candidates:
                pj_candidates = list(mj_filepath.parent.glob(f"*--pj-T{turn_num:02d}-*.md"))
            if not pj_candidates:
                pj_candidates = list(mj_filepath.parent.glob(f"*--pj-T{turn_num}-*.md"))

            for pj_filepath in sorted(pj_candidates):
                for msg in parse_file(pj_filepath):
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


def _load_old_layout(md_files: list[Path], db_path: str, channel_id: str) -> int:
    """Load old-layout files (all .md files, turn boundaries detected by chunker)."""
    conn = get_connection(db_path)
    inserted = 0
    try:
        for filepath in md_files:
            if "Archive" in filepath.parts:
                continue
            messages = parse_file(filepath)
            for msg in messages:
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


def _strip_youtube_embeds(content: str) -> str:
    """Remove YouTube embed blocks from Discord content.

    Discord YouTube embeds follow a consistent pattern:
        https://www.youtube.com/watch?v=...
        YouTube                              <- always present
        Artist Name                          <- short, no French punctuation
        Track Title (optional)               <- short, often English/ALL CAPS

    Strips the URL line, then consumes following lines that look like
    YouTube metadata (short, no sentence-ending punctuation, non-French).
    Stops at the first line that looks like narrative text or an empty line
    after at least one metadata line was consumed.
    """
    lines = content.splitlines()
    cleaned: list[str] = []
    in_youtube_block = False
    meta_lines_seen = 0

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("https://www.youtube.com") or stripped.startswith("https://youtu.be"):
            in_youtube_block = True
            meta_lines_seen = 0
            continue

        if in_youtube_block:
            # Empty lines within embed block are just padding — skip them
            # but don't exit the block yet (metadata may follow)
            if not stripped:
                continue

            # "YouTube" label — always skip (doesn't count toward limit)
            if stripped == "YouTube":
                continue

            # Short line without French sentence markers = likely metadata
            # (artist name, track title). Real narrative has periods, commas,
            # accented chars in longer sentences.
            # Allow up to 3 metadata lines after "YouTube" (artist, title, extra)
            is_meta = (
                len(stripped) < 100
                and not stripped.endswith(".")
                and not stripped.endswith("!")
                and not stripped.endswith("?")
                and meta_lines_seen < 3
            )

            if is_meta:
                meta_lines_seen += 1
                continue
            else:
                # Looks like narrative — stop skipping
                in_youtube_block = False

        cleaned.append(line)

    return "\n".join(cleaned)


def _clean_format_a_content(content: str) -> str:
    """Clean Discord-specific artifacts from Format A content."""
    content = _strip_youtube_embeds(content)

    lines = content.splitlines()
    cleaned: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped == "(modifié)":
            continue
        cleaned.append(line)

    result = "\n".join(cleaned).strip()
    result = re.sub(r"^\[[\d:]+\]\s*", "", result, flags=re.MULTILINE)
    return result.strip()


def _make_message_id(msg: ParsedMessage) -> str:
    """Generate a stable ID from message content for deduplication."""
    raw = f"{msg.source_file}:{msg.author_name}:{msg.timestamp}:{msg.content[:100]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _author_id(author_name: str) -> str:
    """Generate a stable author ID from name.

    Strips trailing date/timestamp suffixes like "(03/09/2024)" so that
    "Arthur Ignatus (03/09/2024)" and "Arthur Ignatus (06/09/2024)" map to
    the same ID. This is critical for GM detection across turns.
    """
    # Remove trailing parenthesized content (dates, timestamps)
    normalized = re.sub(r"\s*\([^)]*\)\s*$", "", author_name).strip()
    return hashlib.md5(normalized.encode()).hexdigest()[:8]
