import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/daos/entity_dao.dart';
import '../models/entity_with_details.dart';
import '../models/filter_state.dart';
import 'database_provider.dart';

final entityFilterProvider =
    StateNotifierProvider<EntityFilterNotifier, EntityFilterState>((ref) {
  return EntityFilterNotifier();
});

class EntityFilterNotifier extends StateNotifier<EntityFilterState> {
  EntityFilterNotifier() : super(const EntityFilterState());

  void setEntityType(String? type) {
    state = state.copyWith(entityType: () => type);
  }

  void setCivId(int? id) {
    state = state.copyWith(civId: () => id);
  }

  void setSearchQuery(String query) {
    state = state.copyWith(searchQuery: query);
  }

  void reset() {
    state = const EntityFilterState();
  }
}

final entityListProvider = StreamProvider<List<EntityWithDetails>>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  final filters = ref.watch(entityFilterProvider);
  return db.entityDao.watchEntities(filters);
});

final entityDetailProvider =
    StreamProvider.family<EntityWithDetails?, int>((ref, entityId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.entityDao.watchEntityDetail(entityId);
});

final entityMentionsProvider =
    StreamProvider.family<List<MentionWithContext>, int>((ref, entityId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.entityDao.watchMentionsForEntity(entityId);
});

final topEntitiesProvider =
    StreamProvider.family<List<EntityWithDetails>, int>((ref, civId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.entityDao.watchTopEntitiesForCiv(civId);
});

final entityTypeBreakdownProvider =
    StreamProvider.family<Map<String, int>, int>((ref, civId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.entityDao.watchEntityTypeBreakdown(civId);
});
