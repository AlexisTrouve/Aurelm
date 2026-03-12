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

  TextColumn get title => text().withDefault(const Constant(''))();
  TextColumn get content => text().withDefault(const Constant(''))();

  TextColumn get createdAt => text().named('created_at')();
  TextColumn get updatedAt => text().named('updated_at')();
}
