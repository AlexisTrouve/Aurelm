import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/database.dart';
import '../models/civ_with_stats.dart';
import 'database_provider.dart';

final civListProvider = StreamProvider<List<CivWithStats>>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.civilizationDao.watchAllCivsWithStats();
});

final civDetailProvider =
    StreamProvider.family<CivWithStats?, int>((ref, civId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.civilizationDao.watchCivWithStats(civId);
});

/// Les 5 derniers tours d'une civ avec leur detailedSummary — pour l'historique
/// récent affiché en haut de CivDetailScreen.
final civBriefProvider =
    StreamProvider.family<List<TurnRow>, int>((ref, civId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.turnDao
      .watchTimeline(civId: civId)
      .map((turns) => turns
          .where((t) => t.turn.detailedSummary != null &&
              t.turn.detailedSummary!.isNotEmpty)
          .take(5)
          .map((t) => t.turn)
          .toList());
});
