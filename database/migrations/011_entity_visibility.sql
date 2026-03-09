-- Migration 011: entity visibility flags (hide / disable)
--
-- hidden = 1  → masquée dans la vue principale, accessible via liens croisés
-- disabled = 1 → complètement désactivée, exclue de toutes les requêtes,
--                liens non-cliquables dans l'UI
--
-- Les deux flags sont indépendants : une entité peut être hidden sans être disabled.

ALTER TABLE entity_entities ADD COLUMN hidden   INTEGER NOT NULL DEFAULT 0;
ALTER TABLE entity_entities ADD COLUMN disabled  INTEGER NOT NULL DEFAULT 0;
ALTER TABLE entity_entities ADD COLUMN disabled_at TEXT;  -- ISO-8601 timestamp, NULL si active
