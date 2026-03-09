"""v15-recall-baseline and variants: v1 prompt + paragraph chunking.

Hypothesis: v1's low recall is a coverage problem, not a prompt problem.
Chunking ensures the LLM sees the full text instead of truncating at num_ctx.
"""

from .base import ExtractionVersion
from .v1 import _V1_FACTS_PROMPT, _V1_ENTITY_PROMPT

# v15-recall-baseline: v1 prompt + paragraph chunking (coverage fix)
V15_RECALL_BASELINE = ExtractionVersion(
    name="v15-recall-baseline",
    description="v1 prompt + paragraph chunking (coverage fix)",
    facts_prompt=_V1_FACTS_PROMPT,
    entity_prompt=_V1_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# v15.1-sysnoise: v15 + system prompt anti-bruit
# Target: reduce FP from generic words, singular variants, descriptions.
# Keep the v1 user prompt intact — only add a lightweight system prompt.
_V15_1_SYSTEM = """Tu extrais des entites nommees d'un jeu de civilisation. Regles :
- Extrais le nom EXACT tel qu'il apparait (pluriel, tirets, majuscules).
- UNE seule forme par entite. Si "Faucons Chasseurs" existe, n'extrais pas aussi "Faucon Chasseur".
- JAMAIS de mots seuls generiques : roi, cercle, hall, sel, ordres, assemblees, rumeur, autre, exil, guerre, combat, collaboration.
- JAMAIS de phrases ou descriptions : "Un Faucon Chasseur veteran", "Action libre - L'epave", "Rencontre du troisieme type".
- JAMAIS de prefixes "Un/Une/Le/La/Les" dans le nom."""

V15_1_SYSNOISE = ExtractionVersion(
    name="v15.1-sysnoise",
    description="v15 + system prompt anti-bruit (generiques, variantes, phrases)",
    system_prompt=_V15_1_SYSTEM,
    facts_prompt=_V1_FACTS_PROMPT,
    entity_prompt=_V1_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# v15.2-negex: v15 + negative examples dans le user prompt.
# Instead of a system prompt, embed anti-noise rules directly in user prompt
# with concrete negative examples from observed FP.
_V15_2_FACTS_PROMPT = """Extrait faits et entites nommees de ce tour de jeu. Reponds UNIQUEMENT avec du JSON.

Texte :
{text}

Reponds avec ce JSON UNIQUEMENT :
{{
  "technologies": ["inventions/savoir-faire adoptes"],
  "resources": ["ressources exploitees"],
  "beliefs": ["croyances/lois/rituels nommes"],
  "geography": ["lieux nommes"],
  "entities": [{{"name": "Nom Propre", "type": "person|place|technology|institution|resource|creature|event|civilization|caste|belief", "context": "phrase courte"}}]
}}

ENTITES = noms propres ET termes specifiques du jeu (institutions, castes, technologies, lieux, civilisations, croyances, evenements, creatures).
OUI : "Cercle des Sages", "Argile Vivante", "Gouffre Humide", "Faucons Chasseurs", "Caste de l'Air", "Gourdins", "Lances", "Ciels-clairs".
NON : pronoms (lui, eux, toi, nous), mots communs (homme, femme, chasseurs, artisans, pecheurs, tribus, vallee, village, riviere), phrases longues.
NON : mots seuls generiques (roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers).
NON : descriptions avec articles ("Un Faucon Chasseur veteran", "Une Grande Foret", "Un representant des pecheurs").
NON : variantes d'un meme nom — extrais UNE SEULE forme (la plus complete, avec le bon pluriel/tiret)."""

_V15_2_ENTITY_PROMPT = """Extrait les noms de technologies, lieux, institutions, castes, civilisations, croyances et evenements de ce texte. JSON uniquement.

Texte :
{text}

Reponds UNIQUEMENT avec ce JSON :
{{"entities": [{{"name": "Nom exact", "type": "technology|place|institution|civilization|caste|belief|event", "context": "phrase courte"}}]}}

OUI : "Gourdins", "Lances", "Rhombes", "Glyphes du Gouffre", "Hall des Serments", "Gorge Profonde", "Cheveux de Sang".
NON : mots communs, mots seuls generiques (roi, hall, cercle, sel, ordres, guerre, exil, autre).
NON : descriptions ("Un Faucon Chasseur veteran", "Action libre - L'epave", "Mars Attack").
NON : variantes — UNE forme par entite.
Si rien, retourne {{"entities": []}}."""

V15_2_NEGEX = ExtractionVersion(
    name="v15.2-negex",
    description="v15 + negative examples in user prompt (anti-noise)",
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V15_2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# v15.3-combo: v15.1 system prompt + v15.2 negative examples.
# Belt and suspenders: both system rules AND user prompt negatives.
V15_3_COMBO = ExtractionVersion(
    name="v15.3-combo",
    description="v15 + system anti-bruit + negex user prompt (full combo)",
    system_prompt=_V15_1_SYSTEM,
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V15_2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

# v15.4-temp005: v15 base with temperature 0.05 (more conservative).
# Hypothesis: lower temp = fewer hallucinated entities = less FP.
V15_4_TEMP005 = ExtractionVersion(
    name="v15.4-temp005",
    description="v15 + temperature 0.05 (more conservative output)",
    facts_prompt=_V1_FACTS_PROMPT,
    entity_prompt=_V1_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    temperature=0.05,
)

# ---------------------------------------------------------------------------
# v15.3 micro-variations — single variable changes from the best config.
# Goal: push F1 above 67.2% by targeting the 19 remaining FP.
# All use the same system+negex combo and chunking as v15.3.
# ---------------------------------------------------------------------------

# v15.3.1: temperature=0 — fully deterministic, may reduce variant FP
V15_3_1_TEMP0 = ExtractionVersion(
    name="v15.3.1-temp0",
    description="v15.3 + temperature=0 (deterministic)",
    system_prompt=_V15_1_SYSTEM,
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V15_2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
    temperature=0.0,
)

# v15.3.2: smaller chunks (600w) — more focused per call, less context confusion
V15_3_2_CHUNK600 = ExtractionVersion(
    name="v15.3.2-chunk600",
    description="v15.3 + max_chunk_words=600 (tighter chunks)",
    system_prompt=_V15_1_SYSTEM,
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V15_2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=600,
)

# v15.3.3: larger chunks (1200w) — more context per call, LLM sees more entities together.
# Hypothesis: seeing "Faucons Chasseurs" and "Faucon Chasseur" in the same chunk
# helps the LLM deduplicate them itself.
V15_3_3_CHUNK1200 = ExtractionVersion(
    name="v15.3.3-chunk1200",
    description="v15.3 + max_chunk_words=1200 (wider chunks)",
    system_prompt=_V15_1_SYSTEM,
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V15_2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=1200,
)

# v15.3.4: tighter NON list — adds the specific FP generics still leaking through
_V15_3_4_SYSTEM = """Tu extrais des entites nommees d'un jeu de civilisation. Regles :
- Extrais le nom EXACT tel qu'il apparait (pluriel, tirets, majuscules).
- UNE seule forme par entite. Si "Faucons Chasseurs" existe, n'extrais pas aussi "Faucon Chasseur".
- JAMAIS de mots seuls generiques : roi, cercle, hall, sel, ordres, guerre, combat, rumeur, exil, autre, collaboration, dangers, assemblees, mission, reincarnation, testament.
- JAMAIS de phrases ou descriptions : "Un Faucon Chasseur veteran", "Action libre - L'epave", "Rencontre du troisieme type", "Grande Foret".
- JAMAIS de prefixes "Un/Une/Le/La/Les" dans le nom."""

V15_3_4_TIGHTNON = ExtractionVersion(
    name="v15.3.4-tightnon",
    description="v15.3 + expanded NON list targeting remaining FP generics",
    system_prompt=_V15_3_4_SYSTEM,
    facts_prompt=_V15_2_FACTS_PROMPT,
    entity_prompt=_V15_2_ENTITY_PROMPT,
    chunk_by_paragraph=True,
    max_chunk_words=800,
)

_VERSIONS_V15: dict[str, ExtractionVersion] = {
    "v15-recall-baseline": V15_RECALL_BASELINE,
    "v15.1-sysnoise": V15_1_SYSNOISE,
    "v15.2-negex": V15_2_NEGEX,
    "v15.3-combo": V15_3_COMBO,
    "v15.4-temp005": V15_4_TEMP005,
    "v15.3.1-temp0": V15_3_1_TEMP0,
    "v15.3.2-chunk600": V15_3_2_CHUNK600,
    "v15.3.3-chunk1200": V15_3_3_CHUNK1200,
    "v15.3.4-tightnon": V15_3_4_TIGHTNON,
}
