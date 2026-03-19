import 'dart:convert';

import 'package:drift/drift.dart';

import '../database.dart';
import '../tables/entities.dart';
import '../tables/mentions.dart';
import '../tables/civilizations.dart';
import '../tables/turns.dart';
import '../../models/entity_with_details.dart';
import '../../models/filter_state.dart';

part 'entity_dao.g.dart';

/// Parse a gm_fields JSON column value into a Set of field names.
Set<String> _parseGmFieldsJson(String? raw) {
  if (raw == null || raw.isEmpty) return {};
  try {
    return Set<String>.from(jsonDecode(raw) as List);
  } catch (_) {
    return {};
  }
}

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

    // Always exclude disabled entities from the main view
    Expression<bool> whereExpr = entityEntities.disabled.equals(false);

    // Exclude hidden unless the filter says to show them
    if (!filters.showHidden) {
      whereExpr = whereExpr & entityEntities.hidden.equals(false);
    }

    if (filters.entityType != null) {
      whereExpr = whereExpr & entityEntities.entityType.equals(filters.entityType!);
    }
    if (filters.civId != null) {
      whereExpr = whereExpr & entityEntities.civId.equals(filters.civId!);
    }
    if (filters.searchQuery.isNotEmpty) {
      whereExpr = whereExpr &
          entityEntities.canonicalName.like('%${filters.searchQuery}%');
    }
    // Tag filter — JSON LIKE match on the tags column
    if (filters.selectedTag != null) {
      whereExpr = whereExpr &
          entityEntities.tags.like('%"${filters.selectedTag!}"%');
    }

    query.where(whereExpr);

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

  /// All disabled entities (for the disabled/archived view + reactivation)
  Stream<List<EntityWithDetails>> watchDisabledEntities({int? civId}) {
    final mentionCountExpr = entityMentions.id.count();

    var query = select(entityEntities).join([
      leftOuterJoin(
          entityMentions, entityMentions.entityId.equalsExp(entityEntities.id)),
    ]);

    Expression<bool> whereExpr = entityEntities.disabled.equals(true);
    if (civId != null) {
      whereExpr = whereExpr & entityEntities.civId.equals(civId);
    }
    query.where(whereExpr);

    query
      ..addColumns([mentionCountExpr])
      ..groupBy([entityEntities.id])
      ..orderBy([OrderingTerm.desc(entityEntities.disabledAt)]);

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
    // Detail view shows any entity (including hidden) — used for cross-links
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

  /// All entities mentioned in a given turn, ordered by mention count desc.
  /// Used for the "Entités du tour" section in TurnDetailScreen.
  Stream<List<EntityWithDetails>> watchEntitiesForTurn(int turnId) {
    final mentionCountExpr = entityMentions.id.count();

    final query = select(entityEntities).join([
      innerJoin(
          entityMentions, entityMentions.entityId.equalsExp(entityEntities.id)),
    ])
      ..where(entityMentions.turnId.equals(turnId) &
          entityEntities.disabled.equals(false))
      ..addColumns([mentionCountExpr])
      ..groupBy([entityEntities.id])
      ..orderBy([OrderingTerm.desc(mentionCountExpr)]);

    return query.watch().map((rows) => rows.map((row) {
          final entity = row.readTable(entityEntities);
          final count = row.read(mentionCountExpr) ?? 0;
          return EntityWithDetails(entity: entity, aliases: [], mentionCount: count);
        }).toList());
  }

  Future<List<EntityWithDetails>> searchEntities(String query) async {
    if (query.isEmpty) return [];

    final mentionCountExpr = entityMentions.id.count();
    final results = await (select(entityEntities).join([
      leftOuterJoin(
          entityMentions, entityMentions.entityId.equalsExp(entityEntities.id)),
    ])
          ..where(entityEntities.canonicalName.like('%$query%') &
              entityEntities.disabled.equals(false))
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

  /// Top entities for a civ by mention count (dashboard cards)
  Stream<List<EntityWithDetails>> watchTopEntitiesForCiv(int civId,
      {int limit = 10}) {
    final mentionCountExpr = entityMentions.id.count();

    final query = select(entityEntities).join([
      leftOuterJoin(
          entityMentions, entityMentions.entityId.equalsExp(entityEntities.id)),
    ])
      ..where(entityEntities.civId.equals(civId) &
          entityEntities.disabled.equals(false) &
          entityEntities.hidden.equals(false))
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

  /// Entity count by type for a civ (bar chart) — excludes disabled + hidden
  Stream<Map<String, int>> watchEntityTypeBreakdown(int civId) {
    final countExpr = entityEntities.id.count();
    final query = selectOnly(entityEntities)
      ..addColumns([entityEntities.entityType, countExpr])
      ..where(entityEntities.civId.equals(civId) &
          entityEntities.disabled.equals(false) &
          entityEntities.hidden.equals(false))
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

  // ---------------------------------------------------------------------------
  // MJ actions: hide / disable / reactivate
  // ---------------------------------------------------------------------------

  // ---------------------------------------------------------------------------
  // Alias queries (for edit mode — need the alias DB id to delete)
  // ---------------------------------------------------------------------------

  /// All aliases for an entity, ordered by id (insertion order proxy).
  Stream<List<AliasRow>> watchAliasesForEntity(int entityId) {
    return (select(entityAliases)
          ..where((t) => t.entityId.equals(entityId))
          ..orderBy([(t) => OrderingTerm.asc(t.id)]))
        .watch();
  }

  // ---------------------------------------------------------------------------
  // GM CRUD: create + edit entities manually
  // ---------------------------------------------------------------------------

  /// Create a new entity manually (GM action). Returns the new entity's id.
  Future<int> createEntity({
    required String canonicalName,
    required String entityType,
    int? civId,
    String? description,
  }) async {
    final now = DateTime.now().toIso8601String();
    return into(entityEntities).insert(EntityEntitiesCompanion(
      canonicalName: Value(canonicalName),
      entityType: Value(entityType),
      civId: Value(civId),
      description: Value(description),
      createdAt: Value(now),
      updatedAt: Value(now),
    ));
  }

  /// Update name, type, civ, and description of an existing entity.
  Future<void> updateEntity({
    required int entityId,
    required String canonicalName,
    required String entityType,
    int? civId,
    String? description,
  }) async {
    final now = DateTime.now().toIso8601String();
    await (update(entityEntities)..where((t) => t.id.equals(entityId)))
        .write(EntityEntitiesCompanion(
      canonicalName: Value(canonicalName),
      entityType: Value(entityType),
      civId: Value(civId),
      description: Value(description),
      updatedAt: Value(now),
    ));
  }

  /// Add a new alias to an entity (GM action).
  Future<void> addAlias(int entityId, String alias) async {
    await into(entityAliases).insert(EntityAliasesCompanion(
      entityId: Value(entityId),
      alias: Value(alias),
    ));
  }

  /// Remove an alias by its DB id (GM action).
  Future<void> removeAlias(int aliasId) async {
    await (delete(entityAliases)..where((t) => t.id.equals(aliasId))).go();
  }

  /// Update the tags JSON array for an entity (GM action).
  Future<void> updateEntityTags(int entityId, List<String> tags) async {
    final encoded = jsonEncode(tags);
    await (update(entityEntities)..where((t) => t.id.equals(entityId)))
        .write(EntityEntitiesCompanion(
      tags: Value(encoded.isEmpty || tags.isEmpty ? null : encoded),
      updatedAt: Value(DateTime.now().toIso8601String()),
    ));
  }

  /// Toggle hidden flag. Hidden entities stay in DB and cross-links work,
  /// but they are filtered out of the main list unless showHidden is true.
  Future<void> setEntityHidden(int entityId, {required bool hidden}) async {
    await (update(entityEntities)..where((t) => t.id.equals(entityId)))
        .write(EntityEntitiesCompanion(
      hidden: Value(hidden),
    ));
  }

  /// Disable an entity (requires confirmation in the UI).
  /// Disabled entities are excluded from all queries and links are non-clickable.
  Future<void> setEntityDisabled(int entityId, {required bool disabled}) async {
    final now = disabled ? DateTime.now().toIso8601String() : null;
    await (update(entityEntities)..where((t) => t.id.equals(entityId)))
        .write(EntityEntitiesCompanion(
      disabled: Value(disabled),
      disabledAt: Value(now),
      // Re-enabling also un-hides the entity
      hidden: disabled ? const Value.absent() : const Value(false),
    ));
  }

  /// Returns the naming history for an entity — all aliases with their first
  /// appearance turn, sorted chronologically (nulls last).
  /// Used to display the naming lineage: "Nés sans ciel (T3) → Sans-Ciel (T7)".
  Future<List<AliasHistoryEntry>> getNamingHistory(int entityId) async {
    // Canonical name + first seen turn for the primary entity
    final entity = await (select(entityEntities)
          ..where((t) => t.id.equals(entityId)))
        .getSingleOrNull();
    if (entity == null) return [];

    // Fetch aliases with their first_seen_turn_id and the turn number
    final rows = await customSelect(
      '''
      SELECT ea.alias, ea.first_seen_turn_id, t.turn_number
      FROM entity_aliases ea
      LEFT JOIN turn_turns t ON t.id = ea.first_seen_turn_id
      WHERE ea.entity_id = ?
      ORDER BY t.turn_number ASC NULLS LAST
      ''',
      variables: [Variable.withInt(entityId)],
      readsFrom: {entityAliases, turnTurns},
    ).get();

    // The canonical name entry (the entity itself)
    final List<AliasHistoryEntry> history = [
      AliasHistoryEntry(
        name: entity.canonicalName,
        turnId: entity.firstSeenTurn,
        turnNumber: null, // resolved separately if needed
        isCurrent: true,
      ),
    ];

    // Add all aliases sorted by turn number
    for (final row in rows) {
      history.add(AliasHistoryEntry(
        name: row.read<String>('alias'),
        turnId: row.read<int?>('first_seen_turn_id'),
        turnNumber: row.read<int?>('turn_number'),
        isCurrent: false,
      ));
    }

    // Sort: entries with turn numbers first (ascending), then null-turn entries
    history.sort((a, b) {
      final ta = a.turnNumber;
      final tb = b.turnNumber;
      if (ta == null && tb == null) return 0;
      if (ta == null) return 1;
      if (tb == null) return -1;
      return ta.compareTo(tb);
    });

    return history;
  }

  // ---------------------------------------------------------------------------
  // GM field locks — per-field protection from pipeline overwrites
  // ---------------------------------------------------------------------------

  /// Returns the set of GM-locked fields for an entity (e.g. {"description", "tags"}).
  /// Uses raw SQL since gm_fields is not in the Drift-generated EntityRow (no codegen).
  Future<Set<String>> getGmFields(int entityId) async {
    final rows = await customSelect(
      'SELECT gm_fields FROM entity_entities WHERE id = ?',
      variables: [Variable.withInt(entityId)],
      readsFrom: {entityEntities},
    ).get();
    if (rows.isEmpty) return {};
    final raw = rows.first.read<String?>('gm_fields');
    return _parseGmFieldsJson(raw);
  }

  /// Reactive stream of GM-locked fields — emits on any change to entityEntities.
  Stream<Set<String>> watchGmFields(int entityId) {
    return customSelect(
      'SELECT gm_fields FROM entity_entities WHERE id = ?',
      variables: [Variable.withInt(entityId)],
      readsFrom: {entityEntities},
    ).watch().map((rows) {
      if (rows.isEmpty) return <String>{};
      final raw = rows.first.read<String?>('gm_fields');
      return _parseGmFieldsJson(raw);
    });
  }

  /// Persist the GM-locked field set. Pass empty set to unlock all fields.
  Future<void> updateGmFields(int entityId, Set<String> fields) async {
    final encoded = fields.isEmpty ? null : jsonEncode(fields.toList()..sort());
    // customUpdate (not customStatement) so Drift notifies table watchers → stream rebuilds.
    await customUpdate(
      'UPDATE entity_entities SET gm_fields = ? WHERE id = ?',
      variables: [
        encoded == null ? Variable<String>(null) : Variable.withString(encoded),
        Variable.withInt(entityId),
      ],
      updates: {entityEntities},
    );
  }

  /// Returns all unique semantic tags across active entities, sorted by frequency.
  Future<List<String>> allEntityTags() async {
    final rows = await (selectOnly(entityEntities)
          ..addColumns([entityEntities.tags])
          ..where(entityEntities.tags.isNotNull() &
              entityEntities.disabled.equals(false)))
        .get();

    final freq = <String, int>{};
    for (final row in rows) {
      final raw = row.read(entityEntities.tags);
      if (raw == null) continue;
      for (final tag in (jsonDecode(raw) as List).cast<String>()) {
        freq[tag] = (freq[tag] ?? 0) + 1;
      }
    }
    final sorted = freq.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return sorted.map((e) => e.key).toList();
  }
}

/// One entry in an entity's naming history.
/// Represents either the canonical name or an alias, with optional turn info.
class AliasHistoryEntry {
  final String name;
  final int? turnId;      // DB id of the turn where this name first appeared
  final int? turnNumber;  // Human-readable turn number (e.g. 3 for "Tour 3")
  final bool isCurrent;   // True for the canonical (current) name

  const AliasHistoryEntry({
    required this.name,
    required this.turnId,
    required this.turnNumber,
    required this.isCurrent,
  });
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
