import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/filter_state.dart';
import '../models/subject_with_details.dart';
import 'database_provider.dart';
import 'favorites_provider.dart';

// ---------------------------------------------------------------------------
// Filter state
// ---------------------------------------------------------------------------

final subjectFilterProvider =
    StateNotifierProvider<SubjectFilterNotifier, SubjectFilterState>((ref) {
  return SubjectFilterNotifier();
});

class SubjectFilterNotifier extends StateNotifier<SubjectFilterState> {
  SubjectFilterNotifier() : super(const SubjectFilterState());

  void setDirection(String? direction) {
    state = state.copyWith(direction: () => direction);
  }

  void setStatus(String? status) {
    state = state.copyWith(subjectStatus: () => status);
  }

  void setCivId(int? id) {
    state = state.copyWith(civId: () => id);
  }

  void setTag(String? tag) {
    state = state.copyWith(selectedTag: () => tag);
  }

  void setFavoritesOnly(bool value) {
    state = state.copyWith(favoritesOnly: value);
  }

  void reset() {
    state = const SubjectFilterState();
  }
}

// ---------------------------------------------------------------------------
// Subject list
// ---------------------------------------------------------------------------

final subjectListProvider = StreamProvider<List<SubjectWithDetails>>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  final filters = ref.watch(subjectFilterProvider);
  final favorites = ref.watch(favoritesProvider);

  return db.subjectDao.watchSubjects(filters).map((list) {
    // Apply favorites filter in-stream — avoids a DB-level join
    if (!filters.favoritesOnly) return list;
    return list.where((s) => favorites.contains('subject_${s.subject.id}')).toList();
  });
});

// ---------------------------------------------------------------------------
// Subject detail
// ---------------------------------------------------------------------------

final subjectDetailProvider =
    StreamProvider.family<SubjectDetail?, int>((ref, subjectId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.subjectDao.watchSubjectDetail(subjectId);
});

/// Reactive set of GM-locked fields for a subject.
/// Empty = no fields protected. Used to show lock badges in subject_detail_screen.
final subjectGmFieldsProvider =
    StreamProvider.family<Set<String>, int>((ref, subjectId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.subjectDao.watchGmFields(subjectId);
});

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/// Manually close a subject with the given status ('resolved' or 'abandoned').
Future<void> closeSubject(WidgetRef ref, int subjectId, String status) {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  return db.subjectDao.updateSubjectStatus(subjectId, status);
}

/// Create a new GM-created subject. Returns the new subject id.
Future<int> createSubject(
  WidgetRef ref, {
  required int civId,
  required String direction,
  required String title,
  required String category,
  String? description,
  List<String> tags = const [],
}) {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  return db.subjectDao.createSubject(
    civId: civId,
    direction: direction,
    title: title,
    category: category,
    description: description,
    tags: tags,
  );
}

/// Update editable fields of an existing subject.
Future<void> updateSubject(
  WidgetRef ref, {
  required int subjectId,
  String? title,
  String? description,
  String? direction,
  String? category,
  String? status,
  List<String>? tags,
}) {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  return db.subjectDao.updateSubject(
    subjectId: subjectId,
    title: title,
    description: description,
    direction: direction,
    category: category,
    status: status,
    tags: tags,
  );
}

// ---------------------------------------------------------------------------
// Stats per civ (used on CivDetail screen)
// ---------------------------------------------------------------------------

final subjectStatsProvider =
    StreamProvider.family<Map<String, int>, int>((ref, civId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.subjectDao.watchSubjectStats(civId);
});

/// Les 5 sujets les plus récents d'une civ — pour le frame CivDetailScreen.
final civRecentSubjectsProvider =
    StreamProvider.family<List<SubjectWithDetails>, int>((ref, civId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.subjectDao
      .watchSubjects(SubjectFilterState(civId: civId))
      .map((list) => list.take(5).toList());
});
