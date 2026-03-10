import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/graph_data.dart';
import 'database_provider.dart';

/// Currently selected entity (center of the ego graph). null = nothing selected.
final graphSelectedEntityProvider = StateProvider<int?>((ref) => null);

/// Optional relation type filter — null = show all relation types.
final graphRelationTypeFilterProvider = StateProvider<String?>((ref) => null);

/// Ego-graph data for the selected entity at depth 2.
/// Depth-2 visibility is managed per-node via expand/collapse in the UI.
final egoGraphDataProvider = StreamProvider<GraphData>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();

  final centerId = ref.watch(graphSelectedEntityProvider);
  if (centerId == null) return Stream.value(GraphData.empty);

  final relType = ref.watch(graphRelationTypeFilterProvider);

  return db.relationDao.watchEgoGraph(
    centerId: centerId,
    depth: 2, // always fetch depth 2; visibility controlled by expand/collapse
    relationType: relType,
  );
});
