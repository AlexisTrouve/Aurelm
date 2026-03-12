import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/database.dart';
import 'database_provider.dart';

// ---------------------------------------------------------------------------
// Watch providers — reactive streams per attachment type
// ---------------------------------------------------------------------------

/// Notes for a specific entity (reactive stream).
final entityNotesProvider =
    StreamProvider.family<List<NoteRow>, int>((ref, entityId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.notesDao.watchNotesForEntity(entityId);
});

/// Notes for a specific subject (reactive stream).
final subjectNotesProvider =
    StreamProvider.family<List<NoteRow>, int>((ref, subjectId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.notesDao.watchNotesForSubject(subjectId);
});

/// Notes for a specific turn (reactive stream).
final turnNotesProvider =
    StreamProvider.family<List<NoteRow>, int>((ref, turnId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.notesDao.watchNotesForTurn(turnId);
});

// ---------------------------------------------------------------------------
// Mutations — called directly via ref.read(databaseProvider)
// ---------------------------------------------------------------------------

Future<void> addNoteForEntity(
    WidgetRef ref, int entityId, String title, String content) {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  return db.notesDao.insertNote(NotesCompanion(
    entityId: Value(entityId),
    title: Value(title),
    content: Value(content),
  ));
}

Future<void> addNoteForSubject(
    WidgetRef ref, int subjectId, String title, String content) {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  return db.notesDao.insertNote(NotesCompanion(
    subjectId: Value(subjectId),
    title: Value(title),
    content: Value(content),
  ));
}

Future<void> addNoteForTurn(
    WidgetRef ref, int turnId, String title, String content) {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  return db.notesDao.insertNote(NotesCompanion(
    turnId: Value(turnId),
    title: Value(title),
    content: Value(content),
  ));
}

Future<void> updateNote(
    WidgetRef ref, int noteId, String title, String content) {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  return db.notesDao.updateNote(noteId, title, content);
}

Future<void> deleteNote(WidgetRef ref, int noteId) {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  return db.notesDao.deleteNote(noteId);
}
