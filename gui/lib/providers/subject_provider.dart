import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/filter_state.dart';
import '../models/subject_with_details.dart';
import 'database_provider.dart';

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
  return db.subjectDao.watchSubjects(filters);
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

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/// Manually close a subject with the given status ('resolved' or 'abandoned').
Future<void> closeSubject(WidgetRef ref, int subjectId, String status) {
  final db = ref.read(databaseProvider);
  if (db == null) throw StateError('No database');
  return db.subjectDao.updateSubjectStatus(subjectId, status);
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
