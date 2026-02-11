-- Migration 003: Add history column to entity_entities
-- Stores JSON array of chronological events built by the entity profiler.

ALTER TABLE entity_entities ADD COLUMN history TEXT;
