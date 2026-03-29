"""Public facade for Aurelm -- one class, one game DB, no global state.

Usage::

    from aurelm import AurelmGame

    # Open existing DB
    game = AurelmGame("path/to/aurelm.db")
    print(game.list_civs())

    # Create new DB from scratch
    with AurelmGame("/tmp/new_game.db", create=True) as game:
        cid = game.register_civ("Confluence", "Rubanc")
        print(game.search_lore("bronze"))
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

# Ensure Aurelm root is on sys.path so bot/pipeline imports work
# even when called from an external repo (e.g. DemiUrgos).
_AURELM_ROOT = str(Path(__file__).resolve().parent.parent)
if _AURELM_ROOT not in sys.path:
    sys.path.insert(0, _AURELM_ROOT)


class AurelmGame:
    """One game = one SQLite DB.  Each instance is independent, no global state.

    Thread safety: the underlying sqlite3.Connection uses WAL mode and
    busy_timeout=5000, so concurrent reads are fine.  Concurrent writes from
    multiple threads should go through a single instance (SQLite serialises
    writes anyway).
    """

    # ------------------------------------------------------------------ #
    # Class-level tool metadata (populated lazily)
    # ------------------------------------------------------------------ #

    _tool_defs: list[dict] | None = None
    _tool_names: set[str] | None = None

    @classmethod
    def _ensure_tool_meta(cls) -> None:
        """Load tool definitions once (lazy -- avoids import cost at module level)."""
        if cls._tool_defs is None:
            from bot.tool_definitions import TOOL_DEFINITIONS
            cls._tool_defs = TOOL_DEFINITIONS
            cls._tool_names = {t["name"] for t in TOOL_DEFINITIONS}

    @classmethod
    def get_tool_definitions(cls) -> list[dict]:
        """JSON schemas for every available tool."""
        cls._ensure_tool_meta()
        return cls._tool_defs  # type: ignore[return-value]

    @classmethod
    def get_tool_names(cls) -> set[str]:
        """Set of valid tool names."""
        cls._ensure_tool_meta()
        return cls._tool_names  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def __init__(self, db_path: str | Path, *, create: bool = False) -> None:
        """Open (or create) a game database.

        Args:
            db_path: Path to the SQLite file.
            create:  If True, run schema init + migrations on a fresh DB.
        """
        self._db_path = str(Path(db_path).resolve())
        self._conn: sqlite3.Connection | None = None

        if create:
            from pipeline.pipeline.db import init_db, run_migrations
            init_db(self._db_path)
            run_migrations(self._db_path)

    @property
    def db_path(self) -> str:
        """Resolved absolute path to the SQLite file."""
        return self._db_path

    @property
    def conn(self) -> sqlite3.Connection:
        """Lazy-opened connection with WAL, foreign keys, and busy timeout."""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA busy_timeout = 5000")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "AurelmGame":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # Lore query -- generic dispatch
    # ------------------------------------------------------------------ #

    def query(self, tool_name: str, tool_input: dict | None = None) -> str:
        """Call any Aurelm tool by name.  Returns Markdown string.

        Raises ValueError for unknown tool names.
        """
        self._ensure_tool_meta()
        if tool_name not in self._tool_names:  # type: ignore[operator]
            raise ValueError(
                f"Unknown tool '{tool_name}'. "
                f"Valid: {sorted(self._tool_names)}"  # type: ignore[arg-type]
            )
        from bot.tools import dispatch_tool
        return dispatch_tool(
            self.conn,
            tool_name,
            tool_input or {},
            db_path=self._db_path,
        )

    # ------------------------------------------------------------------ #
    # Convenience shortcuts (most-used tools)
    # ------------------------------------------------------------------ #

    def search_lore(self, query: str, **kw: Any) -> str:
        """Search entities by name, description, or alias."""
        return self.query("searchLore", {"query": query, **kw})

    def sanity_check(self, statement: str, **kw: Any) -> str:
        """Cross-check a statement against established lore."""
        return self.query("sanityCheck", {"statement": statement, **kw})

    def get_civ_state(self, civ: str, **kw: Any) -> str:
        """Overview of a civilization: recent turns, key entities, type breakdown."""
        return self.query("getCivState", {"civName": civ, **kw})

    def get_entity(self, name: str, **kw: Any) -> str:
        """Full entity profile: description, aliases, mentions, relations."""
        return self.query("getEntityDetail", {"entityName": name, **kw})

    def list_civs(self) -> str:
        """List all civilizations with turn/entity counts."""
        return self.query("listCivs")

    def timeline(self, **kw: Any) -> str:
        """Chronological turn list with optional filters."""
        return self.query("timeline", kw)

    # ------------------------------------------------------------------ #
    # DB management
    # ------------------------------------------------------------------ #

    def register_civ(
        self,
        name: str,
        player_name: str = "",
        discord_channel_id: str = "",
    ) -> int:
        """Register a civilization.  Idempotent -- returns existing id if present."""
        from pipeline.pipeline.db import register_civilization
        return register_civilization(
            self._db_path, name, player_name, discord_channel_id
        )

    def get_civ_id(self, name: str) -> int | None:
        """Look up a civilization id by exact name."""
        from pipeline.pipeline.db import get_civilization_id
        return get_civilization_id(self._db_path, name)

    def apply_migrations(self) -> None:
        """Apply any pending schema migrations."""
        from pipeline.pipeline.db import run_migrations
        run_migrations(self._db_path)

    # ------------------------------------------------------------------ #
    # Writer functions (for external lore extractors like DemiUrgos)
    # ------------------------------------------------------------------ #

    def write_turn(
        self,
        civ_id: int,
        turn_number: int,
        title: str = "",
        summary: str = "",
        raw_message_ids: str = "[]",
    ) -> int:
        """Insert a turn and return its id.  Skips if turn_number already exists for civ."""
        c = self.conn
        existing = c.execute(
            "SELECT id FROM turn_turns WHERE civ_id = ? AND turn_number = ?",
            (civ_id, turn_number),
        ).fetchone()
        if existing:
            return existing["id"]
        cur = c.execute(
            "INSERT INTO turn_turns (civ_id, turn_number, title, summary, raw_message_ids) "
            "VALUES (?, ?, ?, ?, ?)",
            (civ_id, turn_number, title, summary, raw_message_ids),
        )
        c.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def write_entity(
        self,
        name: str,
        entity_type: str,
        civ_id: int,
        description: str = "",
        *,
        first_seen_turn: int | None = None,
    ) -> int:
        """Insert or retrieve an entity.  Returns entity id."""
        c = self.conn
        existing = c.execute(
            "SELECT id FROM entity_entities WHERE canonical_name = ? AND civ_id = ?",
            (name, civ_id),
        ).fetchone()
        if existing:
            return existing["id"]
        cur = c.execute(
            "INSERT INTO entity_entities (canonical_name, entity_type, civ_id, description, first_seen_turn) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, entity_type, civ_id, description, first_seen_turn),
        )
        c.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def write_mention(
        self,
        entity_id: int,
        turn_id: int,
        mention_text: str,
        context: str = "",
    ) -> None:
        """Record an entity mention in a turn."""
        self.conn.execute(
            "INSERT INTO entity_mentions (entity_id, turn_id, mention_text, context) "
            "VALUES (?, ?, ?, ?)",
            (entity_id, turn_id, mention_text, context),
        )
        self.conn.commit()

    def write_relation(
        self,
        source_id: int,
        target_id: int,
        relation_type: str,
        description: str = "",
    ) -> None:
        """Record a relation between two entities.  Skips exact duplicates."""
        c = self.conn
        exists = c.execute(
            "SELECT 1 FROM entity_relations "
            "WHERE source_entity_id = ? AND target_entity_id = ? AND relation_type = ?",
            (source_id, target_id, relation_type),
        ).fetchone()
        if exists:
            return
        c.execute(
            "INSERT INTO entity_relations (source_entity_id, target_entity_id, relation_type, description) "
            "VALUES (?, ?, ?, ?)",
            (source_id, target_id, relation_type, description),
        )
        c.commit()

    def write_alias(self, entity_id: int, alias_text: str) -> None:
        """Add an alias for an entity.  Skips if already exists."""
        c = self.conn
        exists = c.execute(
            "SELECT 1 FROM entity_aliases WHERE entity_id = ? AND alias = ?",
            (entity_id, alias_text),
        ).fetchone()
        if exists:
            return
        c.execute(
            "INSERT INTO entity_aliases (entity_id, alias) VALUES (?, ?)",
            (entity_id, alias_text),
        )
        c.commit()

    # ------------------------------------------------------------------ #
    # Pipeline (lazy import to avoid pulling httpx/ollama at facade level)
    # ------------------------------------------------------------------ #

    def run_pipeline(
        self,
        civ_name: str,
        *,
        data_dir: str | None = None,
        use_llm: bool = True,
        model: str = "qwen3:14b",
        extraction_version: str = "v22.2.2-pastlevel",
        player_name: str | None = None,
        track_progress: bool = False,
        **kw: Any,
    ) -> dict:
        """Run the ML pipeline on this game's DB.

        Args:
            civ_name:  Civilization to process.
            data_dir:  Directory with markdown turn files (CLI mode).
            use_llm:   False for --no-llm dry runs.
            model:     Ollama model name.
            extraction_version: Extraction strategy version.
            player_name: Player name for civ registration.
            track_progress: Enable progress tracking for Flutter UI.
            **kw: Passed through to pipeline.runner.run_pipeline().

        Returns:
            dict with pipeline stats.
        """
        from pipeline.pipeline.runner import run_pipeline
        return run_pipeline(
            db_path=self._db_path,
            civ_name=civ_name,
            data_dir=data_dir,
            use_llm=use_llm,
            model=model,
            extraction_version=extraction_version,
            player_name=player_name,
            track_progress=track_progress,
            **kw,
        )
