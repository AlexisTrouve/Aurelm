import 'package:flutter_riverpod/flutter_riverpod.dart';

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
