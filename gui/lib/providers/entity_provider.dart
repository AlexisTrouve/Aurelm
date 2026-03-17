import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/daos/entity_dao.dart';
import '../models/entity_with_details.dart';
import '../models/filter_state.dart';
import 'database_provider.dart';
import 'favorites_provider.dart';

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

  void toggleShowHidden() {
    state = state.copyWith(showHidden: !state.showHidden);
  }

  void setSelectedTag(String? tag) {
    state = state.copyWith(selectedTag: () => tag);
  }

  void setFavoritesOnly(bool value) {
    state = state.copyWith(favoritesOnly: value);
  }

  void reset() {
    state = const EntityFilterState();
  }
}

/// Provider for disabled (archived) entities, optionally filtered by civ
final disabledEntitiesProvider =
    StreamProvider.family<List<EntityWithDetails>, int?>((ref, civId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.entityDao.watchDisabledEntities(civId: civId);
});

final entityListProvider = StreamProvider<List<EntityWithDetails>>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  final filters = ref.watch(entityFilterProvider);
  final favorites = ref.watch(favoritesProvider);

  return db.entityDao.watchEntities(filters).map((list) {
    // Apply favorites filter in-stream — avoids a DB-level join
    if (!filters.favoritesOnly) return list;
    return list.where((e) => favorites.contains('entity_${e.entity.id}')).toList();
  });
});

final entityDetailProvider =
    StreamProvider.family<EntityWithDetails?, int>((ref, entityId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.entityDao.watchEntityDetail(entityId);
});

/// Reactive set of GM-locked fields for an entity.
/// Empty = no fields protected. Used to show lock badges in entity_detail_screen.
final entityGmFieldsProvider =
    StreamProvider.family<Set<String>, int>((ref, entityId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.entityDao.watchGmFields(entityId);
});

final entityMentionsProvider =
    StreamProvider.family<List<MentionWithContext>, int>((ref, entityId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.entityDao.watchMentionsForEntity(entityId);
});

/// Entities mentioned in a specific turn — for TurnDetailScreen fast travel.
final turnEntitiesProvider =
    StreamProvider.family<List<EntityWithDetails>, int>((ref, turnId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.entityDao.watchEntitiesForTurn(turnId);
});

/// All unique semantic tags across active entities, for the entity filter bar.
/// Naming history for a single entity — aliases sorted chronologically with turn info.
final namingHistoryProvider =
    FutureProvider.family<List<AliasHistoryEntry>, int>((ref, entityId) async {
  final db = ref.watch(databaseProvider);
  if (db == null) return [];
  return db.entityDao.getNamingHistory(entityId);
});

final entityTagsProvider = FutureProvider<List<String>>((ref) async {
  final db = ref.watch(databaseProvider);
  if (db == null) return [];
  return db.entityDao.allEntityTags();
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
