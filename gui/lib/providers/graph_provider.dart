import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/graph_data.dart';
import 'database_provider.dart';

/// Currently selected entity (center of the ego graph). null = nothing selected.
final graphSelectedEntityProvider = StateProvider<int?>((ref) => null);

/// Depth of the ego graph: 1 = direct neighbors only, 2 = neighbors-of-neighbors.
final graphDepthProvider = StateProvider<int>((ref) => 1);

/// Optional relation type filter — null = show all relation types.
final graphRelationTypeFilterProvider = StateProvider<String?>((ref) => null);

/// Ego-graph data for the selected entity at the configured depth.
/// Returns empty GraphData when nothing is selected.
final egoGraphDataProvider = StreamProvider<GraphData>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();

  final centerId = ref.watch(graphSelectedEntityProvider);
  if (centerId == null) return Stream.value(GraphData.empty);

  final depth = ref.watch(graphDepthProvider);
  final relType = ref.watch(graphRelationTypeFilterProvider);

  return db.relationDao.watchEgoGraph(
    centerId: centerId,
    depth: depth,
    relationType: relType,
  );
});
