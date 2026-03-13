"""LLM agent for answering GM questions. Supports Anthropic Claude and Ollama backends."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from .tool_definitions import TOOL_DEFINITIONS
from .tools import dispatch_tool

if TYPE_CHECKING:
    from .config import BotConfig

log = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 10


@dataclass
class AgentResult:
    """Result from answer_in_conversation — text response + tool calls performed."""
    response: str
    tool_calls: list[dict] = field(default_factory=list)  # [{name, input_summary, result_summary}]


def _input_summary(tool_input: dict) -> str:
    """One-line summary of tool input, e.g. 'query=bronze, civName=Confluence'."""
    if not tool_input:
        return ""
    parts = [f"{k}={v!r}" for k, v in list(tool_input.items())[:2]]
    summary = ", ".join(parts)
    return summary[:80] + ("\u2026" if len(summary) > 80 else "")


def _result_summary(result_text: str) -> str:
    """First non-empty, non-heading line of a tool result, truncated to 100 chars."""
    for line in result_text.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:100] + ("\u2026" if len(line) > 100 else "")
    return result_text[:100]


def _compress_tool_history(messages: list[dict]) -> list[dict]:
    """Compress old tool_result turns to compact one-liners.

    For each assistant→tool_result pair that's not the most recent, replaces
    the verbose tool_result content with a compact summary:
        tooluse:{name}({input_summary})→{result_first_line}

    To get the tool name we look at the preceding assistant message which
    contains the tool_use blocks (matched by tool_use_id). The last
    tool_result turn is kept intact — Claude needs it to continue reasoning.
    """
    # Find indices of user messages that carry tool_result blocks
    tool_result_indices = [
        i for i, msg in enumerate(messages)
        if msg.get("role") == "user"
        and isinstance(msg.get("content"), list)
        and any(
            isinstance(b, dict) and b.get("type") == "tool_result"
            for b in msg["content"]
        )
    ]

    # Nothing to compress if only one (or zero) tool-result turn
    if len(tool_result_indices) <= 1:
        return messages

    to_compress = set(tool_result_indices[:-1])  # keep last turn intact
    result = []
    for i, msg in enumerate(messages):
        if i not in to_compress:
            result.append(msg)
            continue

        # Build tool_use_id → (name, input) map from the preceding assistant block
        tool_name_map: dict[str, tuple[str, dict]] = {}
        if i > 0:
            prev = messages[i - 1]
            if prev.get("role") == "assistant" and isinstance(prev.get("content"), list):
                for block in prev["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_name_map[block["id"]] = (
                            block.get("name", "tool"),
                            block.get("input", {}),
                        )

        # Replace each long tool_result with compact format
        new_blocks = []
        for block in msg["content"]:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                raw = block.get("content", "")
                if isinstance(raw, str) and len(raw) > 120:
                    tool_id = block.get("tool_use_id", "")
                    name, inp = tool_name_map.get(tool_id, ("tool", {}))
                    inp_str = _input_summary(inp)
                    res_str = _result_summary(raw)
                    # Compact: "tooluse:searchLore(query='bronze')→Argile Vivante…"
                    compact = f"tooluse:{name}({inp_str})\u2192{res_str}"
                    block = {**block, "content": compact}
            new_blocks.append(block)
        result.append({**msg, "content": new_blocks})

    return result


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


def _load_system_prompt(db_path: str | None = None) -> str:
    """Load SOUL.md + domain-knowledge.md + agent notes from DB as system prompt."""
    base = Path(__file__).resolve().parent.parent / "openclaw-config"
    parts = []

    soul = base / "SOUL.md"
    if soul.exists():
        parts.append(soul.read_text(encoding="utf-8"))

    dk = base / "skills" / "aurelm-gm" / "domain-knowledge.md"
    if dk.exists():
        parts.append(dk.read_text(encoding="utf-8"))

    # Inject agent notes from DB (note_type='agent') — persistent GM instructions
    if db_path:
        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT title, content FROM notes WHERE note_type = 'agent' ORDER BY created_at ASC"
            ).fetchall()
            conn.close()
            if rows:
                note_lines = ["## Instructions du MJ", ""]
                for title, content in rows:
                    note_lines.append(f"**{title or '(instruction)'}**: {content or ''}")
                    note_lines.append("")
                parts.append("\n".join(note_lines))
        except Exception:
            pass  # notes table may not exist on older DBs

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


def _run_tool(
    db_path: str,
    tool_name: str,
    tool_input: dict,
    anthropic_client=None,
    proxy: str | None = None,
) -> str:
    """Execute a tool call against the DB.

    anthropic_client and proxy are passed through for deepExplore sub-agent.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        result = dispatch_tool(
            conn, tool_name, tool_input,
            db_path=db_path,
            anthropic_client=anthropic_client,
            proxy=proxy,
        )
        return result
    except Exception as exc:
        log.exception("Tool %s failed", tool_name)
        return f"Error executing {tool_name}: {exc}"
    finally:
        conn.close()


class Agent:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self._claude_prompt = _load_system_prompt(config.db_path)
        self._ollama_prompt = OLLAMA_SYSTEM_PROMPT
        self._backend = "ollama"  # default

        if config.has_anthropic:
            self._backend = "anthropic"
            self._init_anthropic()
        else:
            self._init_ollama()

        log.info("Agent initialized with %s backend", self._backend)

    def _exec_tool(self, tool_name: str, tool_input: dict) -> str:
        """Run a tool, passing anthropic client for deepExplore if available."""
        client = getattr(self, "_anthropic", None)
        return _run_tool(
            self.config.db_path, tool_name, tool_input,
            anthropic_client=client,
            proxy=self.config.proxy,
        )

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

    async def answer_in_conversation(
        self,
        history: list[dict],
        new_message: str,
        on_event: Callable[[str, dict], None] | None = None,
    ) -> AgentResult:
        """Answer a question with full conversation context.

        Args:
            history: List of previous {"role": "user/assistant", "content": "..."} messages.
            new_message: The new user message to answer.
            on_event: Optional callback fired as events happen in real time.
                Called with (event_type, data_dict). Event types:
                - "tool_start": {"name": str, "input_summary": str}
                - "tool_result": {"name": str, "input_summary": str, "result": str, "result_summary": str}
                - "thinking": {"content": str}

        Returns:
            AgentResult with the text response and tool calls performed.
        """
        if self._backend == "anthropic":
            return await self._answer_anthropic_conv(history, new_message, on_event)
        return await self._answer_ollama_conv(history, new_message, on_event)

    async def answer_streaming(
        self, history: list[dict], new_message: str
    ):
        """Async generator that yields (event_type, data) tuples in real time.

        Events yielded between each LLM round — so the caller can send them
        to the client while the next LLM call is in progress.

        Event types: "tool_start", "tool_result", "thinking", "text", "done", "usage".
        The "usage" event is emitted after each LLM round with cumulative token counts.
        """
        import asyncio

        messages: list[dict] = [*history, {"role": "user", "content": new_message}]
        collected_tool_calls: list[dict] = []
        # Cumulative token usage across all rounds
        total_input_tokens = 0
        total_output_tokens = 0

        for _round in range(MAX_TOOL_ROUNDS):
            compressed = _compress_tool_history(messages)

            if self._backend == "anthropic":
                response = await asyncio.to_thread(
                    self._anthropic.messages.create,
                    model="claude-sonnet-4-6",
                    max_tokens=4096,
                    system=self._claude_prompt,
                    tools=self._anthropic_tools,
                    messages=compressed,
                )

                # Accumulate token usage from this round
                if hasattr(response, "usage") and response.usage:
                    total_input_tokens += getattr(response.usage, "input_tokens", 0)
                    total_output_tokens += getattr(response.usage, "output_tokens", 0)
                    yield ("usage", {
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens,
                    })

                # Yield thinking blocks
                for block in response.content:
                    if getattr(block, "type", None) == "thinking":
                        yield ("thinking", {"content": getattr(block, "thinking", "")})

                if response.stop_reason == "tool_use":
                    tool_results = []
                    assistant_content = response.content

                    for block in assistant_content:
                        if block.type == "tool_use":
                            inp_str = _input_summary(block.input)
                            yield ("tool_start", {"name": block.name, "input_summary": inp_str})

                            log.info("Tool call: %s(%s)", block.name, block.input)
                            result = self._exec_tool(block.name, block.input)

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            })

                            tc_info = {
                                "name": block.name,
                                "input_summary": inp_str,
                                "result_summary": _result_summary(result),
                                "result": result,
                            }
                            collected_tool_calls.append(tc_info)
                            yield ("tool_result", tc_info)

                    messages.append({"role": "assistant", "content": assistant_content})
                    messages.append({"role": "user", "content": tool_results})
                    continue

                # Final text
                text_parts = [b.text for b in response.content if hasattr(b, "text")]
                response_text = "\n".join(text_parts) if text_parts else "(Pas de reponse.)"
                yield ("text", {"content": response_text, "tool_calls": collected_tool_calls})
                return

            else:
                # Ollama backend
                import ollama as _ollama
                ollama_messages = [
                    {"role": "system", "content": self._ollama_prompt},
                    *messages,
                ]
                response = await asyncio.to_thread(
                    _ollama.chat,
                    model=self._ollama_model,
                    messages=ollama_messages,
                    tools=_build_ollama_tools(),
                    options={"num_ctx": 8192},
                )
                msg = response.message

                # Ollama provides eval/prompt token counts
                if hasattr(response, "prompt_eval_count"):
                    total_input_tokens += getattr(response, "prompt_eval_count", 0) or 0
                    total_output_tokens += getattr(response, "eval_count", 0) or 0
                    yield ("usage", {
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens,
                    })

                if msg.tool_calls:
                    messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})
                    for tc in msg.tool_calls:
                        fn = tc.function
                        inp_str = _input_summary(fn.arguments)
                        yield ("tool_start", {"name": fn.name, "input_summary": inp_str})

                        result = self._exec_tool(fn.name, fn.arguments)
                        messages.append({"role": "tool", "content": result})

                        tc_info = {
                            "name": fn.name,
                            "input_summary": inp_str,
                            "result_summary": _result_summary(result),
                            "result": result,
                        }
                        collected_tool_calls.append(tc_info)
                        yield ("tool_result", tc_info)
                    continue

                response_text = msg.content if msg.content else "(Pas de reponse.)"
                yield ("text", {"content": response_text, "tool_calls": collected_tool_calls})
                return

        yield ("text", {
            "content": "(Limite de tours d'outils atteinte.)",
            "tool_calls": collected_tool_calls,
        })

    # ------------------------------------------------------------------ #
    # Anthropic backend
    # ------------------------------------------------------------------ #

    async def _answer_anthropic_conv(
        self,
        history: list[dict],
        new_message: str,
        on_event: Callable[[str, dict], None] | None = None,
    ) -> AgentResult:
        """Run one agent turn with conversation history (Anthropic backend).

        Emits real-time events via on_event callback:
        - tool_start / tool_result as tools are called
        - thinking when Claude emits a thinking block
        """
        import asyncio

        def _emit(event_type: str, data: dict) -> None:
            if on_event is not None:
                on_event(event_type, data)

        messages: list[dict] = [*history, {"role": "user", "content": new_message}]
        collected_tool_calls: list[dict] = []

        for _round in range(MAX_TOOL_ROUNDS):
            compressed = _compress_tool_history(messages)

            response = await asyncio.to_thread(
                self._anthropic.messages.create,
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=self._claude_prompt,
                tools=self._anthropic_tools,
                messages=compressed,
            )

            # Emit thinking blocks (from extended thinking or <thinking> tags)
            for block in response.content:
                if getattr(block, "type", None) == "thinking":
                    _emit("thinking", {"content": getattr(block, "thinking", "")})

            if response.stop_reason == "tool_use":
                tool_results = []
                assistant_content = response.content

                for block in assistant_content:
                    if block.type == "tool_use":
                        inp_str = _input_summary(block.input)
                        # Emit tool_start immediately (before execution)
                        _emit("tool_start", {
                            "name": block.name,
                            "input_summary": inp_str,
                        })

                        log.info("Tool call: %s(%s)", block.name, block.input)
                        result = self._exec_tool(block.name, block.input)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                        res_summary = _result_summary(result)
                        tool_call_info = {
                            "name": block.name,
                            "input_summary": inp_str,
                            "result_summary": res_summary,
                            "result": result,  # full result for UI display
                        }
                        collected_tool_calls.append(tool_call_info)

                        # Emit tool_result with full content
                        _emit("tool_result", tool_call_info)

                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})
                continue

            # Final text response
            text_parts = []
            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
            response_text = "\n".join(text_parts) if text_parts else "(Pas de reponse.)"
            return AgentResult(response=response_text, tool_calls=collected_tool_calls)

        return AgentResult(
            response="(Limite de tours d'outils atteinte.)",
            tool_calls=collected_tool_calls,
        )

    async def _answer_anthropic(self, user_message: str) -> str:
        import asyncio

        messages = [{"role": "user", "content": user_message}]

        for _round in range(MAX_TOOL_ROUNDS):
            response = await asyncio.to_thread(
                self._anthropic.messages.create,
                model="claude-sonnet-4-6",
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
                        result = self._exec_tool(block.name, block.input)
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

    async def _answer_ollama_conv(
        self,
        history: list[dict],
        new_message: str,
        on_event: Callable[[str, dict], None] | None = None,
    ) -> AgentResult:
        """Run one agent turn with conversation history (Ollama backend)."""
        import asyncio
        import ollama

        def _emit(event_type: str, data: dict) -> None:
            if on_event is not None:
                on_event(event_type, data)

        messages = [
            {"role": "system", "content": self._ollama_prompt},
            *history,
            {"role": "user", "content": new_message},
        ]
        collected_tool_calls: list[dict] = []

        for _round in range(MAX_TOOL_ROUNDS):
            response = await asyncio.to_thread(
                ollama.chat,
                model=self._ollama_model,
                messages=messages,
                tools=self._ollama_tools,
                options={"num_ctx": 8192},
            )

            msg = response.message

            if msg.tool_calls:
                messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})

                for tc in msg.tool_calls:
                    fn = tc.function
                    inp_str = _input_summary(fn.arguments)
                    _emit("tool_start", {"name": fn.name, "input_summary": inp_str})

                    log.info("Tool call: %s(%s)", fn.name, fn.arguments)
                    result = self._exec_tool(fn.name, fn.arguments)
                    messages.append({"role": "tool", "content": result})

                    tool_call_info = {
                        "name": fn.name,
                        "input_summary": inp_str,
                        "result_summary": _result_summary(result),
                        "result": result,
                    }
                    collected_tool_calls.append(tool_call_info)
                    _emit("tool_result", tool_call_info)
                continue

            response_text = msg.content if msg.content else "(Pas de reponse.)"
            return AgentResult(response=response_text, tool_calls=collected_tool_calls)

        return AgentResult(
            response="(Limite de tours d'outils atteinte.)",
            tool_calls=collected_tool_calls,
        )

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
                    result = self._exec_tool(fn.name, fn.arguments)
                    messages.append({"role": "tool", "content": result})
                continue

            # No tool calls -- return text
            return msg.content if msg.content else "(Pas de reponse.)"

        return "(Limite de tours d'outils atteinte.)"
