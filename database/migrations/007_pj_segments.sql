-- Migration 007: Add source column to turn_segments
-- Distinguishes GM narrative (source='gm') from player response (source='pj').
-- Both are stored on the same turn_id (UNIQUE civ_id, turn_number constraint preserved).
-- Existing rows default to 'gm' (backward compatible).
ALTER TABLE turn_segments ADD COLUMN source TEXT NOT NULL DEFAULT 'gm';
