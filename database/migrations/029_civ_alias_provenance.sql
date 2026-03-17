-- Add provenance columns to civ_aliases so each alias remembers which
-- source civ (player) used it and in which turn it first appeared.
-- Both nullable — existing rows and manual aliases have no provenance.
ALTER TABLE civ_aliases ADD COLUMN source_civ_id   INTEGER REFERENCES civ_civilizations(id) ON DELETE SET NULL;
ALTER TABLE civ_aliases ADD COLUMN first_seen_turn_id INTEGER REFERENCES turn_turns(id) ON DELETE SET NULL;
