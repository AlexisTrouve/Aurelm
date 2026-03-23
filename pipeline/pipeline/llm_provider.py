"""LLM provider abstraction — unified interface for Ollama (local) and OpenRouter (cloud).

Allows all pipeline modules to call LLMs through a single interface,
regardless of whether the model runs locally via Ollama or remotely via OpenRouter.
Default is always Ollama (local) — OpenRouter is opt-in via --llm-provider flag.

Each provider handles its own retry logic for transient errors:
  - Ollama: GGML OOM crashes, connection timeouts
  - OpenRouter: 429 rate limits, 502/503 gateway errors
"""

from __future__ import annotations

import json
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# Ollama model name -> OpenRouter model ID mapping
# User always passes Ollama-style names; OpenRouter provider translates automatically
_OPENROUTER_MODEL_MAP = {
    "qwen3:8b": "qwen/qwen3-8b",
    "qwen3:14b": "qwen/qwen3-14b",
    "qwen3:32b": "qwen/qwen3-32b",
    "llama3.1:8b": "meta-llama/llama-3.1-8b-instruct",
    "llama3.1:70b": "meta-llama/llama-3.1-70b-instruct",
    "mistral-nemo:latest": "mistralai/mistral-nemo",
    "mistral-nemo": "mistralai/mistral-nemo",
}


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All pipeline modules call .generate() or .chat() — the provider
    handles endpoint differences, auth, retry, and response parsing.
    """

    @abstractmethod
    def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        num_ctx: int = 8192,
        seed: int | None = None,
        json_mode: bool = False,
        json_schema: dict | None = None,
    ) -> str:
        """Send a prompt and return the raw text response.

        This is the /api/generate equivalent — single prompt in, text out.
        Used by fact_extractor (httpx direct calls).
        """
        ...

    @abstractmethod
    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4000,
        num_ctx: int = 8192,
        seed: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """Send a chat messages array and return the response text.

        This is the /api/chat equivalent — messages array in, text out.
        Used by entity_profiler, summarizer, alias_resolver (ollama lib calls).
        """
        ...

    @abstractmethod
    def unload(self, model: str) -> None:
        """Unload model from memory (free VRAM). No-op for cloud providers."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for display (e.g. 'ollama', 'openrouter')."""
        ...

    def get_usage_snapshot(self) -> dict:
        """Return a point-in-time snapshot of token/cost usage.

        Used by runner to compute per-turn cost deltas: snapshot before extraction,
        snapshot after, subtract. Providers with real token tracking (OpenRouter)
        return actual values; Ollama returns char-based estimates (free = $0).
        """
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "total_cost": 0.0}

    # ------------------------------------------------------------------
    # Prompt logging hook
    # ------------------------------------------------------------------

    def set_call_context(self, run_id: int | None, turn_id: int | None) -> None:
        """Set the current run/turn context for prompt logging.

        Called by runner at the start of each turn so that all subsequent
        LLM calls are tagged with the correct run_id / turn_id.
        """
        self._log_run_id: int | None = getattr(self, "_log_run_id", None)
        self._log_turn_id: int | None = getattr(self, "_log_turn_id", None)
        self._log_run_id = run_id
        self._log_turn_id = turn_id

    def set_prompt_logger(self, callback) -> None:
        """Register a callable that persists every LLM call to the DB.

        Signature: callback(run_id, turn_id, stage, model, system, prompt, response)
        Set to None to disable logging.
        """
        self._prompt_logger = callback

    def _log_call(
        self, stage: str, model: str,
        system: str | None, prompt: str, response: str,
    ) -> None:
        """Internal: call the registered prompt logger if one is set."""
        logger = getattr(self, "_prompt_logger", None)
        if logger is None:
            return
        run_id = getattr(self, "_log_run_id", None)
        turn_id = getattr(self, "_log_turn_id", None)
        try:
            logger(run_id, turn_id, stage, model, system, prompt, response)
        except Exception:
            pass  # never let logging break the pipeline

    # current_stage: callers set this attribute before generate()/chat() so
    # _log_call() knows which pipeline stage the call belongs to.
    current_stage: str = "unknown"


class OllamaProvider(LLMProvider):
    """Local Ollama provider — wraps both /api/generate and /api/chat.

    Default provider. Uses httpx for generate() calls (fact_extractor pattern)
    and the ollama Python lib for chat() calls (profiler/summarizer/alias pattern).
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        # Lazy-init httpx client (only created when generate() is called)
        self._client: Any = None
        # Char-based usage tracking — Ollama has no real token API, so we
        # count prompt+response chars and estimate tokens (chars/4).
        self._chars_prompt = 0
        self._chars_completion = 0

    def _get_client(self):
        """Lazy-init httpx client to avoid import cost if only chat() is used."""
        if self._client is None:
            import httpx
            self._client = httpx.Client(timeout=300.0)
        return self._client

    def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        num_ctx: int = 8192,
        seed: int | None = None,
        json_mode: bool = False,
        json_schema: dict | None = None,
    ) -> str:
        """Call Ollama /api/generate with retry on transient GPU errors."""
        request_body: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": num_ctx,
                **({"seed": seed} if seed is not None else {}),
            },
        }
        if system:
            request_body["system"] = system
        # Ollama supports structured JSON schema via "format" field
        if json_schema:
            request_body["format"] = json_schema
        elif json_mode:
            request_body["format"] = "json"

        result = self._post_with_retry(
            f"{self.base_url}/api/generate", request_body
        )
        response_text = result.get("response", "").strip()
        # Track chars for usage estimation
        self._chars_prompt += len(prompt) + len(system or "")
        self._chars_completion += len(response_text)
        self._log_call(self.current_stage, model, system, prompt, response_text)
        return response_text

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4000,
        num_ctx: int = 8192,
        seed: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """Call Ollama /api/chat via the ollama Python library."""
        import ollama

        options: dict[str, Any] = {"num_ctx": num_ctx}
        if seed is not None:
            options["seed"] = seed

        response_text = self._chat_with_retry(
            model=model,
            messages=messages,
            json_mode=json_mode,
            options=options,
        )
        # Track chars for usage estimation (sum all message content)
        prompt_chars = sum(len(m.get("content", "")) for m in messages)
        self._chars_prompt += prompt_chars
        self._chars_completion += len(response_text)
        # Log via chat: reconstruct system+user for the logger
        sys_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        self._log_call(self.current_stage, model, sys_msg, user_msg, response_text)
        return response_text

    def unload(self, model: str) -> None:
        """Unload model from VRAM to free GPU memory."""
        try:
            import ollama
            ollama.generate(model=model, prompt="", keep_alive=0)
            print("  Ollama model unloaded from VRAM.")
        except Exception:
            pass  # Non-critical

    @property
    def name(self) -> str:
        return "ollama"

    def get_usage_snapshot(self) -> dict:
        """Char-based usage estimate — Ollama has no real token API.

        Estimates tokens as chars/4 (rough French text ratio).
        Cost is always 0 since Ollama is local.
        """
        est_prompt = self._chars_prompt // 4
        est_completion = self._chars_completion // 4
        return {
            "prompt_tokens": est_prompt,
            "completion_tokens": est_completion,
            "total_tokens": est_prompt + est_completion,
            "total_cost": 0.0,
            "chars_prompt": self._chars_prompt,
            "chars_completion": self._chars_completion,
        }

    def _post_with_retry(
        self, url: str, body: dict, max_retries: int = 3
    ) -> dict:
        """POST to Ollama with retry on GGML OOM / transient errors."""
        client = self._get_client()
        for attempt in range(max_retries):
            try:
                response = client.post(url, json=body)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 5 * (attempt + 1)
                    print(f"  RETRY {attempt+1}/{max_retries} in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise

    def _chat_with_retry(
        self,
        model: str,
        messages: list[dict[str, str]],
        json_mode: bool,
        options: dict,
        max_retries: int = 3,
    ) -> str:
        """Call ollama.chat() with retry on transient errors."""
        import ollama

        format_arg = "json" if json_mode else None
        for attempt in range(max_retries):
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "options": options,
                    "keep_alive": 60,
                }
                if format_arg:
                    kwargs["format"] = format_arg
                response = ollama.chat(**kwargs)
                return response["message"]["content"]
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 5 * (attempt + 1)
                    print(f"  RETRY {attempt+1}/{max_retries} in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise

    def close(self):
        """Close httpx client if it was created."""
        if self._client is not None:
            self._client.close()
            self._client = None


class OpenRouterProvider(LLMProvider):
    """OpenRouter cloud provider — OpenAI-compatible API.

    Translates Ollama model names to OpenRouter IDs automatically.
    Handles rate limits (429) and gateway errors (502/503) with retry.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        # API key: explicit > env var > .env file
        self.api_key = api_key or self._load_api_key()
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY env var "
                "or add it to pipeline/.env"
            )
        self.base_url = base_url
        self._client: Any = None
        # Usage tracking — accumulates across all calls
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_cost = 0.0

    def get_usage(self) -> dict:
        """Return accumulated usage stats across all calls."""
        return {
            "prompt_tokens": self._total_prompt_tokens,
            "completion_tokens": self._total_completion_tokens,
            "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
            "total_cost": self._total_cost,
        }

    def reset_usage(self):
        """Reset usage counters (e.g. between benchmark runs)."""
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_cost = 0.0

    def get_usage_snapshot(self) -> dict:
        """Return a copy of current usage — use before/after extraction for per-turn deltas."""
        return dict(self.get_usage())

    def _track_usage(self, result: dict):
        """Extract and accumulate usage info from OpenRouter response."""
        usage = result.get("usage", {})
        self._total_prompt_tokens += usage.get("prompt_tokens", 0)
        self._total_completion_tokens += usage.get("completion_tokens", 0)
        # OpenRouter uses "cost" (not "total_cost") in the usage object
        cost = usage.get("cost")
        if cost is not None:
            try:
                self._total_cost += float(cost)
            except (TypeError, ValueError):
                pass

    def _get_client(self):
        """Lazy-init httpx client with auth headers."""
        if self._client is None:
            import httpx
            self._client = httpx.Client(
                timeout=300.0,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    # OpenRouter recommends these for tracking
                    "HTTP-Referer": "https://github.com/AlexisTrouve/Aurelm",
                    "X-Title": "Aurelm Pipeline",
                },
            )
        return self._client

    @staticmethod
    def _load_api_key() -> str | None:
        """Load API key from env var or pipeline/.env file."""
        key = os.environ.get("OPENROUTER_API_KEY")
        if key:
            return key
        # Try loading from .env files in common locations
        for env_path in [
            Path(__file__).parent.parent / ".env",  # pipeline/.env
            Path.cwd() / ".env",
        ]:
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("OPENROUTER_API_KEY="):
                        return line.split("=", 1)[1].strip()
        return None

    @staticmethod
    def _strip_ollama_directives(text: str | None) -> str | None:
        """Remove Ollama-native directives that have no meaning on OpenRouter.

        /no_think is a qwen3 Ollama directive to disable thinking mode.
        On OpenRouter, thinking is controlled via the reasoning API param,
        so /no_think becomes confusing plaintext that the model sees literally.
        """
        if not text:
            return text
        # Remove /no_think (standalone line or inline)
        cleaned = re.sub(r'^\s*/no_think\s*$', '', text, flags=re.MULTILINE)
        # Collapse multiple blank lines left behind
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()

    def _map_model(self, model: str) -> str:
        """Translate Ollama model name to OpenRouter model ID.

        If the model is already an OpenRouter ID (contains '/'), pass through.
        """
        if "/" in model:
            return model  # Already an OpenRouter ID
        mapped = _OPENROUTER_MODEL_MAP.get(model)
        if mapped:
            return mapped
        # Fallback: try qwen/<model> pattern (e.g. qwen3:8b -> qwen/qwen3-8b)
        clean = model.replace(":", "-")
        print(f"  Warning: No mapping for '{model}', trying 'qwen/{clean}'")
        return f"qwen/{clean}"

    def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        num_ctx: int = 8192,
        seed: int | None = None,
        json_mode: bool = False,
        json_schema: dict | None = None,
    ) -> str:
        """Call OpenRouter chat/completions (generate-style, single prompt).

        OpenRouter only has a chat endpoint, so we convert the prompt
        to a messages array with optional system message.
        Strips Ollama-native directives (/no_think) from system prompt.
        """
        # Strip Ollama-native directives that confuse the model on OpenRouter
        clean_system = self._strip_ollama_directives(system)

        messages = []
        if clean_system:
            messages.append({"role": "system", "content": clean_system})
        messages.append({"role": "user", "content": prompt})

        return self.chat(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            num_ctx=num_ctx,
            seed=seed,
            json_mode=json_mode or json_schema is not None,
        )

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4000,
        num_ctx: int = 8192,
        seed: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """Call OpenRouter chat/completions endpoint.

        Automatically strips Ollama-native directives from system messages
        and passes seed for reproducible output.
        """
        or_model = self._map_model(model)

        # Strip Ollama-native directives (/no_think) from system messages
        clean_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                cleaned = self._strip_ollama_directives(msg.get("content", ""))
                if cleaned:
                    clean_messages.append({"role": "system", "content": cleaned})
            else:
                clean_messages.append(msg)

        # OpenRouter has no VRAM constraint — enforce a minimum max_tokens to avoid
        # JSON truncation. Ollama needs low num_predict (thinking tokens budget),
        # but OpenRouter's reasoning.effort:"none" removes that concern.
        effective_max_tokens = max(max_tokens, 8192)

        body: dict[str, Any] = {
            "model": or_model,
            "messages": clean_messages,
            "temperature": temperature,
            "max_tokens": effective_max_tokens,
            # Force high-precision providers only — exclude FP4/Int4 quantizations
            # that destroy instruction following and French text quality
            "provider": {
                "quantizations": ["bf16", "fp16", "fp8", "fp6", "int8"],
            },
            # Disable thinking/reasoning tokens for Qwen3 models — they consume
            # the token budget and degrade structured output (JSON) quality
            "reasoning": {
                "effort": "none",
            },
        }
        # Seed for reproducible sampling (OpenRouter supports it)
        if seed is not None:
            body["seed"] = seed
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        result = self._post_with_retry(body)
        # Track token usage and cost from response
        self._track_usage(result)
        # OpenRouter response format: {"choices": [{"message": {"content": "..."}}]}
        choices = result.get("choices", [])
        if not choices:
            return ""
        response_text = choices[0].get("message", {}).get("content", "").strip()
        sys_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        self._log_call(self.current_stage, model, sys_msg, user_msg, response_text)
        return response_text

    def unload(self, model: str) -> None:
        """No-op for cloud providers — nothing to unload."""
        pass

    @property
    def name(self) -> str:
        return "openrouter"

    def _post_with_retry(self, body: dict, max_retries: int = 3) -> dict:
        """POST to OpenRouter with retry on rate limits and gateway errors."""
        client = self._get_client()
        url = f"{self.base_url}/chat/completions"

        for attempt in range(max_retries):
            try:
                response = client.post(url, json=body)

                # Handle rate limits explicitly
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 10))
                    wait = min(retry_after, 30)
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response.json()

            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 5 * (attempt + 1)
                    print(f"  RETRY {attempt+1}/{max_retries} in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    raise

        # Should not reach here, but just in case
        raise RuntimeError("Max retries exceeded for OpenRouter request")

    def close(self):
        """Close httpx client."""
        if self._client is not None:
            self._client.close()
            self._client = None


def create_provider(
    provider_name: str = "ollama",
    api_key: str | None = None,
    base_url: str | None = None,
) -> LLMProvider:
    """Factory function to create the right provider from a name string.

    Args:
        provider_name: "ollama" (default, local) or "openrouter" (cloud)
        api_key: API key for OpenRouter (optional, falls back to env/file)
        base_url: Custom base URL (optional, uses provider defaults)

    Returns:
        Configured LLMProvider instance
    """
    if provider_name == "ollama":
        return OllamaProvider(base_url=base_url or "http://localhost:11434")
    elif provider_name == "openrouter":
        return OpenRouterProvider(
            api_key=api_key,
            base_url=base_url or "https://openrouter.ai/api/v1",
        )
    elif provider_name == "claude_proxy":
        # Claude proxy (etheryale.com) uses OpenRouter-compatible API
        return OpenRouterProvider(
            api_key=api_key,
            base_url=base_url or "https://ai.etheryale.com/v1",
        )
    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider_name}'. "
            "Use 'ollama', 'openrouter', or 'claude_proxy'."
        )


# ---------------------------------------------------------------------------
# LLMConfig — per-stage model configuration
# ---------------------------------------------------------------------------

# Valid stage names that can have per-stage model overrides
VALID_STAGES = {"extraction", "focus", "summarization", "profiling", "aliases", "validation", "subjects"}


@dataclass
class LLMConfig:
    """Per-stage LLM model and prompt configuration.

    Allows different models and prompt versions per pipeline stage.
    The provider is global — no mixing ollama/openrouter within a run.

    Attributes:
        provider_name: "ollama" or "openrouter" (global for all stages)
        default_model: Fallback model when a stage has no override
        stage_models: Optional per-stage model overrides
        stage_prompt_versions: Optional per-stage prompt version overrides
            e.g. {"aliases": "v1-llama"} to use the Llama-tuned confirmation prompt
    """

    provider_name: str
    default_model: str
    stage_models: dict[str, str] = field(default_factory=dict)
    stage_prompt_versions: dict[str, str] = field(default_factory=dict)
    stage_score_thresholds: dict[str, float] = field(default_factory=dict)

    def get_model(self, stage: str) -> str:
        """Return the model for a given pipeline stage, or the default."""
        return self.stage_models.get(stage, self.default_model)

    def get_prompt_version(self, stage: str) -> str | None:
        """Return the prompt version for a stage, or None if not set."""
        return self.stage_prompt_versions.get(stage)

    def get_score_threshold(self, stage: str, default: float = 0.7) -> float:
        """Return the score threshold for a stage, or the given default."""
        return self.stage_score_thresholds.get(stage, default)

    def summary(self) -> str:
        """Human-readable summary for log output."""
        lines = [f"provider={self.provider_name}, default={self.default_model}"]
        for stage in sorted(self.stage_models):
            pv = self.stage_prompt_versions.get(stage)
            st = self.stage_score_thresholds.get(stage)
            extras = []
            if pv:
                extras.append(f"prompt: {pv}")
            if st is not None:
                extras.append(f"threshold: {st:.0%}")
            extras_str = f" ({', '.join(extras)})" if extras else ""
            lines.append(f"  {stage}: {self.stage_models[stage]}{extras_str}")
        for stage in sorted(self.stage_prompt_versions):
            if stage not in self.stage_models:
                lines.append(f"  {stage}: (default model) prompt={self.stage_prompt_versions[stage]}")
        return "\n".join(lines)


def load_llm_config(path: str | Path) -> LLMConfig:
    """Load an LLMConfig from a JSON file.

    Expected format:
        {
          "provider": "ollama",
          "default_model": "qwen3:14b",
          "stages": {
            "extraction": { "model": "qwen3:14b" },
            "summarization": { "model": "llama3.1:8b" }
          }
        }

    Raises:
        FileNotFoundError: if the file doesn't exist
        ValueError: if required fields are missing or stages are unknown
    """
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    provider = data.get("provider")
    if not provider:
        raise ValueError(f"LLM config missing 'provider' field: {path}")
    if provider not in ("ollama", "openrouter", "claude_proxy"):
        raise ValueError(f"Unknown provider '{provider}' in {path}. Use 'ollama', 'openrouter', or 'claude_proxy'.")

    default_model = data.get("default_model")
    if not default_model:
        raise ValueError(f"LLM config missing 'default_model' field: {path}")

    # Parse per-stage overrides (model + optional prompt_version + score_threshold)
    stage_models: dict[str, str] = {}
    stage_prompt_versions: dict[str, str] = {}
    stage_score_thresholds: dict[str, float] = {}
    for stage_name, stage_cfg in data.get("stages", {}).items():
        if stage_name not in VALID_STAGES:
            raise ValueError(
                f"Unknown stage '{stage_name}' in {path}. "
                f"Valid stages: {sorted(VALID_STAGES)}"
            )
        if isinstance(stage_cfg, dict):
            model = stage_cfg.get("model")
            pv = stage_cfg.get("prompt_version")
            st = stage_cfg.get("score_threshold")
        else:
            model = stage_cfg
            pv = None
            st = None
        if model:
            stage_models[stage_name] = model
        if pv:
            stage_prompt_versions[stage_name] = pv
        if st is not None:
            stage_score_thresholds[stage_name] = float(st)

    return LLMConfig(
        provider_name=provider,
        default_model=default_model,
        stage_models=stage_models,
        stage_prompt_versions=stage_prompt_versions,
        stage_score_thresholds=stage_score_thresholds,
    )


def llm_config_from_cli(model: str, provider_name: str) -> LLMConfig:
    """Build an LLMConfig from CLI --model and --llm-provider args.

    All stages use the same model (backward-compatible behavior).
    """
    return LLMConfig(provider_name=provider_name, default_model=model)
