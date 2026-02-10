import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/database.dart';
import '../models/filter_state.dart';
import '../models/turn_with_entities.dart';
import 'database_provider.dart';

final timelineFilterProvider =
    StateNotifierProvider<TimelineFilterNotifier, TimelineFilterState>((ref) {
  return TimelineFilterNotifier();
});

class TimelineFilterNotifier extends StateNotifier<TimelineFilterState> {
  TimelineFilterNotifier() : super(const TimelineFilterState());

  void setCivId(int? id) {
    state = state.copyWith(civId: () => id);
  }

  void setTurnType(String? type) {
    state = state.copyWith(turnType: () => type);
  }

  void reset() {
    state = const TimelineFilterState();
  }
}

final timelineProvider = StreamProvider<List<TurnWithEntities>>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  final filters = ref.watch(timelineFilterProvider);
  return db.turnDao.watchTimeline(civId: filters.civId);
});

final turnDetailProvider =
    StreamProvider.family<TurnRow?, int>((ref, turnId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.turnDao.watchTurn(turnId);
});

final turnSegmentsProvider =
    StreamProvider.family<List<SegmentRow>, int>((ref, turnId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.turnDao.watchSegments(turnId);
});
