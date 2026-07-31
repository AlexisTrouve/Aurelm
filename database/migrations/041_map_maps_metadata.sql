-- Migration 035: map-level metadata
-- WHY: ingesting a Theomen world needs world-scope facts that do not fit per-cell --
-- the seed and pipeline_hash (reproducibility), cell_km (physical scale), wrap_x
-- (the world is a cylinder, so neighbourhood queries must wrap at the meridian), the
-- region bbox, and the biome palette. map_cells already carries a metadata blob but
-- map_maps did not. Additive TEXT column, so every existing read tool is unaffected.

ALTER TABLE map_maps ADD COLUMN metadata TEXT;
