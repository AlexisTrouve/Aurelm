-- Migration 014: Track which turn each alias first appeared
-- Enables the naming history timeline in the Flutter entity detail screen.
-- first_seen_turn_id: the turn where the alias entity was first extracted
--                     (copied from entity_entities.first_seen_turn at merge time)

ALTER TABLE entity_aliases ADD COLUMN first_seen_turn_id INTEGER REFERENCES turn_turns(id);
