import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/repositories/agent_memory_repository.dart';
import 'database_provider.dart';

/// Repository, rebuilt when the DB path changes (null when no DB configured).
final agentMemoryRepositoryProvider = Provider<AgentMemoryRepository?>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return null;
  return AgentMemoryRepository(db);
});

/// All agent memories (active + inactive) for the review screen. Fetched, not a
/// reactive stream — raw-SQL tables aren't watched by Drift, so callers must
/// `ref.invalidate(agentMemoryProvider)` after a write to refresh.
final agentMemoryProvider = FutureProvider<List<AgentMemory>>((ref) async {
  final repo = ref.watch(agentMemoryRepositoryProvider);
  if (repo == null) return [];
  return repo.loadAll();
});
