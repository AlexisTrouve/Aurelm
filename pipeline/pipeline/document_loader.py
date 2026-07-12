"""Generic document/chapter loader — non-Discord corpora (novels, etc.).

WHAT: Loads plain document files (a novel's chapters) into `turn_raw_messages`,
so the EXISTING pipeline (chunk -> extract -> profile -> aliases) can process
them with no other change. Sits ALONGSIDE loader.py (the Discord loader), never
replacing it — the runner picks one via --corpus-type.

WHY this works with zero schema change: the loader's only contract with the rest
of the pipeline is "insert rows into turn_raw_messages". The Discord-named
columns already hold SYNTHETIC values in the file path (channel "file-import",
hashed ids), so a document corpus fills them the same way. Each chapter becomes
one turn by reusing the Discord loader's trick: a synthetic __player__
placeholder inserted before each chapter's text makes the chunker cut a boundary,
and the chapter (authored by a single "narrator") is the only GM post in that
chunk — so it survives the runner's is_gm_post filter as one turn.

ORDERING: fetch_unprocessed_messages orders by timestamp ASC, so we emit
deterministic, monotonically increasing synthetic timestamps (placeholder before
its chapter, chapters in chapter-number order). Chapter numbers are parsed from
the filename (e.g. CHAP_T05 -> 5) so "T10" sorts after "T5" (not lexically).
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path

from .db import get_connection
from .loader import _SYNTHETIC_PLAYER_ID, _SYNTHETIC_PLAYER_NAME, _author_id

# Chapter number embedded in the filename stem, e.g. "CHAP_T05" -> 5.
_CHAPTER_NUM = re.compile(r"[Tt](\d+)")
# A translation variant carries a 2-letter language code as a secondary suffix,
# e.g. "CHAP_T06.zh.md" -> Path.stem is "CHAP_T06.zh". Skipped by default so a
# translated copy does not duplicate the canonical chapter.
_TRANSLATION_SUFFIX = re.compile(r"\.[a-z]{2}$")

# Deterministic base for synthetic timestamps (kept fixed so runs are stable).
_BASE_TS = datetime(2000, 1, 1)
_DEFAULT_AUTHOR = "Narrator"
_DEFAULT_CHANNEL = "documents"


def _chapter_number(stem: str, fallback: int) -> int:
    """Parse the chapter number from a filename stem, else return fallback."""
    m = _CHAPTER_NUM.search(stem)
    return int(m.group(1)) if m else fallback


def _is_translation(path: Path) -> bool:
    """True if the file is a language variant (e.g. *.zh.md, *.en.txt)."""
    return bool(_TRANSLATION_SUFFIX.search(path.stem))


def _doc_message_id(path: Path, content: str) -> str:
    """Stable id for a chapter message, from path + content head (dedup key)."""
    raw = f"{path.name}:{content[:100]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load_documents(
    data_dir: str,
    db_path: str,
    channel_id: str = _DEFAULT_CHANNEL,
    author_name: str = _DEFAULT_AUTHOR,
    pattern: str = "*.md",
    include_translations: bool = False,
) -> int:
    """Load document/chapter files from a directory into turn_raw_messages.

    Each matching file becomes one turn (chapter). Returns the number of chapter
    messages inserted (placeholders are not counted).

    Args:
        data_dir: directory containing the chapter files.
        db_path: target Aurelm DB.
        channel_id: scope tag stored in discord_channel_id (keeps a corpus
            separate from Discord "file-import" data in the same DB).
        author_name: the single synthetic "narrator" author for every chapter;
            the runner's GM detection resolves it as the GM.
        pattern: glob for chapter files (default "*.md").
        include_translations: if False (default), skip language variants like
            "*.zh.md" so a translated copy does not duplicate a chapter.
    """
    data_path = Path(data_dir)
    if not data_path.is_dir():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    files = list(data_path.glob(pattern))
    if not include_translations:
        files = [f for f in files if not _is_translation(f)]
    if not files:
        raise FileNotFoundError(f"No files matching {pattern!r} in {data_dir}")

    # Sort by parsed chapter number (numeric, so T10 follows T5), then by name.
    files = sorted(files, key=lambda f: (_chapter_number(f.stem, 10**9), f.name))

    author = author_name
    author_hash = _author_id(author)

    conn = get_connection(db_path)
    inserted = 0
    try:
        for i, filepath in enumerate(files):
            content = filepath.read_text(encoding="utf-8").strip()
            if not content:
                continue  # skip empty files rather than create an empty turn
            chapter = _chapter_number(filepath.stem, i + 1)

            # All synthetic values are keyed on the CHAPTER NUMBER, not the file's
            # position in this batch — so the loader is idempotent and composes
            # chapter-by-chapter: loading [T05] then [T06] separately yields the
            # same stable ids/timestamps as loading them together (no collisions,
            # correct order). Timestamps are monotonic by chapter (placeholder
            # strictly before its chapter) so fetch_unprocessed_messages reads in
            # chapter order.
            placeholder_ts = (_BASE_TS + timedelta(minutes=2 * chapter)).isoformat()
            chapter_ts = (_BASE_TS + timedelta(minutes=2 * chapter + 1)).isoformat()

            # 1. Synthetic __player__ placeholder — triggers a chunker boundary so
            # each chapter is its own turn (same mechanism as the Discord loader).
            conn.execute(
                """INSERT OR IGNORE INTO turn_raw_messages
                   (discord_message_id, discord_channel_id, author_id, author_name,
                    content, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (f"synth-player-doc-T{chapter:04d}", channel_id, _SYNTHETIC_PLAYER_ID,
                 _SYNTHETIC_PLAYER_NAME, f"[Tour {chapter}]", placeholder_ts),
            )

            # 2. The chapter itself, authored by the single narrator (= GM).
            cursor = conn.execute(
                """INSERT OR IGNORE INTO turn_raw_messages
                   (discord_message_id, discord_channel_id, author_id, author_name,
                    content, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (_doc_message_id(filepath, content), channel_id, author_hash,
                 author, content, chapter_ts),
            )
            if cursor.rowcount > 0:
                inserted += 1

        conn.commit()
    finally:
        conn.close()

    return inserted
