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

  /// Ego-graph centered on [centerId].
  /// Depth 1 = direct neighbors. Depth 2 = also neighbors-of-neighbors.
  /// Optionally filter by [relationType].
  Stream<GraphData> watchEgoGraph({
    required int centerId,
    int depth = 1,
    String? relationType,
  }) {
    // Re-query whenever relations change
    return watchRelationsForEntity(centerId).asyncMap((_) async {
      final allRelations = await (select(entityRelations)
            ..where((t) => t.isActive.equals(1)))
          .get();

      // Helper: get all neighbor IDs for a given entity
      List<int> neighborsOf(int id) {
        return allRelations
            .where((r) =>
                (r.sourceEntityId == id || r.targetEntityId == id) &&
                (relationType == null || r.relationType == relationType))
            .map((r) => r.sourceEntityId == id ? r.targetEntityId : r.sourceEntityId)
            .where((nId) => nId != id)
            .toList();
      }

      // Collect all node IDs to include
      final depth1Ids = neighborsOf(centerId).toSet();
      final depth2Ids = <int>{};
      if (depth >= 2) {
        for (final d1Id in depth1Ids) {
          depth2Ids.addAll(neighborsOf(d1Id).where((id) => id != centerId));
        }
        depth2Ids.removeAll(depth1Ids);
      }

      final allIds = {centerId, ...depth1Ids, ...depth2Ids};

      // Load entity data for all nodes
      final entities = await (select(entityEntities)
            ..where((t) => t.id.isIn(allIds))
            ..where((t) => t.isActive.equals(1)))
          .get();

      // Build mention counts
      final mentionCounts = <int, int>{};
      for (final id in allIds) {
        final count = await (select(entityMentions)
              ..where((t) => t.entityId.equals(id)))
            .get()
            .then((rows) => rows.length);
        mentionCounts[id] = count;
      }

      final entityMap = {for (final e in entities) e.id: e};
      final nodes = allIds
          .where((id) => entityMap.containsKey(id))
          .map((id) {
            final e = entityMap[id]!;
            return GraphNode(
              id: e.id,
              name: e.canonicalName,
              entityType: e.entityType,
              mentionCount: mentionCounts[id] ?? 0,
              civId: e.civId,
              // depth from center (0=center, 1=direct, 2=extended)
              depth: id == centerId ? 0 : depth1Ids.contains(id) ? 1 : 2,
            );
          })
          .toList();

      // Only edges between visible nodes
      final visibleIds = {for (final n in nodes) n.id};
      final edges = allRelations
          .where((r) =>
              visibleIds.contains(r.sourceEntityId) &&
              visibleIds.contains(r.targetEntityId) &&
              (relationType == null || r.relationType == relationType))
          .map((r) => GraphEdge(
                sourceId: r.sourceEntityId,
                targetId: r.targetEntityId,
                relationType: r.relationType,
                description: r.description,
              ))
          .toList();

      return GraphData(nodes: nodes, edges: edges, centerId: centerId);
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
