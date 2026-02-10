import 'package:drift/drift.dart';

import '../database.dart';
import '../tables/entities.dart';
import '../tables/mentions.dart';
import '../tables/civilizations.dart';
import '../tables/turns.dart';
import '../../models/entity_with_details.dart';
import '../../models/filter_state.dart';

part 'entity_dao.g.dart';

@DriftAccessor(
    tables: [EntityEntities, EntityAliases, EntityMentions, CivCivilizations, TurnTurns])
class EntityDao extends DatabaseAccessor<AurelmDatabase>
    with _$EntityDaoMixin {
  EntityDao(super.db);

  Stream<List<EntityWithDetails>> watchEntities(EntityFilterState filters) {
    final mentionCountExpr = entityMentions.id.count();

    var query = select(entityEntities).join([
      leftOuterJoin(
          entityMentions, entityMentions.entityId.equalsExp(entityEntities.id)),
    ]);

    Expression<bool>? whereExpr;

    if (filters.entityType != null) {
      whereExpr = entityEntities.entityType.equals(filters.entityType!);
    }
    if (filters.civId != null) {
      final civExpr = entityEntities.civId.equals(filters.civId!);
      whereExpr = whereExpr == null ? civExpr : whereExpr & civExpr;
    }
    if (filters.searchQuery.isNotEmpty) {
      final searchExpr =
          entityEntities.canonicalName.like('%${filters.searchQuery}%');
      whereExpr = whereExpr == null ? searchExpr : whereExpr & searchExpr;
    }

    if (whereExpr != null) {
      query.where(whereExpr);
    }

    query
      ..addColumns([mentionCountExpr])
      ..groupBy([entityEntities.id])
      ..orderBy([OrderingTerm.desc(mentionCountExpr)]);

    return query.watch().map((rows) {
      return rows.map((row) {
        final entity = row.readTable(entityEntities);
        final count = row.read(mentionCountExpr) ?? 0;
        return EntityWithDetails(
          entity: entity,
          aliases: [],
          mentionCount: count,
        );
      }).toList();
    });
  }

  Stream<EntityWithDetails?> watchEntityDetail(int entityId) {
    return (select(entityEntities)..where((t) => t.id.equals(entityId)))
        .watchSingleOrNull()
        .asyncMap((entity) async {
      if (entity == null) return null;

      final aliases = await (select(entityAliases)
            ..where((t) => t.entityId.equals(entityId)))
          .get();

      final countExpr = entityMentions.id.count();
      final countRow = await (selectOnly(entityMentions)
            ..addColumns([countExpr])
            ..where(entityMentions.entityId.equals(entityId)))
          .getSingle();
      final mentionCount = countRow.read(countExpr) ?? 0;

      return EntityWithDetails(
        entity: entity,
        aliases: aliases.map((a) => a.alias).toList(),
        mentionCount: mentionCount,
      );
    });
  }

  Stream<List<MentionWithContext>> watchMentionsForEntity(int entityId,
      {int limit = 20}) {
    final query = select(entityMentions).join([
      innerJoin(turnTurns, turnTurns.id.equalsExp(entityMentions.turnId)),
      innerJoin(
          civCivilizations, civCivilizations.id.equalsExp(turnTurns.civId)),
    ])
      ..where(entityMentions.entityId.equals(entityId))
      ..orderBy([OrderingTerm.desc(turnTurns.turnNumber)])
      ..limit(limit);

    return query.watch().map((rows) {
      return rows.map((row) {
        final mention = row.readTable(entityMentions);
        final turn = row.readTable(turnTurns);
        final civ = row.readTable(civCivilizations);
        return MentionWithContext(
          mention: mention,
          turnNumber: turn.turnNumber,
          turnTitle: turn.title,
          civName: civ.name,
        );
      }).toList();
    });
  }

  Future<List<EntityWithDetails>> searchEntities(String query) async {
    if (query.isEmpty) return [];

    final mentionCountExpr = entityMentions.id.count();
    final results = await (select(entityEntities).join([
      leftOuterJoin(
          entityMentions, entityMentions.entityId.equalsExp(entityEntities.id)),
    ])
          ..where(entityEntities.canonicalName.like('%$query%'))
          ..addColumns([mentionCountExpr])
          ..groupBy([entityEntities.id])
          ..orderBy([OrderingTerm.desc(mentionCountExpr)])
          ..limit(20))
        .get();

    return results.map((row) {
      final entity = row.readTable(entityEntities);
      final count = row.read(mentionCountExpr) ?? 0;
      return EntityWithDetails(
        entity: entity,
        aliases: [],
        mentionCount: count,
      );
    }).toList();
  }

  /// Top entities for a civ by mention count
  Stream<List<EntityWithDetails>> watchTopEntitiesForCiv(int civId,
      {int limit = 10}) {
    final mentionCountExpr = entityMentions.id.count();

    final query = select(entityEntities).join([
      leftOuterJoin(
          entityMentions, entityMentions.entityId.equalsExp(entityEntities.id)),
    ])
      ..where(entityEntities.civId.equals(civId))
      ..addColumns([mentionCountExpr])
      ..groupBy([entityEntities.id])
      ..orderBy([OrderingTerm.desc(mentionCountExpr)])
      ..limit(limit);

    return query.watch().map((rows) {
      return rows.map((row) {
        final entity = row.readTable(entityEntities);
        final count = row.read(mentionCountExpr) ?? 0;
        return EntityWithDetails(
          entity: entity,
          aliases: [],
          mentionCount: count,
        );
      }).toList();
    });
  }

  /// Entity count by type for a civ (for pie/bar chart)
  Stream<Map<String, int>> watchEntityTypeBreakdown(int civId) {
    final countExpr = entityEntities.id.count();
    final query = selectOnly(entityEntities)
      ..addColumns([entityEntities.entityType, countExpr])
      ..where(entityEntities.civId.equals(civId))
      ..groupBy([entityEntities.entityType]);

    return query.watch().map((rows) {
      final map = <String, int>{};
      for (final row in rows) {
        final type = row.read(entityEntities.entityType);
        final count = row.read(countExpr);
        if (type != null && count != null) {
          map[type] = count;
        }
      }
      return map;
    });
  }
}

class MentionWithContext {
  final MentionRow mention;
  final int turnNumber;
  final String? turnTitle;
  final String civName;

  const MentionWithContext({
    required this.mention,
    required this.turnNumber,
    required this.turnTitle,
    required this.civName,
  });
}
