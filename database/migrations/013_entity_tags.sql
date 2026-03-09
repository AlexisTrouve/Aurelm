-- Migration 013: semantic tags for entities
--
-- tags = JSON array of strings from a fixed vocabulary:
--   domain : militaire, religieux, politique, economique, culturel,
--             diplomatique, technologique, mythologique
--   status : actif, disparu, emergent, legendaire
--
-- Assigned by entity_profiler.py via LLM during stage [8/10].
-- NULL = not yet tagged (pre-migration data).

ALTER TABLE entity_entities ADD COLUMN tags TEXT;
