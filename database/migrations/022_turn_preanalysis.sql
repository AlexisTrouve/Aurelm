-- Turn preanalysis: novelty tracking + player strategy per turn
-- Stage 6.5 in the pipeline (between extraction and subjects)

ALTER TABLE turn_turns ADD COLUMN novelty_summary TEXT;
ALTER TABLE turn_turns ADD COLUMN new_entity_ids TEXT;
ALTER TABLE turn_turns ADD COLUMN player_strategy TEXT;
ALTER TABLE turn_turns ADD COLUMN strategy_tags TEXT;
