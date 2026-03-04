import 'package:drift/drift.dart';

import '../database.dart';
import '../tables/relations.dart';
import '../tables/entities.dart';
import '../tables/mentions.dart';
import '../../models/graph_data.dart';

part 'relation_dao.g.dart';

/// Relation enriched with canonical names for both endpoints — avoids N+1 lookups.
class RelationWithNames {
  final RelationRow relation;
  final String sourceName;
  final String targetName;

  /// Name of the "other" entity (opposite side from the queried entity)
  final String relatedName;
  final int relatedEntityId;

  /// true = this entity is the source (→ outgoing); false = this entity is target (← incoming)
  final bool isOutgoing;

  const RelationWithNames({
    required this.relation,
    required this.sourceName,
    required this.targetName,
    required this.relatedName,
    required this.relatedEntityId,
    required this.isOutgoing,
  });
}

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

  /// Relations enriched with entity names — avoids N+1 by using two table aliases.
  Stream<List<RelationWithNames>> watchRelationsWithNamesForEntity(
      int entityId) {
    // Drift alias: join entity_entities twice (once for source, once for target)
    final sourceAlias = alias(entityEntities, 'src');
    final targetAlias = alias(entityEntities, 'tgt');

    return (select(entityRelations).join([
      leftOuterJoin(
          sourceAlias, sourceAlias.id.equalsExp(entityRelations.sourceEntityId)),
      leftOuterJoin(
          targetAlias, targetAlias.id.equalsExp(entityRelations.targetEntityId)),
    ])
          ..where((entityRelations.sourceEntityId.equals(entityId) |
                  entityRelations.targetEntityId.equals(entityId)) &
              entityRelations.isActive.equals(1)))
        .watch()
        .map((rows) {
      return rows.map((row) {
        final relation = row.readTable(entityRelations);
        final sourceName =
            row.readTableOrNull(sourceAlias)?.canonicalName ?? '…';
        final targetName =
            row.readTableOrNull(targetAlias)?.canonicalName ?? '…';
        // "Related" entity = the other side of the relation
        final isOutgoing = relation.sourceEntityId == entityId;
        return RelationWithNames(
          relation: relation,
          sourceName: sourceName,
          targetName: targetName,
          relatedName: isOutgoing ? targetName : sourceName,
          relatedEntityId:
              isOutgoing ? relation.targetEntityId : relation.sourceEntityId,
          isOutgoing: isOutgoing,
        );
      }).toList();
    });
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
