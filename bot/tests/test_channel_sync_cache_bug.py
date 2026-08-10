"""Regression test: _channel_pending / _channel_sync must use fetch_channel()
(discord.py REST call), not get_channel() (local cache only).

WHY this matters: get_channel() returns None whenever the channel isn't
already in the gateway's local cache — which is exactly the case right after
the bot starts (e.g. right after the setup wizard finishes and the user
immediately clicks per-civ sync). The global sync path (bot/main.py) already
fixed this with fetch_channel() + a comment documenting the trap; the two
per-channel HTTP routes in bot/server.py never got the same fix, so a
freshly-onboarded user's per-civ sync silently 404s while "Sync global"
(which goes through main.py) works fine — exactly the bug reported by Alexi
during the 0.2.4 local dogfood.

This test doesn't spin up a real aiohttp server; it calls the handler
coroutines directly with a fake aiohttp Request (only .match_info and
.query are read by the handlers under test).
"""
from __future__ import annotations

import sqlite3
from types import SimpleNamespace

import pytest

from bot.config import BotConfig
from bot.server import BotServer


class _FakeDiscordClient:
    """Simulates discord.py's Client: get_channel() is cache-only (sync,
    returns None on a cold cache), fetch_channel() is a REST call (async,
    succeeds even when the channel was never cached)."""

    def __init__(self, cached_channel=None, fetchable_channel=None):
        self._cached = cached_channel
        self._fetchable = fetchable_channel

    def get_channel(self, channel_id: int):
        # Cold cache: never returns anything, exactly like right after
        # the gateway connects and hasn't yet populated its channel cache.
        return self._cached

    async def fetch_channel(self, channel_id: int):
        if self._fetchable is None:
            raise Exception("channel not found (simulated 404)")
        return self._fetchable


class _FakeChannel:
    """Minimal stand-in — enough for fetch_and_store()/history() callers
    that this test doesn't actually reach (it only proves the channel
    lookup itself no longer 404s on a cold cache)."""

    def __init__(self, channel_id: int):
        self.id = channel_id

    async def history(self, **kwargs):
        return
        yield  # pragma: no cover — makes this an async generator


def _make_request(channel_id: str, query: dict | None = None):
    return SimpleNamespace(match_info={"channel_id": channel_id}, query=query or {})


@pytest.fixture
def server(tmp_path):
    db_path = str(tmp_path / "aurelm_test.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE civ_civilizations (id INTEGER PRIMARY KEY, name TEXT, "
        "player_name TEXT, discord_channel_id TEXT)"
    )
    conn.execute(
        "INSERT INTO civ_civilizations (name, player_name, discord_channel_id) "
        "VALUES ('Confluence', 'Rubanc', '111222333')"
    )
    conn.execute(
        "CREATE TABLE turn_raw_messages (id INTEGER PRIMARY KEY, "
        "discord_channel_id TEXT, timestamp TEXT)"
    )
    conn.commit()
    conn.close()

    cfg = BotConfig(db_path=db_path)
    return BotServer(cfg)


@pytest.mark.asyncio
async def test_channel_pending_uses_fetch_not_cache(server):
    """A channel absent from the cold cache but reachable via REST must NOT
    404 — this is the exact scenario right after bot startup / onboarding."""
    channel_id = "111222333"
    fake_channel = _FakeChannel(int(channel_id))
    server._discord_client = _FakeDiscordClient(
        cached_channel=None,  # cold cache — simulates fresh bot startup
        fetchable_channel=fake_channel,
    )
    server._discord_connected = True

    resp = await server._channel_pending(_make_request(channel_id))

    assert resp.status != 404, (
        "channel_pending 404'd on a cold cache despite the channel being "
        "fetchable via REST — get_channel() is being used instead of "
        "fetch_channel()"
    )


@pytest.mark.asyncio
async def test_channel_sync_uses_fetch_not_cache(server):
    """Same bug, the actual sync-trigger route (not just the preview)."""
    channel_id = "111222333"
    fake_channel = _FakeChannel(int(channel_id))
    server._discord_client = _FakeDiscordClient(
        cached_channel=None,
        fetchable_channel=fake_channel,
    )
    server._discord_connected = True

    resp = await server._channel_sync(_make_request(channel_id))

    assert resp.status != 404, (
        "channel_sync 404'd on a cold cache despite the channel being "
        "fetchable via REST — get_channel() is being used instead of "
        "fetch_channel()"
    )
