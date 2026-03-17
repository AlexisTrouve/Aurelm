import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/database.dart';
import '../data/daos/turn_dao.dart';
import '../models/filter_state.dart';
import '../models/turn_with_entities.dart';
import 'database_provider.dart';
import 'favorites_provider.dart';

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

  void setSelectedTag(String? tag) {
    state = state.copyWith(selectedTag: () => tag);
  }

  void setFromTurn(int? n) {
    state = state.copyWith(fromTurn: () => n);
  }

  void setToTurn(int? n) {
    state = state.copyWith(toTurn: () => n);
  }

  void setFavoritesOnly(bool value) {
    state = state.copyWith(favoritesOnly: value);
  }

  void reset() {
    state = const TimelineFilterState();
  }
}

final timelineProvider = StreamProvider<List<TurnWithEntities>>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  final filters = ref.watch(timelineFilterProvider);
  final favorites = ref.watch(favoritesProvider);

  // Pass both filters — turnType was previously ignored in the DAO
  return db.turnDao
      .watchTimeline(
        civId: filters.civId,
        turnType: filters.turnType,
        selectedTag: filters.selectedTag,
        fromTurn: filters.fromTurn,
        toTurn: filters.toTurn,
      )
      .map((list) {
    // Apply favorites filter in-stream — avoids a DB-level join
    if (!filters.favoritesOnly) return list;
    return list.where((t) => favorites.contains('turn_${t.turn.id}')).toList();
  });
});

/// All unique thematic tags from the DB, for the filter bar.
final turnTagsProvider = FutureProvider<List<String>>((ref) async {
  final db = ref.watch(databaseProvider);
  if (db == null) return [];
  return db.turnDao.allThematicTags();
});

final turnDetailProvider =
    StreamProvider.family<TurnRow?, int>((ref, turnId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.turnDao.watchTurn(turnId);
});

/// Enriched turn detail for the TurnDetailScreen.
final turnDetailDataProvider =
    StreamProvider.family<TurnDetailData?, int>((ref, turnId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.turnDao.watchTurnDetail(turnId);
});

final turnSegmentsProvider =
    StreamProvider.family<List<SegmentRow>, int>((ref, turnId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.turnDao.watchSegments(turnId);
});
