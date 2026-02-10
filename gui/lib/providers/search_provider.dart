import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/entity_with_details.dart';
import 'database_provider.dart';

final globalSearchQueryProvider = StateProvider<String>((ref) => '');

final globalSearchResultsProvider =
    FutureProvider<List<EntityWithDetails>>((ref) async {
  final db = ref.watch(databaseProvider);
  final query = ref.watch(globalSearchQueryProvider);
  if (db == null || query.length < 2) return [];
  return db.entityDao.searchEntities(query);
});
