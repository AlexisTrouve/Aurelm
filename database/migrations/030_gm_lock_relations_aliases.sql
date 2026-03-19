-- Migration 030: gm_lock flag on civ_relations and civ_aliases
--
-- Allows the GM to protect a relation or alias from being overwritten by the
-- pipeline. When gm_lock = 1, build_civ_relations and _detect_civ_mentions
-- skip the row entirely.

ALTER TABLE civ_relations ADD COLUMN gm_lock INTEGER NOT NULL DEFAULT 0;
ALTER TABLE civ_aliases   ADD COLUMN gm_lock INTEGER NOT NULL DEFAULT 0;
