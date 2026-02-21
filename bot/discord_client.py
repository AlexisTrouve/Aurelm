"""Discord bot client: listens for mentions/DMs and routes to the agent."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from .agent import Agent

log = logging.getLogger(__name__)

# Max Discord message length
MAX_MSG_LEN = 2000


class AurelmBot(discord.Client):
    def __init__(self, agent: Agent, proxy: str | None = None, **kwargs) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents, proxy=proxy, **kwargs)
        self.agent = agent
        self._on_ready_callback: callable | None = None

    def set_on_ready(self, callback: callable) -> None:
        self._on_ready_callback = callback

    async def on_ready(self) -> None:
        log.info("Discord bot connected as %s", self.user)
        if self._on_ready_callback:
            self._on_ready_callback()

    async def on_message(self, message: discord.Message) -> None:
        # Ignore own messages
        if message.author == self.user:
            return

        # Respond to DMs or mentions
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mention = self.user in message.mentions if self.user else False

        if not is_dm and not is_mention:
            return

        # Strip the mention from the text
        content = message.content
        if is_mention and self.user:
            content = content.replace(f"<@{self.user.id}>", "").strip()
            content = content.replace(f"<@!{self.user.id}>", "").strip()

        if not content:
            return

        log.info("Question from %s: %s", message.author.display_name, content[:100])

        async with message.channel.typing():
            try:
                reply = await self.agent.answer(content)
            except Exception:
                log.exception("Agent error")
                reply = "Erreur interne. Veuillez reessayer."

        # Split long replies into chunks
        try:
            for chunk in _split_message(reply):
                await message.reply(chunk)
        except discord.Forbidden:
            log.warning("No permission to reply in %s", message.channel)
        except discord.DiscordException:
            log.exception("Failed to send reply")


def _split_message(text: str) -> list[str]:
    """Split a message into chunks respecting Discord's 2000 char limit."""
    if len(text) <= MAX_MSG_LEN:
        return [text]

    chunks = []
    while text:
        if len(text) <= MAX_MSG_LEN:
            chunks.append(text)
            break
        # Try to split at a newline
        split_at = text.rfind("\n", 0, MAX_MSG_LEN)
        if split_at == -1:
            split_at = MAX_MSG_LEN
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks
