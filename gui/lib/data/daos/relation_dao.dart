import 'package:drift/drift.dart';

import '../database.dart';
import '../tables/relations.dart';
import '../tables/entities.dart';
import '../tables/mentions.dart';
import '../../models/graph_data.dart';

part 'relation_dao.g.dart';

@DriftAccessor(tables: [EntityRelations, EntityEntities, EntityMentions])
class RelationDao extends DatabaseAccessor<AurelmDatabase>
    with _$RelationDaoMixin {
  RelationDao(super.db);

  Stream<List<RelationRow>> watchRelationsForEntity(int entityId) {
    return (select(entityRelations)
          ..where((t) =>
              t.sourceEntityId.equals(entityId) |
              t.targetEntityId.equals(entityId))
          ..where((t) => t.isActive.equals(1)))
        .watch();
  }

  Stream<GraphData> watchGraphData({int? civId, int entityLimit = 50}) {
    final mentionCountExpr = entityMentions.id.count();

    // Get top entities by mention count
    var entityQuery = select(entityEntities).join([
      leftOuterJoin(
          entityMentions, entityMentions.entityId.equalsExp(entityEntities.id)),
    ])
      ..addColumns([mentionCountExpr])
      ..groupBy([entityEntities.id])
      ..orderBy([OrderingTerm.desc(mentionCountExpr)])
      ..limit(entityLimit);

    if (civId != null) {
      entityQuery.where(entityEntities.civId.equals(civId));
    }

    return entityQuery.watch().asyncMap((entityRows) async {
      final nodes = <GraphNode>[];
      final nodeIds = <int>{};

      for (final row in entityRows) {
        final entity = row.readTable(entityEntities);
        final count = row.read(mentionCountExpr) ?? 0;
        nodes.add(GraphNode(
          id: entity.id,
          name: entity.canonicalName,
          entityType: entity.entityType,
          mentionCount: count,
          civId: entity.civId,
        ));
        nodeIds.add(entity.id);
      }

      // Get relations between these entities
      final relations = await (select(entityRelations)
            ..where((t) => t.isActive.equals(1)))
          .get();

      final edges = <GraphEdge>[];
      for (final rel in relations) {
        if (nodeIds.contains(rel.sourceEntityId) &&
            nodeIds.contains(rel.targetEntityId)) {
          edges.add(GraphEdge(
            sourceId: rel.sourceEntityId,
            targetId: rel.targetEntityId,
            relationType: rel.relationType,
            description: rel.description,
          ));
        }
      }

      return GraphData(nodes: nodes, edges: edges);
    });
  }
}
