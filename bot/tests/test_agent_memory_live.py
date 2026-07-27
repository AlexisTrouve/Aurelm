"""LIVE-LLM test: does the agent actually USE its memory tools?

Everything else about the memory layer is mechanically tested (write, recall, review,
links). What no unit test can prove is BEHAVIOUR: given SOUL.md, does a real model
call `editMemory` when Arthur corrects it? This drives one real turn through the
etheryale proxy and checks the wire.

Opt-in — the default suite must stay fast and offline:

    AURELM_LIVE_LLM=1 py -3.12 -m pytest bot/tests/test_agent_memory_live.py -q -s

Cost: a single turn (a few tool calls) on the configured model.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sqlite3
from pathlib import Path

import pytest

from bot.agent import Agent, _recall_memories
from bot.config import BotConfig

# Dev-only test key, direct use authorised (CLAUDE.md). Env wins if set.
_KEY = os.environ.get("ETHERYALE_API_KEY") or "eai_ESu-8usnN17_6I09zZ2F5A15rGnrZVfQ"
_FIXTURE = Path(__file__).resolve().parents[2] / "gui" / "integration_test" / "fixtures" / "e2e.db"

pytestmark = pytest.mark.skipif(
    not os.environ.get("AURELM_LIVE_LLM"),
    reason="live-LLM test — set AURELM_LIVE_LLM=1 to run",
)


def _live_db(tmp_path) -> str:
    """A realistic DB (the E2E fixture) with the seeded memories cleared, so any
    memory found afterwards was written by the agent during this test."""
    if not _FIXTURE.exists():
        pytest.skip(f"fixture DB missing: {_FIXTURE} (run build_fixture.py)")
    db = tmp_path / "live.db"
    shutil.copy(_FIXTURE, db)
    conn = sqlite3.connect(db)
    conn.execute("DELETE FROM agent_memory_links")
    conn.execute("DELETE FROM agent_memory")
    conn.commit()
    conn.close()
    return str(db)


def _run(agent: Agent, message: str) -> list:
    events: list = []

    async def drive():
        async for event in agent.answer_streaming([], message):
            events.append(event)

    asyncio.run(drive())
    return events


def test_agent_memorises_a_gm_ruling(tmp_path):
    """Arthur states a world rule as feedback -> the agent must persist it itself.

    Uses pytest's tmp_path (not TemporaryDirectory): on Windows the sqlite file stays
    locked briefly and eager cleanup raises PermissionError.
    """
    db = _live_db(tmp_path)
    agent = Agent(BotConfig(db_path=db, proxy_api_key=_KEY, default_effort="low"))

    events = _run(agent, "Petite correction à retenir pour la suite : dans ce monde, "
                         "le bronze exige du commerce d'étain. Retiens-le.")

    tools_called = [d.get("name") for t, d in events if t == "tool_start"]
    errors = [d for t, d in events if t == "error"]
    print(f"\n[live] tools called: {tools_called}")
    print(f"[live] errors: {errors}")
    assert not errors, f"the turn errored: {errors}"

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT mem_key, content, mem_type FROM agent_memory WHERE active = 1"
        ).fetchall()
    finally:
        conn.close()
    print(f"[live] memories written: {rows}")

    assert "editMemory" in tools_called, (
        f"the agent never called editMemory on explicit GM feedback "
        f"(tools it did call: {tools_called})"
    )
    assert rows, "editMemory was called but no active memory row exists"
    blob = " ".join(f"{k} {c}" for k, c, _ in rows).lower()
    assert "etain" in blob or "étain" in blob or "bronze" in blob, (
        f"the memory does not carry the ruling: {rows}"
    )

    # The loop closes without a second LLM call: the new memory is recalled.
    recalled = _recall_memories(db, "est-ce que le bronze est accessible ?")
    print(f"[live] recall block:\n{recalled}")
    assert "bronze" in recalled.lower(), "the fresh memory was not recalled"


def test_agent_memorises_an_implicit_correction(tmp_path):
    """The harder, realistic case: Arthur corrects the agent WITHOUT saying "remember
    this". SOUL.md says a correction is memorable on its own — does the model act on it?
    """
    db = _live_db(tmp_path)
    agent = Agent(BotConfig(db_path=db, proxy_api_key=_KEY, default_effort="low"))

    events = _run(agent, "Non, tu te trompes : les Confluents n'ont jamais eu de bronze, "
                         "leur métallurgie s'arrête au cuivre.")

    tools_called = [d.get("name") for t, d in events if t == "tool_start"]
    print(f"\n[live-implicit] tools called: {tools_called}")

    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT mem_key, content, mem_type, civ_id FROM agent_memory WHERE active = 1"
        ).fetchall()
    finally:
        conn.close()
    print(f"[live-implicit] memories written: {rows}")

    assert "editMemory" in tools_called, (
        f"the agent did not memorise an implicit correction (tools: {tools_called})"
    )
    assert rows, "editMemory called but nothing persisted"


def test_agent_links_memory_to_an_article(tmp_path):
    """`links` has NEVER been seen on the wire. Arthur states a ruling about a specific
    entity and asks to attach it to that article -> the agent should call editMemory
    with links=['entity:Argile Vivante'], producing a row in agent_memory_links. That
    row is what lets recall show "→ liens : Argile Vivante" and the agent drill back in.
    """
    db = _live_db(tmp_path)
    agent = Agent(BotConfig(db_path=db, proxy_api_key=_KEY, default_effort="low"))

    events = _run(agent, "Règle à retenir sur la Confluence : l'Argile Vivante durcit "
                         "instantanément au contact de l'air. Rattache cette note à "
                         "l'article de l'entité « Argile Vivante » pour qu'on y revienne.")

    tools_called = [d.get("name") for t, d in events if t == "tool_start"]
    errors = [d for t, d in events if t == "error"]
    print(f"\n[live-links] tools called: {tools_called}")
    print(f"[live-links] errors: {errors}")
    assert not errors, f"the turn errored: {errors}"
    assert "editMemory" in tools_called, f"editMemory never called (tools: {tools_called})"

    conn = sqlite3.connect(db)
    try:
        links = conn.execute(
            "SELECT m.mem_key, e.canonical_name FROM agent_memory_links l "
            "JOIN agent_memory m ON m.id = l.memory_id "
            "LEFT JOIN entity_entities e ON e.id = l.entity_id "
            "WHERE m.active = 1"
        ).fetchall()
    finally:
        conn.close()
    print(f"[live-links] links written: {links}")
    assert links, "editMemory was called but produced NO link row (the `links` path is dead on the wire)"
    assert any(name and "argile" in name.lower() for _, name in links), (
        f"a link exists but not to the Argile Vivante entity: {links}"
    )


def test_agent_forgets_a_memory_the_gm_says_is_wrong(tmp_path):
    """`forget=true` has NEVER been seen on the wire. Pre-seed an ACTIVE memory whose
    key surfaces at recall (its keyword matches the message), then Arthur says it is
    false -> the agent should call editMemory(key=..., forget=true), flipping active=0.
    """
    db = _live_db(tmp_path)
    # Seed one active fact memory. Its keyword ("bronze") matches Arthur's message, so
    # _recall_memories surfaces its KEY in the prompt — the only way the agent knows
    # which key to forget.
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO agent_memory (mem_key, description, content, civ_id, keywords,"
        " mem_type, active, created_at, updated_at) VALUES"
        " ('confluence-bronze', 'Bronze de la Confluence',"
        " 'Les Confluents maîtrisent le bronze.', 1, 'bronze metallurgie', 'fact', 1,"
        " datetime('now'), datetime('now'))")
    conn.commit()
    conn.close()

    agent = Agent(BotConfig(db_path=db, proxy_api_key=_KEY, default_effort="low"))
    events = _run(agent, "Correction : c'est faux, les Confluents n'ont jamais eu de "
                         "bronze. Cette info est erronée, oublie-la.")

    tools_called = [d.get("name") for t, d in events if t == "tool_start"]
    errors = [d for t, d in events if t == "error"]
    print(f"\n[live-forget] tools called: {tools_called}")
    print(f"[live-forget] errors: {errors}")
    assert not errors, f"the turn errored: {errors}"
    assert "editMemory" in tools_called, f"editMemory never called (tools: {tools_called})"

    conn = sqlite3.connect(db)
    try:
        active = conn.execute(
            "SELECT active FROM agent_memory WHERE mem_key = 'confluence-bronze'"
        ).fetchone()
    finally:
        conn.close()
    print(f"[live-forget] confluence-bronze active flag: {active}")
    assert active is not None, "the seeded memory vanished entirely"
    assert active[0] == 0, "the agent did not forget the memory the GM called false (active still 1)"
