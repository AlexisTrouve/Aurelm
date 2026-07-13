"""LLM agent for GM questions — single backend: the etheryale proxy.

WHAT: one OpenAI-compatible client talking to the etheryale proxy
(`https://ai.etheryale.com/v1`), which fronts EVERY model (Claude + GPT) behind a
single OpenAI Chat Completions surface. This replaces the old three-backend setup
(Anthropic SDK + Ollama + `claude -p` fallback) with one path.

WHY OpenAI SDK for Claude models: the proxy exposes only the OpenAI surface — even
to reach a Claude model you speak Chat Completions, not the Anthropic Messages API
(cf. the proxy INTEGRATION doc §4). Model choice is data-driven: any proxy model,
overridable per request (Flutter model picker); Claude-only features (extended
thinking) are gated by model name.

COMMENT: two clients — an async one (`AsyncOpenAI`) drives the main streaming loop
(the aiohttp server is async); a sync one (`OpenAI`) is handed to tools that make
their own LLM call (deepExplore), which run inside `asyncio.to_thread`. Auth is
`x-api-key` (not Bearer). The proxy QUEUES instead of returning 429, so the client
timeout is generous and there is no aggressive client-side retry.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from .tool_definitions import TOOL_DEFINITIONS
from .tools import dispatch_tool

if TYPE_CHECKING:
    from .config import BotConfig

log = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 10
# Above this estimated size we inject a "stay focused" reminder into a deep
# tool-calling chain so the model wraps up instead of drifting.
CONTEXT_REMINDER_THRESHOLD = 40_000


# --------------------------------------------------------------------------- #
# Small helpers (pure, reused by streaming + non-streaming paths)
# --------------------------------------------------------------------------- #

def _input_summary(tool_input: dict) -> str:
    """One-line summary of tool input, e.g. 'query=bronze, civName=Confluence'."""
    if not tool_input:
        return ""
    parts = [f"{k}={v!r}" for k, v in list(tool_input.items())[:2]]
    summary = ", ".join(parts)
    return summary[:80] + ("…" if len(summary) > 80 else "")


def _result_summary(result_text: str) -> str:
    """First non-empty, non-heading line of a tool result, truncated to 100 chars."""
    for line in result_text.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:100] + ("…" if len(line) > 100 else "")
    return result_text[:100]


def _estimate_tokens(messages: list[dict]) -> int:
    """Rough token estimate: total chars across message content, divided by 4."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total += sum(len(v) for v in block.values() if isinstance(v, str))
        for tc in msg.get("tool_calls", []) or []:
            fn = tc.get("function", {}) if isinstance(tc, dict) else {}
            total += len(fn.get("arguments", "") or "")
    return total // 4


def _context_reminder(messages: list[dict]) -> dict | None:
    """A short system reminder for long tool chains, or None if the chain is short.

    Keeps the model anchored on the user's question so it concludes instead of
    looping. Returned as an OpenAI `role:"system"` message (appended, not merged).
    """
    if _estimate_tokens(messages) < CONTEXT_REMINDER_THRESHOLD:
        return None
    last_user = next(
        (m["content"] for m in reversed(messages)
         if m.get("role") == "user" and isinstance(m.get("content"), str) and m["content"].strip()),
        "",
    )
    if not last_user:
        return None
    if len(last_user) > 300:
        last_user = last_user[:300] + "..."
    return {
        "role": "system",
        "content": (
            "[RAPPEL CONTEXTE — conversation longue]\n"
            f"Question originale : {last_user}\n"
            "Reste concentre. Si tu as deja assez d'informations via les outils, "
            "formule ta reponse finale maintenant."
        ),
    }


def _vendor_field(obj, name: str):
    """Read a non-standard field the proxy adds (e.g. `thinking`) off an SDK object.

    The OpenAI SDK may surface unknown fields either as an attribute or bucketed in
    `model_extra` depending on version — check both so thinking display is robust.
    """
    v = getattr(obj, name, None)
    if v is not None:
        return v
    extra = getattr(obj, "model_extra", None)
    return extra.get(name) if isinstance(extra, dict) else None


def _build_openai_tools() -> list[dict]:
    """Convert the Anthropic-shaped TOOL_DEFINITIONS to OpenAI function format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOL_DEFINITIONS
    ]


def _is_claude(model: str) -> bool:
    """True for Claude models — the only ones that support the thinking extension."""
    return model.startswith("claude")


def _load_system_prompt(db_path: str | None = None) -> str:
    """Load SOUL.md + domain-knowledge.md + agent notes from DB as the system prompt."""
    base = Path(__file__).resolve().parent / "prompts"
    parts = []

    soul = base / "SOUL.md"
    if soul.exists():
        parts.append(soul.read_text(encoding="utf-8"))

    dk = base / "domain-knowledge.md"
    if dk.exists():
        parts.append(dk.read_text(encoding="utf-8"))

    # Persistent GM instructions stored as agent-type notes.
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


def _run_tool(db_path: str, tool_name: str, tool_input: dict, *, llm_client=None,
              model: str | None = None, proxy: str | None = None) -> str:
    """Execute a tool against the DB (sync — runs in a worker thread).

    llm_client + model are threaded through for the deepExplore sub-agent, which
    makes its own LLM call via the proxy.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        return dispatch_tool(
            conn, tool_name, tool_input,
            db_path=db_path, llm_client=llm_client, model=model, proxy=proxy,
        )
    except Exception as exc:
        log.exception("Tool %s failed", tool_name)
        return f"Error executing {tool_name}: {exc}"
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Agent
# --------------------------------------------------------------------------- #

class Agent:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self._system_prompt = _load_system_prompt(config.db_path)
        self._tools = _build_openai_tools()
        self._default_model = config.model
        self._init_clients()
        log.info("Agent initialized (etheryale proxy, default model=%s)", self._default_model)

    def _init_clients(self) -> None:
        """One proxy, two clients: async (main loop) + sync (tools in threads)."""
        from openai import AsyncOpenAI, OpenAI

        key = self.config.proxy_api_key
        common = dict(
            api_key=key,                          # SDK requires it; proxy reads x-api-key
            base_url=self.config.proxy_base_url,
            default_headers={"x-api-key": key},   # proxy auth is x-api-key, NOT Bearer
            timeout=self.config.request_timeout,
            max_retries=0,                         # proxy queues; don't hammer it
        )
        self._aclient = AsyncOpenAI(**common)
        self._client = OpenAI(**common)

    def _request_extra(self, model: str) -> dict:
        """extra_body for the request — Claude extended thinking, gated by model."""
        if _is_claude(model) and self.config.thinking_budget > 0:
            return {"thinking": {"type": "enabled", "budget_tokens": self.config.thinking_budget}}
        return {}

    def _exec_tool(self, tool_name: str, tool_input: dict) -> str:
        """Run a tool (sync), handing the sync proxy client to deepExplore."""
        return _run_tool(
            self.config.db_path, tool_name, tool_input,
            llm_client=self._client, model=self._default_model, proxy=self.config.proxy,
        )

    # -------------------- streaming (HTTP /chat) -------------------- #

    async def answer_streaming(self, history: list[dict], new_message: str,
                               model: str | None = None):
        """Async generator yielding (event_type, data) tuples in real time.

        Event types: context_estimate, thinking, text_delta, tool_start,
        tool_result, text (final, carries full content for persistence), error.
        `history` is a list of plain {role, content} messages (already OpenAI-shaped).
        `model` overrides the default (Flutter model picker).
        """
        model = model or self._default_model
        messages: list[dict] = [
            {"role": "system", "content": self._system_prompt},
            *history,
            {"role": "user", "content": new_message},
        ]
        collected_tool_calls: list[dict] = []

        for _round in range(MAX_TOOL_ROUNDS):
            yield ("context_estimate", {
                "raw_tokens": _estimate_tokens(messages),
                "round": _round,
            })

            req_messages = messages
            reminder = _context_reminder(messages)
            if reminder:
                req_messages = [*messages, reminder]

            try:
                stream = await self._aclient.chat.completions.create(
                    model=model,
                    messages=req_messages,
                    tools=self._tools,
                    stream=True,
                    extra_body=self._request_extra(model),
                )
            except Exception as exc:  # proxy 502 / upstream 429 / etc. — surface, no fallback
                log.warning("Proxy request failed: %s", exc)
                yield ("error", {"message": str(exc)[:300]})
                return

            content_parts: list[str] = []
            # index -> {id, name, args} — tool_call deltas arrive fragmented
            tool_calls_acc: dict[int, dict] = {}

            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta is None:
                    continue

                think = _vendor_field(delta, "thinking")
                if think:
                    yield ("thinking", {"content": think})

                if delta.content:
                    content_parts.append(delta.content)
                    yield ("text_delta", {"chunk": delta.content})

                for tc in (delta.tool_calls or []):
                    slot = tool_calls_acc.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            slot["name"] = tc.function.name
                        if tc.function.arguments:
                            slot["args"] += tc.function.arguments

            if tool_calls_acc:
                # Assistant turn that requested tools → execute → feed results → loop.
                messages.append({
                    "role": "assistant",
                    "content": "".join(content_parts) or None,
                    "tool_calls": [
                        {"id": s["id"], "type": "function",
                         "function": {"name": s["name"], "arguments": s["args"] or "{}"}}
                        for s in tool_calls_acc.values()
                    ],
                })
                for s in tool_calls_acc.values():
                    try:
                        inp = json.loads(s["args"]) if s["args"] else {}
                    except json.JSONDecodeError:
                        inp = {}
                    inp_str = _input_summary(inp)
                    yield ("tool_start", {"name": s["name"], "input_summary": inp_str})

                    result = await asyncio.to_thread(self._exec_tool, s["name"], inp)
                    messages.append({"role": "tool", "tool_call_id": s["id"], "content": result})

                    tc_info = {
                        "name": s["name"],
                        "input_summary": inp_str,
                        "result_summary": _result_summary(result),
                        "result": result,
                    }
                    collected_tool_calls.append(tc_info)
                    yield ("tool_result", tc_info)
                continue

            # No tools requested → final answer.
            text = "".join(content_parts) or "(Pas de reponse.)"
            yield ("text", {"content": text, "tool_calls": collected_tool_calls})
            return

        yield ("text", {
            "content": "(Limite de tours d'outils atteinte.)",
            "tool_calls": collected_tool_calls,
        })

    # -------------------- non-streaming (Discord) -------------------- #

    async def answer(self, user_message: str, model: str | None = None) -> str:
        """One agent turn, non-streaming — returns the final text (Discord path)."""
        model = model or self._default_model
        messages: list[dict] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_message},
        ]

        for _round in range(MAX_TOOL_ROUNDS):
            try:
                resp = await self._aclient.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=self._tools,
                    extra_body=self._request_extra(model),
                )
            except Exception as exc:
                log.warning("Proxy request failed: %s", exc)
                return f"(Erreur backend : {str(exc)[:150]})"

            msg = resp.choices[0].message
            if msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": msg.content or None,
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    try:
                        inp = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        inp = {}
                    result = await asyncio.to_thread(self._exec_tool, tc.function.name, inp)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                continue

            return msg.content or "(Pas de reponse.)"

        return "(Limite de tours d'outils atteinte.)"

    async def list_models(self) -> list[str]:
        """Model ids the proxy currently serves — feeds the Flutter model picker."""
        try:
            result = await self._aclient.models.list()
            return [m.id for m in result.data]
        except Exception as exc:
            log.warning("models.list failed: %s", exc)
            return []

    # -------------------- session compaction -------------------- #

    async def summarize_for_compress(self, messages: list[dict], mode: str = "compress") -> str:
        """Summarize conversation messages into a compact block (session compaction).

        mode: "compress" (summarize ~20 messages) or "resume" (merge compress blocks).
        """
        if not messages:
            return "(Aucun message a resumer.)"

        lines = []
        for msg in messages:
            prefix = "Utilisateur" if msg.get("role") == "user" else "Agent"
            content = msg.get("content", "")
            if len(content) > 2000:
                content = content[:2000] + "..."
            lines.append(f"{prefix}: {content}")
        conversation_text = "\n\n".join(lines)

        if mode == "resume":
            instruction = (
                "Tu recois plusieurs blocs COMPRESS d'une session MJ/archiviste-IA. "
                "Fusionne-les en UN bloc structure, sans rien perdre. Ultra-concis, "
                "400 mots max. Sections : INTENTION, OUTILS APPELES, FAITS ETABLIS, "
                "ENTITES, TOURS, DECISIONS, POINTS OUVERTS, CONTEXTE LIBRE."
            )
            max_tokens = 2500
        else:
            instruction = (
                "Resume cette conversation MJ/IA. Ultra-concis, 250 mots max, "
                "abreviations OK. Sections : DEMANDE DU MJ, OUTILS APPELES, FAITS "
                "ETABLIS, ENTITES, TOURS, DECISIONS, POINTS OUVERTS, CONTEXTE LIBRE."
            )
            max_tokens = 1500

        try:
            resp = await self._aclient.chat.completions.create(
                model=self._default_model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content":
                     "Tu es un archiviste technique ultra-concis. Faits essentiels, "
                     "zero preambule, densite maximale."},
                    {"role": "user", "content": f"{instruction}\n\nCONVERSATION :\n{conversation_text}"},
                ],
            )
            return resp.choices[0].message.content or "(Resume indisponible.)"
        except Exception as exc:
            log.warning("Summarize failed: %s", exc)
            return "(Resume indisponible.)"
