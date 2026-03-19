"""Shared fixtures for bot tests — in-memory SQLite with seed data."""

from __future__ import annotations

import sqlite3

import pytest


SEED_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE civ_civilizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    player_name TEXT,
    discord_channel_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE turn_raw_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_message_id TEXT UNIQUE NOT NULL,
    discord_channel_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    author_name TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    attachments TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE turn_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    civ_id INTEGER NOT NULL REFERENCES civ_civilizations(id),
    turn_number INTEGER NOT NULL,
    title TEXT,
    summary TEXT,
    detailed_summary TEXT,
    key_events TEXT,
    choices_made TEXT,
    raw_message_ids TEXT NOT NULL,
    turn_type TEXT NOT NULL DEFAULT 'standard',
    game_date_start TEXT,
    game_date_end TEXT,
    technologies TEXT,
    resources TEXT,
    beliefs TEXT,
    geography TEXT,
    choices_proposed TEXT,
    novelty_summary TEXT,
    new_entity_ids TEXT,
    player_strategy TEXT,
    strategy_tags TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at TEXT,
    UNIQUE(civ_id, turn_number)
);

CREATE TABLE turn_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
    segment_order INTEGER NOT NULL,
    segment_type TEXT NOT NULL,
    content TEXT NOT NULL,
    UNIQUE(turn_id, segment_order)
);

CREATE TABLE entity_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    civ_id INTEGER REFERENCES civ_civilizations(id),
    description TEXT,
    history TEXT,
    first_seen_turn INTEGER REFERENCES turn_turns(id),
    last_seen_turn INTEGER REFERENCES turn_turns(id),
    is_active INTEGER NOT NULL DEFAULT 1,
    hidden INTEGER NOT NULL DEFAULT 0,
    disabled INTEGER NOT NULL DEFAULT 0,
    disabled_at TEXT,
    tags TEXT DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(canonical_name, civ_id)
);

CREATE TABLE entity_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    UNIQUE(entity_id, alias)
);

CREATE TABLE entity_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
    segment_id INTEGER REFERENCES turn_segments(id),
    mention_text TEXT NOT NULL,
    context TEXT
);

CREATE TABLE entity_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    target_entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    description TEXT,
    turn_id INTEGER REFERENCES turn_turns(id),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE subject_subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    civ_id INTEGER NOT NULL REFERENCES civ_civilizations(id),
    source_turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'choice',
    direction TEXT NOT NULL DEFAULT 'mj_to_pj',
    status TEXT NOT NULL DEFAULT 'open',
    source_quote TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE subject_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES subject_subjects(id) ON DELETE CASCADE,
    option_number INTEGER NOT NULL,
    label TEXT NOT NULL,
    description TEXT,
    is_libre INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE subject_resolutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES subject_subjects(id) ON DELETE CASCADE,
    resolved_by_turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
    resolution_text TEXT,
    confidence REAL NOT NULL DEFAULT 0.0,
    is_libre INTEGER NOT NULL DEFAULT 0,
    chosen_option_id INTEGER REFERENCES subject_options(id)
);

CREATE TABLE notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id   INTEGER REFERENCES entity_entities(id) ON DELETE CASCADE,
    subject_id  INTEGER REFERENCES subject_subjects(id) ON DELETE CASCADE,
    turn_id     INTEGER REFERENCES turn_turns(id) ON DELETE CASCADE,
    title       TEXT NOT NULL DEFAULT '',
    content     TEXT NOT NULL DEFAULT '',
    pinned      INTEGER NOT NULL DEFAULT 0,
    note_type   TEXT NOT NULL DEFAULT 'gm',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE map_maps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    image_path      TEXT,
    grid_type       TEXT    NOT NULL DEFAULT 'hex',
    grid_cols       INTEGER NOT NULL DEFAULT 20,
    grid_rows       INTEGER NOT NULL DEFAULT 15,
    parent_map_id   INTEGER REFERENCES map_maps(id),
    parent_cell_q   INTEGER,
    parent_cell_r   INTEGER,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE map_cells (
    map_id              INTEGER NOT NULL REFERENCES map_maps(id),
    q                   INTEGER NOT NULL,
    r                   INTEGER NOT NULL,
    terrain_type        TEXT    NOT NULL DEFAULT 'plain',
    controlling_civ_id  INTEGER REFERENCES civ_civilizations(id),
    entity_id           INTEGER REFERENCES entity_entities(id),
    label               TEXT,
    child_map_id        INTEGER REFERENCES map_maps(id),
    metadata            TEXT,
    PRIMARY KEY (map_id, q, r)
);

CREATE TABLE map_cell_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    map_id      INTEGER NOT NULL REFERENCES map_maps(id),
    q           INTEGER NOT NULL,
    r           INTEGER NOT NULL,
    turn_id     INTEGER REFERENCES turn_turns(id),
    description TEXT    NOT NULL,
    event_type  TEXT    NOT NULL DEFAULT 'note',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    messages_processed INTEGER DEFAULT 0,
    turns_created INTEGER DEFAULT 0,
    entities_extracted INTEGER DEFAULT 0,
    error_message TEXT
);
"""

SEED_DATA = """
INSERT INTO civ_civilizations (name, player_name) VALUES
    ('Civilisation de la Confluence', 'Rubanc'),
    ('Cheveux de Sang', 'PlayerB');

INSERT INTO turn_turns (civ_id, turn_number, title, summary, raw_message_ids, turn_type, game_date_start, technologies, resources, beliefs, geography, choices_proposed, choices_made) VALUES
    (1, 1, 'Fondation', 'Les cinq castes fondent la cite au confluent des deux fleuves.', '[]', 'standard', 'An 1', '["gourdins","pieux"]', '["Poisson","Bois"]', '["Culte des Cinq Elements"]', '["Confluent des deux fleuves"]', NULL, NULL),
    (1, 2, 'Premier Contact', 'Les eclaireurs rapportent une presence etrangere.', '[]', 'first_contact', 'An 5', '["lance"]', NULL, NULL, NULL, '["Envoyer une delegation diplomatique","Renforcer les defenses"]', '["Envoyer une delegation diplomatique"]'),
    (1, 3, 'Decouverte des Ruines', 'Exploration des ruines anciennes revele l argile vivante.', '[]', 'standard', 'An 8', '["Argile Vivante"]', NULL, NULL, '["Ruines Anciennes"]', '["Explorer les ruines","Ignorer les ruines"]', '["Explorer les ruines"]'),
    (2, 1, 'Depart Maritime', 'Les Cheveux de Sang prennent la mer pour explorer.', '[]', 'standard', 'An 1', '["Navigation"]', '["Bois","Poisson"]', NULL, '["Cote maritime"]', NULL, NULL);

INSERT INTO turn_segments (turn_id, segment_order, segment_type, content) VALUES
    (1, 1, 'narrative', 'Au confluent des deux fleuves, cinq castes se reunissent pour fonder une nouvelle civilisation.'),
    (1, 2, 'description', 'Les castes sont: Air, Feu, Eau, Terre, et Ether. Chacune apporte un savoir unique.'),
    (2, 1, 'narrative', 'Des eclaireurs de la caste de l Air rapportent des voiles etrangeres sur la mer.'),
    (2, 2, 'choice', 'Faut-il envoyer une delegation diplomatique ou renforcer les defenses?'),
    (3, 1, 'narrative', 'L expedition vers les ruines anciennes decouvre une substance remarquable: l argile vivante.'),
    (3, 2, 'consequence', 'La technologie de l argile vivante est maintenant disponible.'),
    (4, 1, 'narrative', 'Les Cheveux de Sang construisent des navires et prennent la mer.');

INSERT INTO entity_entities (canonical_name, entity_type, civ_id, description, history, first_seen_turn, last_seen_turn) VALUES
    ('Argile Vivante', 'technology', 1, 'Substance qui durcit instantanement au contact de l air', '["Decouverte lors de l expedition aux ruines anciennes"]', 3, 3),
    ('Caste de l Air', 'institution', 1, 'Une des cinq castes fondatrices', NULL, 1, 2),
    ('Caste du Feu', 'institution', 1, 'Une des cinq castes fondatrices', NULL, 1, 1),
    ('Ruines Anciennes', 'place', 1, 'Site archeologique pre-civilisation', NULL, 3, 3),
    ('Cheveux de Sang', 'institution', 2, 'Civilisation maritime etrangere', NULL, 2, 2);

INSERT INTO entity_aliases (entity_id, alias) VALUES
    (1, 'argile'),
    (1, 'living clay'),
    (2, 'caste air'),
    (5, 'CdS');

INSERT INTO entity_mentions (entity_id, turn_id, segment_id, mention_text, context) VALUES
    (1, 3, 5, 'argile vivante', 'decouvre une substance remarquable: l argile vivante'),
    (1, 3, 6, 'argile vivante', 'La technologie de l argile vivante est maintenant disponible'),
    (2, 1, 1, 'castes', 'cinq castes se reunissent pour fonder'),
    (2, 2, 3, 'caste de l Air', 'Des eclaireurs de la caste de l Air'),
    (3, 1, 2, 'Feu', 'Les castes sont: Air, Feu, Eau'),
    (4, 3, 5, 'ruines anciennes', 'L expedition vers les ruines anciennes'),
    (5, 2, 3, 'voiles etrangeres', 'des voiles etrangeres sur la mer');

INSERT INTO entity_relations (source_entity_id, target_entity_id, relation_type, turn_id) VALUES
    (1, 4, 'discovered_at', 3),
    (2, 1, 'member_of', 1);

INSERT INTO notes (entity_id, title, content, pinned, note_type) VALUES
    (1, 'Propriete speciale', 'L argile vivante durcit au contact de l air en 3 secondes.', 1, 'gm'),
    (1, 'Usage militaire', 'Peut etre utilisee comme armure improvisee.', 0, 'gm');

INSERT INTO notes (title, content, note_type) VALUES
    ('Regle maison', 'Toujours verifier les technologies avant de valider un tour.', 'agent');

INSERT INTO map_maps (name, grid_type, grid_cols, grid_rows) VALUES
    ('Monde', 'hex', 20, 15),
    ('Region Confluent', 'square', 10, 8);

UPDATE map_maps SET parent_map_id = 1, parent_cell_q = 5, parent_cell_r = 3 WHERE id = 2;

INSERT INTO map_cells (map_id, q, r, terrain_type, controlling_civ_id, label) VALUES
    (1, 0, 0, 'plain', 1, 'Confluent'),
    (1, 1, 0, 'forest', NULL, NULL),
    (1, 2, 0, 'mountain', NULL, 'Massif Central'),
    (2, 0, 0, 'river', 1, 'Source'),
    (2, 1, 0, 'plain', 1, NULL);

INSERT INTO map_cells (map_id, q, r, terrain_type, entity_id) VALUES
    (1, 3, 0, 'ruins', 4);

INSERT INTO map_cell_events (map_id, q, r, description, event_type) VALUES
    (1, 0, 0, 'Fondation de la cite au confluent.', 'settlement'),
    (1, 0, 0, 'Premier contact avec les etrangers.', 'diplomatic'),
    (2, 0, 0, 'Source decouverte.', 'discovery');
"""


@pytest.fixture
def db():
    """Create an in-memory SQLite database with seed data."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SEED_SCHEMA)
    conn.executescript(SEED_DATA)
    yield conn
    conn.close()
