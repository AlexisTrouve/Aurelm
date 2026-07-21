# `exclude_entity_types` — opt-in entity-type suppression

Lets a caller tell the Aurelm pipeline to **not extract or persist** certain entity
types. Built for a specific arrangement (below), but generic: any type in the active
domain profile can be suppressed.

Shipped: PR #17 (`9bfca5f`, 2026-07-21).

## Why it exists — Aurelm ↔ Demiurgos

Demiurgos (a sibling GM-AI, separate repo) owns a **curated `technology` extractor**
(Sonnet 5, high precision, with provenance) and writes clean technology entities into
each game's Aurelm DB itself via `add_entity`. Aurelm's generic qwen extraction is only
~50–70 % precise on `technology` (monuments/pendants misfiled as technology, alias
dupes). If both run, Aurelm's noise mixes into Demiurgos's clean entities and pollutes
the GM's grounding.

Solution: Demiurgos calls `run_pipeline(..., exclude_entity_types=["technology"])`.
Demiurgos owns technology; Aurelm keeps person / place / event / institution / belief /
caste / civilization / resource / creature.

## API

```python
run_pipeline(..., exclude_entity_types: list[str] | None = None)          # runner.py
run_pipeline_for_channels(..., exclude_entity_types: list[str] | None = None)
```

CLI:

```bash
python -m pipeline.runner --data-dir … --civ … --extraction-version … \
    --exclude-entity-types technology
```

Default `None` (or omitted) = **strictly unchanged behaviour**. The values are
case-insensitive and stripped.

## Where it's consumed (single chokepoint)

The list is subtracted from `FactExtractor.allowed_entity_types` in
`FactExtractor.__init__` (`pipeline/fact_extractor.py`):

```python
_allowed = get_profile(self.version.profile).entity_types
if exclude_entity_types:
    _allowed = _allowed - {t.strip().lower() for t in exclude_entity_types}
self.allowed_entity_types = _allowed
```

That set is the **one ontology gate** every extraction call consults, at
`_coerce_entity_list` (`fact_extractor.py`):

```python
if etype not in allowed:
    continue          # dropped at extraction — not coerced to a default
```

It covers every extraction call site at once: facts+entities, entities-only, focused,
masked passes, and PJ entities. A suppressed type is dropped **before** dedup / validate
/ persist and before any downstream stage runs.

## Why it's cascade-free (no dangling refs)

A never-persisted entity produces no downstream artefacts, by construction:

- **Entities**: one ingest creation site (`runner.py`), fed by the gated list.
- **Relations** (`entity_profiler.py`): targets are resolved against *persisted*
  entities (`name_to_id` built from `entity_entities WHERE is_active=1` + aliases); an
  unresolved target hits `continue` — dropped, never a dangling FK. A suppressed type
  can't be a relation *source* either (it has no profile).
- **Mentions / aliases**: FK'd to `entity_entities(id)` (with `ON DELETE CASCADE`) →
  none created for an absent entity.
- **Subjects**: hold no entity FK at all.

No multi-site filtering is needed — the single early gate solves the whole cascade.

## Two operational constraints for callers

1. **Ordering (write-before-ingest).** Demiurgos must write its technology entities
   (`add_entity`) **before** Aurelm ingests. Aurelm's relations reference entities by
   **name** and silently drop unresolved targets, so ingest-before-write *loses* the
   relations that point at Demiurgos's techniques (not dangling — lost).

2. **Mid-corpus switch is not retroactive.** Exclusion only affects future extractions.
   A DB that already holds qwen-extracted technology rows needs a one-time purge:

   ```sql
   DELETE FROM entity_entities WHERE entity_type = 'technology';
   ```

   `ON DELETE CASCADE` clears their mentions / aliases / relations with them. On a
   **fresh** DB, no purge is needed — cascade-free from the start.

## Tests

`pipeline/tests/test_domain_profile.py` (co-located with the ontology-gate test):

- exclusion subtracts from the gate,
- `None` / omitted is backward-compatible,
- the excluded type is dropped at `_coerce_entity_list` while others survive.

Full pipeline suite green: 270 passed / 5 skipped (3 `_real` live-LLM tests deselected).

## Scope note

This is the *filter*, not an ontology refonte — it reuses the existing profile-aware
gate (`domain_profile.py`, P2 of the generic-engine work). It does not touch extraction
prompts: qwen would ignore a negative "don't extract technology" instruction anyway, and
the deterministic gate catches everything regardless.
