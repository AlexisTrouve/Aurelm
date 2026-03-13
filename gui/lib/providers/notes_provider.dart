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

/// Notes for a specific civilization (reactive stream).
final civNotesProvider =
    StreamProvider.family<List<NoteRow>, int>((ref, civId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.notesDao.watchNotesForCiv(civId);
});

// ---------------------------------------------------------------------------
// Mutations — called directly via ref.read(databaseProvider)
// ---------------------------------------------------------------------------

Future<void> addNoteForEntity(
    WidgetRef ref, int entityId, String title, String content) async {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  try {
    await db.notesDao.insertNote(NotesCompanion(
      entityId: Value(entityId),
      title: Value(title),
      content: Value(content),
    ));
  } catch (e) {
    // Log FK constraint or table-missing errors for diagnosis
    print('[notes_provider] addNoteForEntity failed: $e');
    rethrow;
  }
}

Future<void> addNoteForSubject(
    WidgetRef ref, int subjectId, String title, String content) async {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  try {
    await db.notesDao.insertNote(NotesCompanion(
      subjectId: Value(subjectId),
      title: Value(title),
      content: Value(content),
    ));
  } catch (e) {
    print('[notes_provider] addNoteForSubject failed: $e');
    rethrow;
  }
}

Future<void> addNoteForCiv(
    WidgetRef ref, int civId, String title, String content) async {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  try {
    await db.notesDao.insertNote(NotesCompanion(
      civId: Value(civId),
      title: Value(title),
      content: Value(content),
    ));
  } catch (e) {
    print('[notes_provider] addNoteForCiv failed: $e');
    rethrow;
  }
}

Future<void> addNoteForTurn(
    WidgetRef ref, int turnId, String title, String content) async {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  try {
    await db.notesDao.insertNote(NotesCompanion(
      turnId: Value(turnId),
      title: Value(title),
      content: Value(content),
    ));
  } catch (e) {
    print('[notes_provider] addNoteForTurn failed: $e');
    rethrow;
  }
}

Future<void> updateNote(
    WidgetRef ref, int noteId, String title, String content) {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  return db.notesDao.updateNote(noteId, title, content);
}

/// Toggle pinned status on a note.
Future<void> toggleNotePinned(WidgetRef ref, int noteId, bool pinned) {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  return db.notesDao.togglePinned(noteId, pinned);
}

Future<void> deleteNote(WidgetRef ref, int noteId) {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  return db.notesDao.deleteNote(noteId);
}
