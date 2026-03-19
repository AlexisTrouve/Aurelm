import 'package:drift/drift.dart';

/// Drift table for notes — GM annotations attached to an entity, subject, or turn.
/// Exactly one of entity_id / subject_id / turn_id must be non-null per row
/// (enforced by the Python migration, not by Drift).
@DataClassName('NoteRow')
class Notes extends Table {
  @override
  String get tableName => 'notes';

  IntColumn get id => integer().autoIncrement()();

  /// FK to entity_entities.id — null if note is on a subject or turn
  IntColumn get entityId => integer().named('entity_id').nullable()();

  /// FK to subject_subjects.id — null if note is on an entity or turn
  IntColumn get subjectId => integer().named('subject_id').nullable()();

  /// FK to turn_turns.id — null if note is on an entity or subject
  IntColumn get turnId => integer().named('turn_id').nullable()();

  /// FK to civ_civilizations.id — null if note is on an entity/subject/turn
  IntColumn get civId => integer().named('civ_id').nullable()();

  /// FK to a map cell — set when note is attached to a map cell.
  IntColumn get mapId => integer().named('map_id').nullable()();
  IntColumn get mapCellQ => integer().named('map_cell_q').nullable()();
  IntColumn get mapCellR => integer().named('map_cell_r').nullable()();

  TextColumn get title => text().withDefault(const Constant(''))();
  TextColumn get content => text().withDefault(const Constant(''))();

  /// Whether this note should always be shown (even in compact tool output)
  IntColumn get pinned => integer().withDefault(const Constant(0))();

  /// 'gm' = GM annotation, 'agent' = injected into agent system prompt
  TextColumn get noteType =>
      text().named('note_type').withDefault(const Constant('gm'))();

  TextColumn get createdAt => text().named('created_at')();
  TextColumn get updatedAt => text().named('updated_at')();
}
