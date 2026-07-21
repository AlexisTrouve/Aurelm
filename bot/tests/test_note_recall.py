"""Increment 1 of the agent memory layer: per-request recall of agent notes.

WHAT: `_recall_agent_notes(db_path, query)` returns the block of agent-type notes
RELEVANT to a given query, replacing the old static "inject every agent note at
startup" behaviour. This is the recall layer's proof — same notes, but surfaced
dynamically by relevance (civ mentioned + keyword overlap) instead of all-or-nothing.

WHY the selection rule (no regression, real recall):
- pinned OR civ_id NULL  -> always injected (general/behavioural GM instructions;
  keeps the old always-on behaviour so nothing that used to be injected is lost).
- civ-scoped notes        -> injected ONLY when that civ is named in the query OR a
  query keyword overlaps the note — that's the recall.
- note_type != 'agent'    -> never injected (GM annotations are not agent instructions).
"""
from __future__ import annotations

import sqlite3

from bot.agent import _recall_agent_notes


def _make_db(tmp_path) -> str:
    """A file DB (the function opens its own connection) with a notes table that
    matches the real post-migration-021 schema (has civ_id)."""
    p = tmp_path / "recall.db"
    conn = sqlite3.connect(str(p))
    conn.executescript(
        """
        CREATE TABLE civ_civilizations (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, content TEXT,
            pinned INTEGER NOT NULL DEFAULT 0,
            note_type TEXT NOT NULL DEFAULT 'gm',
            civ_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.executemany(
        "INSERT INTO civ_civilizations (id, name) VALUES (?, ?)",
        [(1, "Confluence"), (2, "Cheveux de Sang")],
    )
    conn.executemany(
        "INSERT INTO notes (title, content, pinned, note_type, civ_id) VALUES (?, ?, ?, ?, ?)",
        [
            ("Style", "Toujours citer le tour dans la reponse.", 0, "agent", None),   # global -> always
            ("Regle bronze", "Le bronze exige l'etain dans ce monde.", 1, "agent", None),  # pinned -> always
            ("Confluence secret", "Les Confluents cachent une reserve d'or.", 0, "agent", 1),  # civ 1
            ("CdS flotte", "Les Cheveux de Sang alignent 12 navires de guerre.", 0, "agent", 2),  # civ 2
            ("Annotation", "Ceci est une note GM ordinaire.", 0, "gm", None),  # not agent -> never
        ],
    )
    conn.commit()
    conn.close()
    return str(p)


def test_global_and_pinned_always_injected(tmp_path):
    out = _recall_agent_notes(_make_db(tmp_path), "sujet totalement hors contexte zzz")
    assert "citer le tour" in out           # global (civ_id NULL) always injected
    assert "bronze exige" in out            # pinned always injected
    assert "reserve d'or" not in out        # civ-scoped, civ not named / no keyword
    assert "12 navires" not in out
    assert "note GM ordinaire" not in out   # note_type != 'agent' never injected


def test_civ_scoped_recalled_when_civ_named(tmp_path):
    out = _recall_agent_notes(_make_db(tmp_path), "fais-moi un recap de la Confluence")
    assert "reserve d'or" in out            # civ 1 note recalled (civ named)
    assert "12 navires" not in out          # civ 2 note not relevant


def test_civ_scoped_recalled_by_keyword(tmp_path):
    out = _recall_agent_notes(_make_db(tmp_path), "combien de navires dans la flotte ?")
    assert "12 navires" in out              # keyword 'navires' hits the CdS note
    assert "reserve d'or" not in out        # no overlap with the Confluence note


def test_no_agent_notes_returns_empty(tmp_path):
    p = tmp_path / "empty.db"
    conn = sqlite3.connect(str(p))
    conn.executescript(
        "CREATE TABLE civ_civilizations(id INTEGER PRIMARY KEY, name TEXT);"
        "CREATE TABLE notes(id INTEGER PRIMARY KEY, title TEXT, content TEXT,"
        " pinned INTEGER DEFAULT 0, note_type TEXT DEFAULT 'gm', civ_id INTEGER, created_at TEXT);"
    )
    conn.commit()
    conn.close()
    assert _recall_agent_notes(str(p), "anything") == ""


def test_recalled_notes_reach_the_system_message(tmp_path):
    """Wiring lock: a query naming a civ must inject that civ's agent note into the
    SYSTEM message actually sent to the proxy — and the static base must no longer
    carry notes. Reuses test_agent's proven fake stream, spying on the messages."""
    import asyncio

    from bot.agent import Agent
    from bot.config import BotConfig
    from bot.tests.test_agent import _FakeChunk, _FakeDelta, _FakeStreamingClient

    db = _make_db(tmp_path)
    agent = Agent(BotConfig(db_path=db, proxy_api_key="test-key"))
    # The static base prompt must NOT statically carry the notes anymore.
    assert "reserve d'or" not in agent._system_prompt

    client = _FakeStreamingClient([[_FakeChunk(_FakeDelta(content="ok"))]])
    captured: dict = {}
    orig = client.chat.completions.create

    async def spy(**kwargs):
        captured["messages"] = kwargs["messages"]
        return await orig(**kwargs)

    client.chat.completions.create = spy  # type: ignore[assignment]
    agent._aclient = client  # type: ignore[assignment]

    async def drive(q: str):
        async for _ in agent.answer_streaming([], q):
            pass

    asyncio.run(drive("fais-moi un recap de la Confluence"))
    sysmsg = captured["messages"][0]["content"]
    assert "reserve d'or" in sysmsg      # civ-scoped note recalled into real context
    assert "citer le tour" in sysmsg     # global instruction always present


def test_missing_civ_id_column_is_tolerated(tmp_path):
    """Old DBs (pre-migration-021) have a notes table without civ_id. The recall
    must not crash — it falls back to treating every agent note as global."""
    p = tmp_path / "old.db"
    conn = sqlite3.connect(str(p))
    conn.executescript(
        "CREATE TABLE civ_civilizations(id INTEGER PRIMARY KEY, name TEXT);"
        "CREATE TABLE notes(id INTEGER PRIMARY KEY, title TEXT, content TEXT,"
        " pinned INTEGER DEFAULT 0, note_type TEXT DEFAULT 'gm', created_at TEXT);"
    )
    conn.execute("INSERT INTO notes (title, content, note_type) VALUES ('R', 'regle importante', 'agent')")
    conn.commit()
    conn.close()
    out = _recall_agent_notes(str(p), "n'importe quoi")
    assert "regle importante" in out
