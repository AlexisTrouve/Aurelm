"""v16-bigctx: v1 prompt + 16K context window (no chunking).

Alternative coverage fix: instead of chunking, expand the context window
so the full 7.6K-word turn fits in a single call.
Risk: "lost in the middle" — LLM may forget entities from the center.
"""

from .base import ExtractionVersion
from .v1 import _V1_FACTS_PROMPT, _V1_ENTITY_PROMPT

V16_BIGCTX = ExtractionVersion(
    name="v16-bigctx",
    description="v1 prompt + num_ctx=16384 (full text in one call)",
    facts_prompt=_V1_FACTS_PROMPT,
    entity_prompt=_V1_ENTITY_PROMPT,
    chunk_by_paragraph=False,
    num_ctx=16384,
)

_VERSIONS_V16: dict[str, ExtractionVersion] = {
    "v16-bigctx": V16_BIGCTX,
}
