import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/repositories/civ_alias_repository.dart';
import 'database_provider.dart';

/// Repository instance — null if DB not yet open.
final civAliasRepositoryProvider = Provider<CivAliasRepository?>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return null;
  return CivAliasRepository(db);
});

/// Reactive list of aliases for a given civ.
final civAliasesProvider =
    FutureProvider.family<List<CivAliasEntry>, int>((ref, civId) async {
  final repo = ref.watch(civAliasRepositoryProvider);
  if (repo == null) return [];
  return repo.loadAliasesForCiv(civId);
});

/// Count of unresolved civ names — drives the badge on the dashboard button.
final unresolvedCivCountProvider = FutureProvider<int>((ref) async {
  final repo = ref.watch(civAliasRepositoryProvider);
  if (repo == null) return 0;
  return repo.loadUnresolvedCount();
});
