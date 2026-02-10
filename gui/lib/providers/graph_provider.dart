import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/app_constants.dart';
import '../models/graph_data.dart';
import 'database_provider.dart';

final graphCivFilterProvider = StateProvider<int?>((ref) => null);

final graphShowAllProvider = StateProvider<bool>((ref) => false);

final graphDataProvider = StreamProvider<GraphData>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  final civId = ref.watch(graphCivFilterProvider);
  final showAll = ref.watch(graphShowAllProvider);
  final limit = showAll ? 999 : AppConstants.graphDefaultEntityLimit;
  return db.relationDao.watchGraphData(civId: civId, entityLimit: limit);
});
