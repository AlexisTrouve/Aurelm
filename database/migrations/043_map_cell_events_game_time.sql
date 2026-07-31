-- Migration 043: in-game time stamp on chronicle events (for aging, done by Demiurgos)
-- WHY: a tile event must be able to age -- a "someone knaps flint" discovery from turn 0
-- should not resurface generations later. But Aurelm owns NO clock and NO aging policy:
-- Demiurgos holds elapsed_years / era pace and decides what expires. This column is pure
-- STORAGE -- Demiurgos writes the in-game year via recordEvent/annotate, and passes a
-- cutoff to groundCivTerrain that Aurelm filters mechanically. Nullable / no default so
-- the events written before stamping (game_time unknown) don't break -- they are simply
-- never time-filtered here (Demiurgos treats them as "unknown time").
-- Keep created_at (wall-clock) as-is: game_time is the GAME's time, the only one aging cares about.

ALTER TABLE map_cell_events ADD COLUMN game_time INTEGER;
