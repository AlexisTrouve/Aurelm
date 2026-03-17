import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';

import 'tables/civilizations.dart';
import 'tables/turns.dart';
import 'tables/entities.dart';
import 'tables/mentions.dart';
import 'tables/relations.dart';
import 'tables/pipeline_runs.dart';
import 'tables/subjects.dart';
import 'tables/notes.dart';

import 'daos/civilization_dao.dart';
import 'daos/turn_dao.dart';
import 'daos/entity_dao.dart';
import 'daos/relation_dao.dart';
import 'daos/pipeline_dao.dart';
import 'daos/subject_dao.dart';
import 'daos/notes_dao.dart';

part 'database.g.dart';

@DriftDatabase(
  tables: [
    CivCivilizations,
    TurnTurns,
    TurnSegments,
    EntityEntities,
    EntityAliases,
    EntityMentions,
    EntityRelations,
    PipelineRuns,
    // Subject tracking tables (migration 006)
    SubjectSubjects,
    SubjectOptions,
    SubjectResolutions,
    // Notes (migration 019+020)
    Notes,
  ],
  daos: [
    CivilizationDao,
    TurnDao,
    EntityDao,
    RelationDao,
    PipelineDao,
    SubjectDao,
    NotesDao,
  ],
)
class AurelmDatabase extends _$AurelmDatabase {
  AurelmDatabase(super.e);

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        // Python manages the full schema — Drift is query-only.
        // _ensureMigrations() in setup handles missing tables/columns.
        onCreate: (_) async {},
        onUpgrade: (_, __, ___) async {},
      );

  static AurelmDatabase open(String dbPath) {
    return AurelmDatabase(_openConnection(dbPath));
  }
}

/// Idempotent migrations — ensures Drift-required tables/columns exist.
/// Runs synchronously in the NativeDatabase setup callback (before any query).
/// Each statement is wrapped in try/catch to handle "already exists" gracefully.
void _ensureMigrations(dynamic db) {
  const statements = [
    // Migration 019: notes table
    '''CREATE TABLE IF NOT EXISTS notes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id   INTEGER REFERENCES entity_entities(id) ON DELETE CASCADE,
        subject_id  INTEGER REFERENCES subject_subjects(id) ON DELETE CASCADE,
        turn_id     INTEGER REFERENCES turn_turns(id) ON DELETE CASCADE,
        title       TEXT NOT NULL DEFAULT '',
        content     TEXT NOT NULL DEFAULT '',
        created_at  TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )''',
    // Migration 020: pinned + note_type
    "ALTER TABLE notes ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE notes ADD COLUMN note_type TEXT NOT NULL DEFAULT 'gm'",
    // Migration 016: chat sessions
    '''CREATE TABLE IF NOT EXISTS chat_sessions (
        id          TEXT PRIMARY KEY,
        title       TEXT NOT NULL DEFAULT '',
        created_at  TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
        db_path     TEXT
    )''',
    '''CREATE TABLE IF NOT EXISTS chat_messages (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
        role        TEXT NOT NULL,
        content     TEXT NOT NULL,
        tool_calls  TEXT,
        created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )''',
    // Migration 018: subject tags
    "ALTER TABLE subject_subjects ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'",
    // Migration 015: source_quote on subjects
    "ALTER TABLE subject_subjects ADD COLUMN source_quote TEXT",
    // Lore link cache — persists linked text across app restarts.
    // entity_count tracks when cache should be invalidated (entity set changed).
    '''CREATE TABLE IF NOT EXISTS _lore_link_cache (
        text_hash   TEXT PRIMARY KEY,
        linked_text TEXT NOT NULL,
        entity_count INTEGER NOT NULL DEFAULT 0
    )''',
    // Migration 024: user favorites (entities, subjects, turns)
    '''CREATE TABLE IF NOT EXISTS user_favorites (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        type        TEXT NOT NULL,
        entity_id   INTEGER,
        subject_id  INTEGER,
        turn_id     INTEGER,
        civ_id      INTEGER,
        created_at  TEXT NOT NULL
    )''',
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_favorites_entity"
    "  ON user_favorites(entity_id) WHERE entity_id IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_favorites_subject"
    "  ON user_favorites(subject_id) WHERE subject_id IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_favorites_turn"
    "  ON user_favorites(turn_id) WHERE turn_id IS NOT NULL",
    // Migration 025: per-field GM lock (JSON array of field names)
    "ALTER TABLE entity_entities ADD COLUMN gm_fields TEXT",
    "ALTER TABLE subject_subjects ADD COLUMN gm_fields TEXT",
    // Migration 026: same for turns
    "ALTER TABLE turn_turns ADD COLUMN gm_fields TEXT",
    // Migration 027: inter-civ relations
    '''CREATE TABLE IF NOT EXISTS civ_mentions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        source_civ_id   INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
        target_civ_id   INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
        turn_id         INTEGER NOT NULL REFERENCES turn_turns(id) ON DELETE CASCADE,
        context         TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )''',
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_civ_mentions_unique"
    "  ON civ_mentions(source_civ_id, target_civ_id, turn_id)",
    '''CREATE TABLE IF NOT EXISTS civ_relations (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        source_civ_id   INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
        target_civ_id   INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
        opinion         TEXT NOT NULL DEFAULT 'unknown',
        description     TEXT,
        treaties        TEXT,
        last_turn_id    INTEGER REFERENCES turn_turns(id),
        updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(source_civ_id, target_civ_id)
    )''',
    // Migration 028: civ alias mappings + dismissed false positives
    '''CREATE TABLE IF NOT EXISTS civ_aliases (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        civ_id      INTEGER NOT NULL REFERENCES civ_civilizations(id) ON DELETE CASCADE,
        alias_name  TEXT    NOT NULL,
        created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
    )''',
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_civ_aliases_name ON civ_aliases(alias_name)",
    '''CREATE TABLE IF NOT EXISTS civ_alias_dismissed (
        alias_name  TEXT PRIMARY KEY,
        created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )''',
    // Migration 029: provenance — which source civ + turn first used this alias
    "ALTER TABLE civ_aliases ADD COLUMN source_civ_id INTEGER REFERENCES civ_civilizations(id) ON DELETE SET NULL",
    "ALTER TABLE civ_aliases ADD COLUMN first_seen_turn_id INTEGER REFERENCES turn_turns(id) ON DELETE SET NULL",
  ];

  for (final sql in statements) {
    try {
      db.execute(sql);
    } catch (_) {
      // "duplicate column" or "table already exists" — safe to ignore
    }
  }
}

LazyDatabase _openConnection(String dbPath) {
  return LazyDatabase(() async {
    final file = File(dbPath);
    return NativeDatabase.createInBackground(file, setup: (db) {
      db.execute('PRAGMA foreign_keys = ON');
      _ensureMigrations(db);
    });
  });
}
