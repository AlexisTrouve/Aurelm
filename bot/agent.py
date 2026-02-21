"""LLM agent for answering GM questions. Supports Anthropic Claude and Ollama backends."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from .tools import TOOL_DEFINITIONS, dispatch_tool

if TYPE_CHECKING:
    from .config import BotConfig

log = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 10


OLLAMA_SYSTEM_PROMPT = """\
Tu es Aurelm, archiviste expert d'un JDR de civilisation. Tu reponds en francais.

REGLE ABSOLUE: Tu dois TOUJOURS utiliser les outils disponibles pour chercher dans la base de donnees avant de repondre. Ne reponds JAMAIS de memoire. Chaque fait doit venir d'un outil.

Outils principaux:
- listCivs: lister les civilisations
- getCivState: etat d'une civilisation (civName requis)
- searchLore: chercher une entite/concept (query requis)
- getEntityDetail: fiche complete d'une entite (entityName requis)
- sanityCheck: verifier une affirmation (statement requis)
- timeline: chronologie des tours
- getTurnDetail: detail d'un tour (civName + turnNumber requis)
- compareCivs: comparer des civilisations (civNames requis)
- searchTurnContent: recherche plein texte (query requis)

Pour toute question sur le jeu, appelle d'abord un outil, puis reponds avec les resultats."""


def _load_system_prompt() -> str:
    """Load SOUL.md + domain-knowledge.md as system prompt for Claude."""
    base = Path(__file__).resolve().parent.parent / "openclaw-config"
    parts = []

    soul = base / "SOUL.md"
    if soul.exists():
        parts.append(soul.read_text(encoding="utf-8"))

    dk = base / "skills" / "aurelm-gm" / "domain-knowledge.md"
    if dk.exists():
        parts.append(dk.read_text(encoding="utf-8"))

    if not parts:
        return "Tu es Aurelm, archiviste expert du monde de jeu. Reponds en francais."
    return "\n\n---\n\n".join(parts)


def _build_ollama_tools() -> list[dict]:
    """Convert TOOL_DEFINITIONS to Ollama tool format."""
    tools = []
    for t in TOOL_DEFINITIONS:
        tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        })
    return tools


def _run_tool(db_path: str, tool_name: str, tool_input: dict) -> str:
    """Execute a tool call against the DB."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        result = dispatch_tool(conn, tool_name, tool_input)
        return result
    except Exception as exc:
        log.exception("Tool %s failed", tool_name)
        return f"Error executing {tool_name}: {exc}"
    finally:
        conn.close()


class Agent:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self._claude_prompt = _load_system_prompt()
        self._ollama_prompt = OLLAMA_SYSTEM_PROMPT
        self._backend = "ollama"  # default

        if config.has_anthropic:
            self._backend = "anthropic"
            self._init_anthropic()
        else:
            self._init_ollama()

        log.info("Agent initialized with %s backend", self._backend)

    def _init_anthropic(self) -> None:
        import anthropic
        import httpx

        http_client = None
        if self.config.proxy:
            http_client = httpx.Client(proxy=self.config.proxy)

        self._anthropic = anthropic.Anthropic(
            api_key=self.config.anthropic_api_key,
            http_client=http_client,
        )
        self._anthropic_tools = [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["input_schema"],
            }
            for t in TOOL_DEFINITIONS
        ]

    def _init_ollama(self) -> None:
        self._ollama_model = self.config.ollama_model or "llama3.1:8b"
        self._ollama_tools = _build_ollama_tools()
        log.info("Ollama backend: model=%s", self._ollama_model)

    async def answer(self, user_message: str) -> str:
        if self._backend == "anthropic":
            return await self._answer_anthropic(user_message)
        return await self._answer_ollama(user_message)

    # ------------------------------------------------------------------ #
    # Anthropic backend
    # ------------------------------------------------------------------ #

    async def _answer_anthropic(self, user_message: str) -> str:
        import asyncio

        messages = [{"role": "user", "content": user_message}]

        for _round in range(MAX_TOOL_ROUNDS):
            response = await asyncio.to_thread(
                self._anthropic.messages.create,
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=self._claude_prompt,
                tools=self._anthropic_tools,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                tool_results = []
                assistant_content = response.content

                for block in assistant_content:
                    if block.type == "tool_use":
                        log.info("Tool call: %s(%s)", block.name, block.input)
                        result = _run_tool(self.config.db_path, block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})
                continue

            text_parts = []
            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
            return "\n".join(text_parts) if text_parts else "(Pas de reponse.)"

        return "(Limite de tours d'outils atteinte.)"

    # ------------------------------------------------------------------ #
    # Ollama backend
    # ------------------------------------------------------------------ #

    async def _answer_ollama(self, user_message: str) -> str:
        import asyncio
        import ollama

        messages = [
            {"role": "system", "content": self._ollama_prompt},
            {"role": "user", "content": user_message},
        ]

        for _round in range(MAX_TOOL_ROUNDS):
            response = await asyncio.to_thread(
                ollama.chat,
                model=self._ollama_model,
                messages=messages,
                tools=self._ollama_tools,
                options={"num_ctx": 8192},
            )

            msg = response.message

            # Check for tool calls
            if msg.tool_calls:
                # Add assistant message with tool calls
                messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})

                for tc in msg.tool_calls:
                    fn = tc.function
                    log.info("Tool call: %s(%s)", fn.name, fn.arguments)
                    result = _run_tool(self.config.db_path, fn.name, fn.arguments)
                    messages.append({"role": "tool", "content": result})
                continue

            # No tool calls -- return text
            return msg.content if msg.content else "(Pas de reponse.)"

        return "(Limite de tours d'outils atteinte.)"
