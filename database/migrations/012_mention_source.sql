-- Migration 012: source tracking for entity mentions (gm vs pj)
--
-- source = 'gm' → mention issue de l'extraction du texte MJ (narratif GM)
-- source = 'pj' → mention issue de l'extraction du texte PJ (réponse joueur)
--
-- DEFAULT 'gm' pour la compatibilité avec les données existantes.

ALTER TABLE entity_mentions ADD COLUMN source TEXT NOT NULL DEFAULT 'gm';
