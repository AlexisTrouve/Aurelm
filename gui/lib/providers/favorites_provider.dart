import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/repositories/favorites_repository.dart';
import 'database_provider.dart';

/// Holds the full set of favorited items as string keys "type_id"
/// (e.g. "entity_42", "subject_7", "turn_3").
///
/// Loaded once from DB on construction, then mutated in-memory on each toggle.
class FavoritesNotifier extends StateNotifier<Set<String>> {
  final FavoritesRepository _repo;

  FavoritesNotifier(this._repo) : super(const {}) {
    _load();
  }

  Future<void> _load() async {
    state = await _repo.loadAll();
  }

  /// Check whether an item is currently favorited.
  bool isFavorite(String type, int id) => state.contains('${type}_$id');

  /// Toggle favorite status. Persists to DB and updates in-memory state.
  Future<void> toggle(String type, int id, int? civId) async {
    final key = '${type}_$id';
    if (state.contains(key)) {
      await _repo.remove(type, id);
      state = Set.from(state)..remove(key);
    } else {
      await _repo.add(type, id, civId);
      state = {...state, key};
    }
  }
}

final favoritesProvider =
    StateNotifierProvider<FavoritesNotifier, Set<String>>((ref) {
  // Watch db so notifier reloads when db path changes
  final db = ref.watch(databaseProvider);
  return FavoritesNotifier(FavoritesRepository(db));
});
