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
import re
import sqlite3
import unicodedata
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

# Models the proxy serves but we DON'T want in the chat picker.
# WHY: opus-4-6/4-7 are superseded by opus-4-8 (same family, strictly worse) —
# keeping them only clutters the picker; gpt-image-2 is an image-generation
# vendor model, not a chat model, and selecting it would break a chat turn.
# We denylist (not allowlist) so any NEW chat model the proxy adds shows up
# automatically without a code change.
HIDDEN_MODELS = frozenset({
    "claude-opus-4-7",
    "claude-opus-4-6",
    "gpt-image-2",
})

# Reasoning-effort levels offered to the GM, weakest → strongest. `reasoning_effort`
# is the ONE knob across providers: the proxy maps it to Anthropic's adaptive
# `output_config.effort` for opus-4-7/4-8, to a derived thinking budget for the
# classic Claude models (sonnet-4-6 / opus-4-6 / haiku), and passes it straight
# through to GPT. Measured on opus-4-8: low→max is ~2.3x latency, ~2.8x tokens.
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

# xhigh/max are Anthropic-only levels. Sending them to a GPT model does NOT return a
# clean 400 — it kills the upstream connection (measured: 4/4 SSL EOF on gpt-5.6-luna
# with effort=max, while minimal/low/medium/high succeed). So we clamp them down for
# non-Claude models rather than let a picker choice break the turn.
CLAUDE_ONLY_EFFORTS = frozenset({"xhigh", "max"})
OPENAI_MAX_EFFORT = "high"


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


def _clamp_effort(model: str, effort: str) -> str:
    """Reduce an Anthropic-only effort level to the strongest one GPT accepts.

    WHY: xhigh/max are valid for Claude but break the connection on a GPT model
    (see CLAUDE_ONLY_EFFORTS). A GM who picks "max" then switches to a GPT model
    should get GPT's hardest setting, not a dead turn.
    """
    if effort in CLAUDE_ONLY_EFFORTS and not _is_claude(model):
        return OPENAI_MAX_EFFORT
    return effort


def _load_system_prompt(db_path: str | None = None, include_notes: bool = True) -> str:
    """Load the STATIC system prompt: SOUL.md + domain-knowledge.md (+ agent notes).

    ``include_notes`` is kept True for backward compatibility (external callers get
    the historical behaviour). The Agent builds its base with include_notes=False
    and injects agent notes DYNAMICALLY per request via `_recall_agent_notes` — the
    prompt should not carry every note statically anymore (that never refreshed and
    flooded unrelated context).
    """
    base = Path(__file__).resolve().parent / "prompts"
    parts = []

    soul = base / "SOUL.md"
    if soul.exists():
        parts.append(soul.read_text(encoding="utf-8"))

    dk = base / "domain-knowledge.md"
    if dk.exists():
        parts.append(dk.read_text(encoding="utf-8"))

    # Persistent GM instructions stored as agent-type notes (legacy static path).
    if db_path and include_notes:
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


# --------------------------------------------------------------------------- #
# Agent-note recall (memory layer, increment 1)
# --------------------------------------------------------------------------- #

# French stopwords too common to be useful recall keys (kept small on purpose).
_FR_STOPWORDS = frozenset({
    "avec", "dans", "pour", "sans", "sous", "elle", "vous", "nous", "leur",
    "leurs", "cette", "cela", "quoi", "quel", "quelle", "quels", "quelles",
    "mais", "donc", "alors", "plus", "moins", "tout", "tous", "toute", "toutes",
    "etre", "avoir", "fait", "faire", "peux", "peut", "sont", "etait", "chez",
    "comme", "meme", "tres", "deja", "encore",
})


def _norm(text: str) -> str:
    """Lowercase + strip diacritics for accent-insensitive matching."""
    nfkd = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _keywords(text: str) -> set[str]:
    """Meaningful query tokens: >=4 chars, not a stopword."""
    return {
        t for t in re.split(r"[^a-z0-9]+", _norm(text))
        if len(t) >= 4 and t not in _FR_STOPWORDS
    }


def _recall_agent_notes(db_path: str | None, query: str, limit: int = 12) -> str:
    """Return the block of agent-type notes RELEVANT to `query`, or "".

    Selection (no regression + real recall):
    - pinned OR civ_id NULL  -> always injected (general/behavioural instructions;
      preserves the old always-on behaviour so nothing that was injected is lost).
    - civ-scoped note         -> injected only when its civ is named in the query,
      or a query keyword overlaps the note text. That is the recall.
    - note_type != 'agent'    -> never injected.

    Returns a block prefixed with the '\\n\\n---\\n\\n' separator so it appends
    cleanly onto the static base prompt, or "" when nothing is relevant.
    """
    if not db_path:
        return ""
    try:
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                "SELECT title, content, pinned, civ_id FROM notes "
                "WHERE note_type = 'agent' ORDER BY created_at ASC"
            ).fetchall()
        except sqlite3.OperationalError:
            # Old DB (pre-migration-021): no civ_id column -> all treated as global.
            rows = [
                (t, c, p, None)
                for (t, c, p) in conn.execute(
                    "SELECT title, content, pinned FROM notes "
                    "WHERE note_type = 'agent' ORDER BY created_at ASC"
                ).fetchall()
            ]
        civs = conn.execute("SELECT id, name FROM civ_civilizations").fetchall()
        conn.close()
    except Exception:
        return ""  # notes/civ table may not exist on very old DBs

    if not rows:
        return ""

    nquery = _norm(query)
    qkeys = _keywords(query)
    # Civ ids named in the query (normalized civ name is a substring of the query).
    named_civ_ids = {cid for cid, name in civs if name and _norm(name) in nquery}

    selected: list[tuple[str, str]] = []
    for title, content, pinned, civ_id in rows:
        if pinned or civ_id is None:
            selected.append((title, content))          # always-on instruction
            continue
        note_norm = _norm(f"{title or ''} {content or ''}")
        if civ_id in named_civ_ids or any(k in note_norm for k in qkeys):
            selected.append((title, content))          # recalled by relevance

    if not selected:
        return ""

    note_lines = ["## Instructions du MJ", ""]
    for title, content in selected[:limit]:
        note_lines.append(f"**{title or '(instruction)'}**: {content or ''}")
        note_lines.append("")
    return "\n\n---\n\n" + "\n".join(note_lines)


def _recall_memories(db_path: str | None, query: str, limit: int = 12) -> str:
    """Return the agent's self-authored memories RELEVANT to `query`, or "".

    These are written by the agent from GM feedback (see the saveMemory tool).
    Recall rules:
    - mem_type 'preference' -> always injected (behavioural, applies to every answer).
    - mem_type 'fact'       -> injected only when its civ is named in the query or a
      query keyword overlaps the memory (a world ruling is topical, not always-on).
    Only active memories are considered. Tolerant of DBs predating migration 039.
    """
    if not db_path:
        return ""
    try:
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute(
                "SELECT m.mem_key, m.description, m.content, m.civ_id, m.keywords, "
                "       m.mem_type, t.turn_number "
                "FROM agent_memory m "
                "LEFT JOIN turn_turns t ON t.id = m.source_turn "
                "WHERE m.active = 1 ORDER BY m.updated_at DESC"
            ).fetchall()
        except sqlite3.OperationalError:
            conn.close()
            return ""  # table absent (pre-migration-039)
        civs = conn.execute("SELECT id, name FROM civ_civilizations").fetchall()
        conn.close()
    except Exception:
        return ""

    if not rows:
        return ""

    nquery = _norm(query)
    qkeys = _keywords(query)
    named_civ_ids = {cid for cid, name in civs if name and _norm(name) in nquery}

    selected: list[tuple[str, str, str, int | None]] = []
    for mem_key, description, content, civ_id, keywords, mem_type, turn_number in rows:
        if mem_type == "preference":
            selected.append((mem_key, description, content, turn_number))     # always-on
            continue
        text = _norm(f"{mem_key} {description} {content} {keywords}")
        if (civ_id is not None and civ_id in named_civ_ids) or any(k in text for k in qkeys):
            selected.append((mem_key, description, content, turn_number))     # recalled fact

    if not selected:
        return ""

    lines = ["## Mémoire de l'agent (rulings et préférences du MJ — font foi)", ""]
    for mem_key, description, content, turn_number in selected[:limit]:
        head = description or mem_key
        # Surface the anchor so the agent treats the memory as "as of T<n>" and can
        # flag when newer pipeline data may have superseded it.
        anchor = f" (à partir de T{turn_number})" if turn_number is not None else ""
        lines.append(f"**{head}**{anchor}: {content}")
        lines.append("")
    return "\n\n---\n\n" + "\n".join(lines)


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
        # STATIC base only (SOUL + domain-knowledge). Agent notes are injected
        # DYNAMICALLY per request by _recall_agent_notes, so they refresh without a
        # restart and only relevant ones enter context.
        self._system_prompt = _load_system_prompt(config.db_path, include_notes=False)
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

    def _request_extra(self, model: str, effort: str | None = None,
                       show_thinking: bool = False) -> dict:
        """extra_body for the request — reasoning effort + optional visible reasoning.

        WHY only reasoning_effort (and never `thinking.budget_tokens`): the proxy gives
        an explicit client `thinking` block priority and then ignores the effort, so
        sending both would silently disable the effort knob. One mechanism, no overlap.

        show_thinking asks the proxy for a readable reasoning summary (it sets Claude's
        `display: "summarized"`). Note: opus-4-7/4-8 fill that summary only sporadically
        — the classic models stream their thinking regardless. Harmless on GPT (verified).
        """
        extra: dict = {}
        effort = effort or self.config.default_effort
        if effort:
            extra["reasoning_effort"] = _clamp_effort(model, effort)
        if show_thinking:
            extra["include_reasoning"] = True
        return extra

    def _exec_tool(self, tool_name: str, tool_input: dict) -> str:
        """Run a tool (sync), handing the sync proxy client to deepExplore."""
        return _run_tool(
            self.config.db_path, tool_name, tool_input,
            llm_client=self._client, model=self._default_model, proxy=self.config.proxy,
        )

    # -------------------- streaming (HTTP /chat) -------------------- #

    async def answer_streaming(self, history: list[dict], new_message: str,
                               model: str | None = None, effort: str | None = None,
                               show_thinking: bool = False):
        """Async generator yielding (event_type, data) tuples in real time.

        Event types: context_estimate, thinking, text_delta, tool_start,
        tool_result, text (final, carries full content for persistence), error.
        `history` is a list of plain {role, content} messages (already OpenAI-shaped).
        `model` / `effort` / `show_thinking` override the defaults (Flutter pickers).
        """
        model = model or self._default_model
        messages: list[dict] = [
            {"role": "system",
             "content": self._system_prompt
             + _recall_agent_notes(self.config.db_path, new_message)
             + _recall_memories(self.config.db_path, new_message)},
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
                    extra_body=self._request_extra(model, effort, show_thinking),
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
                    # A null entry carries nothing to accumulate — skip it instead of
                    # crashing the whole turn on `tc.index`. Logged (not swallowed) so a
                    # real tool call vanishing this way stays visible in the bot log.
                    if tc is None:
                        log.warning("Null tool_call entry in delta, skipped: %s",
                                    chunk.model_dump_json()[:300])
                        continue
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

    async def answer(self, user_message: str, model: str | None = None,
                     effort: str | None = None) -> str:
        """One agent turn, non-streaming — returns the final text (Discord path).

        No show_thinking: Discord renders text only, a reasoning summary has nowhere
        to go there. Effort falls back to the configured default.
        """
        model = model or self._default_model
        messages: list[dict] = [
            {"role": "system",
             "content": self._system_prompt
             + _recall_agent_notes(self.config.db_path, user_message)
             + _recall_memories(self.config.db_path, user_message)},
            {"role": "user", "content": user_message},
        ]

        for _round in range(MAX_TOOL_ROUNDS):
            try:
                resp = await self._aclient.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=self._tools,
                    extra_body=self._request_extra(model, effort),
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
        """Chat model ids the proxy serves — feeds the Flutter model picker.

        Filters out HIDDEN_MODELS (superseded Claude variants + the image-gen
        vendor model) so the picker only offers current, chat-capable models.
        """
        try:
            result = await self._aclient.models.list()
            return [m.id for m in result.data if m.id not in HIDDEN_MODELS]
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
