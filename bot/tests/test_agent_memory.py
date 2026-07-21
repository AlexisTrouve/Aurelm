"""Increment 2 of the agent memory layer: the agent WRITES memories for itself.

The agent saves durable memories from GM feedback (corrections, world rulings,
answer preferences) via `saveMemory`, keyed by a slug so re-saving the same key
UPDATES instead of duplicating (a memory it maintains, not an append-log), and
`forgetMemory` deactivates a stale one. `_recall_memories` surfaces the relevant
ones per request:
- type 'preference'  -> always injected (behavioural, applies to every answer).
- type 'fact'        -> only when its civ is named or a query keyword overlaps.
"""
from __future__ import annotations

import sqlite3

from bot.agent import _recall_memories
from bot.tools import forget_memory, save_memory

# Mirrors migration 039_agent_memory.sql (tests are self-contained).
_SCHEMA = """
CREATE TABLE civ_civilizations (id INTEGER PRIMARY KEY, name TEXT, player_name TEXT);
CREATE TABLE agent_memory (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mem_key     TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    content     TEXT NOT NULL DEFAULT '',
    civ_id      INTEGER REFERENCES civ_civilizations(id) ON DELETE CASCADE,
    keywords    TEXT NOT NULL DEFAULT '',
    mem_type    TEXT NOT NULL DEFAULT 'fact',
    source_turn INTEGER,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.executescript(_SCHEMA)
    c.executemany(
        "INSERT INTO civ_civilizations (id, name) VALUES (?, ?)",
        [(1, "Confluence"), (2, "Cheveux de Sang")],
    )
    c.commit()
    return c


def _file_db(tmp_path) -> tuple[str, sqlite3.Connection]:
    """A file DB (for _recall_memories, which opens its own connection)."""
    p = tmp_path / "mem.db"
    c = sqlite3.connect(str(p))
    c.executescript(_SCHEMA)
    c.executemany(
        "INSERT INTO civ_civilizations (id, name) VALUES (?, ?)",
        [(1, "Confluence"), (2, "Cheveux de Sang")],
    )
    c.commit()
    return str(p), c


def test_save_memory_inserts():
    c = _conn()
    msg = save_memory(c, "confluence-bronze", "Les Confluents n'ont pas de bronze.", civ_id=1)
    assert "enregistr" in msg.lower()
    rows = c.execute("SELECT mem_key, content, civ_id FROM agent_memory").fetchall()
    assert rows == [("confluence-bronze", "Les Confluents n'ont pas de bronze.", 1)]


def test_save_memory_upserts_by_key():
    c = _conn()
    save_memory(c, "confluence-bronze", "pas de bronze", civ_id=1)
    save_memory(c, "confluence-bronze", "ont du bronze depuis T20", civ_id=1)  # correction
    rows = c.execute(
        "SELECT content FROM agent_memory WHERE mem_key='confluence-bronze' AND civ_id=1"
    ).fetchall()
    assert len(rows) == 1                       # updated, not duplicated
    assert rows[0][0] == "ont du bronze depuis T20"


def test_same_key_distinct_across_civs():
    c = _conn()
    save_memory(c, "reserve", "or", civ_id=1)
    save_memory(c, "reserve", "poisson", civ_id=2)   # same key, different civ -> distinct rows
    assert c.execute("SELECT COUNT(*) FROM agent_memory").fetchone()[0] == 2


def test_forget_memory_deactivates():
    c = _conn()
    save_memory(c, "vieux-ruling", "info fausse", civ_id=None)
    msg = forget_memory(c, "vieux-ruling")
    assert "oubli" in msg.lower()
    assert c.execute(
        "SELECT active FROM agent_memory WHERE mem_key='vieux-ruling'"
    ).fetchone()[0] == 0


def test_recall_preference_always_fact_gated(tmp_path):
    db, c = _file_db(tmp_path)
    save_memory(c, "confluence-or", "Les Confluents cachent une reserve d'or.", civ_id=1, mem_type="fact")
    save_memory(c, "style", "Toujours citer le tour.", civ_id=None, mem_type="preference")
    c.close()

    named = _recall_memories(db, "fais un recap de la Confluence")
    assert "reserve d'or" in named          # fact recalled: civ named
    assert "citer le tour" in named         # preference always

    other = _recall_memories(db, "meteo de demain")
    assert "reserve d'or" not in other      # fact: civ not named, no keyword overlap
    assert "citer le tour" in other         # preference still always injected


def test_forgotten_memory_not_recalled(tmp_path):
    db, c = _file_db(tmp_path)
    save_memory(c, "confluence-or", "reserve d'or cachee", civ_id=1)
    forget_memory(c, "confluence-or", civ_id=1)
    c.close()
    assert "reserve d'or" not in _recall_memories(db, "recap Confluence")


def test_dispatch_routes_save_and_forget():
    """Wiring lock: the model's tool call flows through dispatch_tool → a memory row,
    with civName resolved to civ_id; forgetMemory deactivates it."""
    from bot.tools import dispatch_tool

    c = _conn()
    out = dispatch_tool(c, "saveMemory", {
        "key": "confluence-bronze",
        "content": "Les Confluents n'ont pas de bronze.",
        "type": "fact",
        "civName": "Confluence",
    })
    assert "enregistr" in out.lower()
    row = c.execute(
        "SELECT content, civ_id, mem_type FROM agent_memory WHERE mem_key='confluence-bronze'"
    ).fetchone()
    assert row == ("Les Confluents n'ont pas de bronze.", 1, "fact")  # civName -> civ_id=1

    out2 = dispatch_tool(c, "forgetMemory", {"key": "confluence-bronze", "civName": "Confluence"})
    assert "oubli" in out2.lower()
    assert c.execute(
        "SELECT active FROM agent_memory WHERE mem_key='confluence-bronze'"
    ).fetchone()[0] == 0


def test_dispatch_save_requires_key_and_content():
    from bot.tools import dispatch_tool

    c = _conn()
    assert "Error" in dispatch_tool(c, "saveMemory", {"content": "x"})   # no key
    assert "Error" in dispatch_tool(c, "saveMemory", {"key": "k"})       # no content
    assert c.execute("SELECT COUNT(*) FROM agent_memory").fetchone()[0] == 0


def test_recall_missing_table_tolerated(tmp_path):
    p = tmp_path / "notable.db"
    c = sqlite3.connect(str(p))
    c.execute("CREATE TABLE civ_civilizations(id INTEGER PRIMARY KEY, name TEXT)")
    c.commit()
    c.close()
    assert _recall_memories(str(p), "quoi que ce soit") == ""
