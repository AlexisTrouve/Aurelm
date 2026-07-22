"""Increment 2 of the agent memory layer: the agent WRITES memories for itself.

The agent saves durable memories from GM feedback (corrections, world rulings,
answer preferences) via `editMemory`, keyed by a slug so re-saving the same key
UPDATES instead of duplicating (a memory it maintains, not an append-log), and
`editMemory(forget=true)` deactivates a stale one. `_recall_memories` surfaces the relevant
ones per request:
- type 'preference'  -> always injected (behavioural, applies to every answer).
- type 'fact'        -> only when its civ is named or a query keyword overlaps.
"""
from __future__ import annotations

import sqlite3

from bot.agent import _recall_memories
from bot.tools import discover_memory, forget_memory, save_memory

# Mirrors migration 039_agent_memory.sql (tests are self-contained).
_SCHEMA = """
CREATE TABLE civ_civilizations (id INTEGER PRIMARY KEY, name TEXT, player_name TEXT);
CREATE TABLE turn_turns (id INTEGER PRIMARY KEY AUTOINCREMENT, civ_id INTEGER, turn_number INTEGER);
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
    # A turn to anchor memories on (civ 1, turn 12 -> turn_id 1).
    c.execute("INSERT INTO turn_turns (id, civ_id, turn_number) VALUES (1, 1, 12)")
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
    # A turn to anchor memories on (civ 1, turn 12 -> turn_id 1).
    c.execute("INSERT INTO turn_turns (id, civ_id, turn_number) VALUES (1, 1, 12)")
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


def test_editmemory_creates_updates_and_forgets():
    """One tool does everything: dispatch_tool('editMemory', ...) creates (civName
    resolved), updates on the same key, and forgets with forget=true."""
    from bot.tools import dispatch_tool

    c = _conn()
    # create
    out = dispatch_tool(c, "editMemory", {
        "key": "confluence-bronze",
        "content": "Les Confluents n'ont pas de bronze.",
        "type": "fact",
        "civName": "Confluence",
    })
    assert "enregistr" in out.lower()
    assert c.execute(
        "SELECT content, civ_id, mem_type FROM agent_memory WHERE mem_key='confluence-bronze'"
    ).fetchone() == ("Les Confluents n'ont pas de bronze.", 1, "fact")

    # update (same key -> no duplicate)
    dispatch_tool(c, "editMemory", {
        "key": "confluence-bronze", "content": "Ils ont du bronze depuis T20.", "civName": "Confluence",
    })
    rows = c.execute("SELECT content FROM agent_memory WHERE mem_key='confluence-bronze'").fetchall()
    assert len(rows) == 1 and rows[0][0] == "Ils ont du bronze depuis T20."

    # forget
    out2 = dispatch_tool(c, "editMemory", {
        "key": "confluence-bronze", "civName": "Confluence", "forget": True,
    })
    assert "oubli" in out2.lower()
    assert c.execute(
        "SELECT active FROM agent_memory WHERE mem_key='confluence-bronze'"
    ).fetchone()[0] == 0


def test_editmemory_requires_key_and_content():
    from bot.tools import dispatch_tool

    c = _conn()
    assert "Error" in dispatch_tool(c, "editMemory", {"content": "x"})   # no key
    assert "Error" in dispatch_tool(c, "editMemory", {"key": "k"})       # no content (and not forget)
    assert c.execute("SELECT COUNT(*) FROM agent_memory").fetchone()[0] == 0


def test_editmemory_forget_needs_no_content():
    """forget=true must work without content (it ignores the content fields)."""
    from bot.tools import dispatch_tool

    c = _conn()
    save_memory(c, "k", "x", civ_id=None)
    out = dispatch_tool(c, "editMemory", {"key": "k", "forget": True})
    assert "oubli" in out.lower()
    assert c.execute("SELECT active FROM agent_memory WHERE mem_key='k'").fetchone()[0] == 0


# --- increment 3: source_turn anchoring ("as of turn N") --------------------

def test_save_memory_stores_source_turn():
    c = _conn()
    save_memory(c, "confluence-bronze", "pas de bronze", civ_id=1, source_turn=1)
    assert c.execute(
        "SELECT source_turn FROM agent_memory WHERE mem_key='confluence-bronze'"
    ).fetchone()[0] == 1


def test_dispatch_resolves_turn_number_to_id():
    """The model passes a turn NUMBER (T12); dispatch resolves it to the turn_id
    for that civ before storing it as the anchor."""
    from bot.tools import dispatch_tool

    c = _conn()  # seeds turn (civ 1, turn_number 12) -> turn_id 1
    out = dispatch_tool(c, "editMemory", {
        "key": "confluence-bronze",
        "content": "Les Confluents n'ont pas de bronze.",
        "civName": "Confluence",
        "turnNumber": 12,
    })
    assert "enregistr" in out.lower()
    assert c.execute(
        "SELECT source_turn FROM agent_memory WHERE mem_key='confluence-bronze'"
    ).fetchone()[0] == 1  # resolved (civ 1, turn 12) -> turn_id 1


def test_recall_shows_anchor_turn(tmp_path):
    db, c = _file_db(tmp_path)  # seeds turn (civ 1, turn 12) -> turn_id 1
    save_memory(c, "confluence-bronze",
                "Les Confluents n'ont pas de bronze.", civ_id=1, mem_type="fact", source_turn=1)
    c.close()
    out = _recall_memories(db, "recap de la Confluence")
    assert "bronze" in out
    assert "T12" in out  # the anchor is surfaced so the agent reasons "as of T12"


def test_recall_surfaces_the_key(tmp_path):
    """The mem_key must appear in the recalled block so the agent can reuse it via
    editMemory to correct or forget the memory."""
    db, c = _file_db(tmp_path)
    save_memory(c, "confluence-bronze", "pas de bronze", description="Bronze",
                civ_id=1, mem_type="fact")
    c.close()
    out = _recall_memories(db, "recap de la Confluence")
    assert "confluence-bronze" in out  # the key is visible, not just the description


def test_recall_no_anchor_when_source_turn_null(tmp_path):
    db, c = _file_db(tmp_path)
    save_memory(c, "regle-globale", "Le bronze exige l'etain.", civ_id=None, mem_type="preference")
    c.close()
    out = _recall_memories(db, "quoi que ce soit")
    assert "bronze exige" in out
    assert "à partir de T" not in out  # no anchor => no "as of" clause


# --- discoverMemory: the agent READS its own memory -------------------------
# Recall is push-only (relevance-gated), so without this the agent cannot ask
# "what do I already know?" nor look up the key of a memory it wants to correct.

def test_discover_inventory_lists_keys_without_content():
    """No keys -> a compact inventory: keys + descriptions, but NOT the content."""
    c = _conn()
    save_memory(c, "confluence-bronze", "Les Confluents n'ont pas de bronze.",
                description="Bronze de la Confluence", civ_id=1, source_turn=1)
    save_memory(c, "style-citation", "Toujours citer le tour.",
                description="Style de reponse", civ_id=None, mem_type="preference")

    out = discover_memory(c)
    assert "confluence-bronze" in out and "style-citation" in out
    assert "Bronze de la Confluence" in out          # descriptions shown
    assert "n'ont pas de bronze" not in out          # content NOT shown (cheap)
    assert "T12" in out                              # anchor shown in the inventory


def test_discover_by_keys_returns_content():
    c = _conn()
    save_memory(c, "confluence-bronze", "Les Confluents n'ont pas de bronze.", civ_id=1)
    save_memory(c, "style-citation", "Toujours citer le tour.", civ_id=None)

    out = discover_memory(c, keys=["confluence-bronze"])
    assert "n'ont pas de bronze" in out       # full content for the asked key
    assert "citer le tour" not in out         # the other memory is not returned


def test_discover_reports_unknown_keys():
    """An unknown key must be reported, not silently dropped."""
    c = _conn()
    save_memory(c, "connue", "contenu", civ_id=None)
    out = discover_memory(c, keys=["connue", "inexistante"])
    assert "contenu" in out
    assert "inexistante" in out  # explicitly flagged as not found


def test_discover_excludes_inactive_unless_asked():
    c = _conn()
    save_memory(c, "vieille", "info perimee", civ_id=None)
    forget_memory(c, "vieille")

    assert "vieille" not in discover_memory(c)
    assert "vieille" in discover_memory(c, include_inactive=True)


def test_discover_filters_by_civ_and_type():
    c = _conn()
    save_memory(c, "conf-fact", "fait confluence", civ_id=1, mem_type="fact")
    save_memory(c, "cds-fact", "fait cheveux", civ_id=2, mem_type="fact")
    save_memory(c, "pref", "une preference", civ_id=None, mem_type="preference")

    civ_only = discover_memory(c, civ_id=1)
    assert "conf-fact" in civ_only and "cds-fact" not in civ_only

    prefs = discover_memory(c, mem_type="preference")
    assert "pref" in prefs and "conf-fact" not in prefs


def test_dispatch_discovermemory_wiring():
    from bot.tools import dispatch_tool

    c = _conn()
    save_memory(c, "conf-fact", "fait confluence", civ_id=1)
    save_memory(c, "cds-fact", "fait cheveux", civ_id=2)

    out = dispatch_tool(c, "discoverMemory", {"civName": "Confluence"})
    assert "conf-fact" in out and "cds-fact" not in out  # civName -> civ_id filter

    full = dispatch_tool(c, "discoverMemory", {"keys": ["conf-fact"]})
    assert "fait confluence" in full  # content returned for the asked key


def test_discover_empty_is_explicit():
    c = _conn()
    assert "aucune" in discover_memory(c).lower()


def test_recall_missing_table_tolerated(tmp_path):
    p = tmp_path / "notable.db"
    c = sqlite3.connect(str(p))
    c.execute("CREATE TABLE civ_civilizations(id INTEGER PRIMARY KEY, name TEXT)")
    c.commit()
    c.close()
    assert _recall_memories(str(p), "quoi que ce soit") == ""
