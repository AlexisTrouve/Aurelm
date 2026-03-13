import 'package:drift/drift.dart';

import '../database.dart';
import '../tables/notes.dart';

part 'notes_dao.g.dart';

@DriftAccessor(tables: [Notes])
class NotesDao extends DatabaseAccessor<AurelmDatabase> with _$NotesDaoMixin {
  NotesDao(super.db);

  // ---------------------------------------------------------------------------
  // Queries
  // ---------------------------------------------------------------------------

  /// Stream of notes attached to an entity.
  Stream<List<NoteRow>> watchNotesForEntity(int entityId) {
    return (select(notes)
          ..where((n) => n.entityId.equals(entityId))
          ..orderBy([(n) => OrderingTerm.desc(n.createdAt)]))
        .watch();
  }

  /// Stream of notes attached to a subject.
  Stream<List<NoteRow>> watchNotesForSubject(int subjectId) {
    return (select(notes)
          ..where((n) => n.subjectId.equals(subjectId))
          ..orderBy([(n) => OrderingTerm.desc(n.createdAt)]))
        .watch();
  }

  /// Stream of notes attached to a turn.
  Stream<List<NoteRow>> watchNotesForTurn(int turnId) {
    return (select(notes)
          ..where((n) => n.turnId.equals(turnId))
          ..orderBy([(n) => OrderingTerm.desc(n.createdAt)]))
        .watch();
  }

  /// Stream of notes attached to a civilization.
  Stream<List<NoteRow>> watchNotesForCiv(int civId) {
    return (select(notes)
          ..where((n) => n.civId.equals(civId))
          ..orderBy([(n) => OrderingTerm.desc(n.createdAt)]))
        .watch();
  }

  /// Stream of all pinned notes (pinned = 1), regardless of attachment.
  Stream<List<NoteRow>> watchPinnedNotes() {
    return (select(notes)
          ..where((n) => n.pinned.equals(1))
          ..orderBy([(n) => OrderingTerm.desc(n.createdAt)]))
        .watch();
  }

  /// Stream of agent notes (note_type = 'agent') — injected into system prompt.
  Stream<List<NoteRow>> watchAgentNotes() {
    return (select(notes)
          ..where((n) => n.noteType.equals('agent'))
          ..orderBy([(n) => OrderingTerm.desc(n.createdAt)]))
        .watch();
  }

  // ---------------------------------------------------------------------------
  // Mutations
  // ---------------------------------------------------------------------------

  /// Insert a new note and return the generated row id.
  Future<int> insertNote(NotesCompanion companion) {
    final now = DateTime.now().toIso8601String();
    final toInsert = companion.copyWith(
      createdAt: Value(now),
      updatedAt: Value(now),
    );
    // Log for diagnosis — surfaces FK constraint or schema issues
    print('[NotesDao] insertNote: entity=${companion.entityId}, '
        'subject=${companion.subjectId}, turn=${companion.turnId}');
    return into(notes).insert(toInsert);
  }

  /// Update title and content of an existing note.
  Future<void> updateNote(int noteId, String title, String content) {
    return (update(notes)..where((n) => n.id.equals(noteId))).write(
      NotesCompanion(
        title: Value(title),
        content: Value(content),
        updatedAt: Value(DateTime.now().toIso8601String()),
      ),
    );
  }

  /// Toggle the pinned flag on a note.
  Future<void> togglePinned(int noteId, bool pinned) {
    return (update(notes)..where((n) => n.id.equals(noteId))).write(
      NotesCompanion(
        pinned: Value(pinned ? 1 : 0),
        updatedAt: Value(DateTime.now().toIso8601String()),
      ),
    );
  }

  /// Delete a note by id.
  Future<void> deleteNote(int noteId) {
    return (delete(notes)..where((n) => n.id.equals(noteId))).go();
  }
}
