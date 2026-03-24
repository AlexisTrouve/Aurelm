import 'package:drift/drift.dart';

import '../database.dart';
import '../tables/civilizations.dart';
import '../tables/turns.dart';
import '../tables/entities.dart';
import '../../models/civ_with_stats.dart';

part 'civilization_dao.g.dart';

@DriftAccessor(tables: [CivCivilizations, TurnTurns, EntityEntities])
class CivilizationDao extends DatabaseAccessor<AurelmDatabase>
    with _$CivilizationDaoMixin {
  CivilizationDao(super.db);

  Stream<List<CivWithStats>> watchAllCivsWithStats() {
    final turnCountExpr = turnTurns.id.count();
    final entityCountExpr = entityEntities.id.count();

    // We need two separate queries since drift doesn't easily do
    // two LEFT JOINs with different count columns in one query.
    // Instead, we watch civs and enrich with counts.
    return (select(civCivilizations)
          ..orderBy([(t) => OrderingTerm.asc(t.name)]))
        .watch()
        .asyncMap((civs) async {
      final result = <CivWithStats>[];
      for (final civ in civs) {
        final turnCount = await (selectOnly(turnTurns)
              ..addColumns([turnCountExpr])
              ..where(turnTurns.civId.equals(civ.id)))
            .map((row) => row.read(turnCountExpr) ?? 0)
            .getSingle();

        final entityCount = await (selectOnly(entityEntities)
              ..addColumns([entityCountExpr])
              ..where(entityEntities.civId.equals(civ.id)))
            .map((row) => row.read(entityCountExpr) ?? 0)
            .getSingle();

        result.add(CivWithStats(
          civ: civ,
          turnCount: turnCount,
          entityCount: entityCount,
        ));
      }
      return result;
    });
  }

  /// Stream of all civs (no stats, lighter).
  Stream<List<CivRow>> watchAllCivs() {
    return (select(civCivilizations)
          ..orderBy([(t) => OrderingTerm.asc(t.name)]))
        .watch();
  }

  /// Create a new civilization, or update Discord bindings if name already exists.
  /// Preserves createdAt on update (only updatedAt + Discord fields change).
  Future<int> createCiv({
    required String name,
    String? playerName,
    String? discordChannelId,
    String? discordGuildName,
    String? discordChannelName,
  }) async {
    final now = DateTime.now().toIso8601String();
    // Check if civ already exists
    final existing = await (select(civCivilizations)
          ..where((t) => t.name.equals(name)))
        .getSingleOrNull();
    if (existing != null) {
      // Update only mutable fields, preserve createdAt
      await (update(civCivilizations)..where((t) => t.id.equals(existing.id)))
          .write(CivCivilizationsCompanion(
        playerName: Value(playerName),
        discordChannelId: Value(discordChannelId),
        discordGuildName: Value(discordGuildName),
        discordChannelName: Value(discordChannelName),
        updatedAt: Value(now),
      ));
      return existing.id;
    }
    // New civ
    return into(civCivilizations).insert(
      CivCivilizationsCompanion.insert(
        name: name,
        playerName: Value(playerName),
        discordChannelId: Value(discordChannelId),
        discordGuildName: Value(discordGuildName),
        discordChannelName: Value(discordChannelName),
        createdAt: now,
        updatedAt: now,
      ),
    );
  }

  /// Update the Discord channel binding for an existing civ.
  /// Stores display names so we never need to show raw IDs.
  Future<void> updateCivChannel(
    int civId, {
    String? channelId,
    String? guildName,
    String? channelName,
  }) {
    final now = DateTime.now().toIso8601String();
    return (update(civCivilizations)..where((t) => t.id.equals(civId))).write(
      CivCivilizationsCompanion(
        discordChannelId: Value(channelId),
        discordGuildName: Value(guildName),
        discordChannelName: Value(channelName),
        updatedAt: Value(now),
      ),
    );
  }

  /// Delete a civilization and all its data (CASCADE + raw messages cleanup).
  Future<void> deleteCiv(int civId) async {
    // Get the channel ID before deleting — needed to clean up raw messages
    final civ = await (select(civCivilizations)
          ..where((t) => t.id.equals(civId)))
        .getSingleOrNull();
    final channelId = civ?.discordChannelId;

    // CASCADE delete (turns, entities, segments, mentions, etc.)
    await (delete(civCivilizations)..where((t) => t.id.equals(civId))).go();

    // Clean up raw messages for this channel (no FK, linked by channel ID)
    if (channelId != null && channelId.isNotEmpty) {
      await customStatement(
        'DELETE FROM turn_raw_messages WHERE discord_channel_id = ?',
        [channelId],
      );
    }
  }

  Stream<CivWithStats?> watchCivWithStats(int civId) {
    final turnCountExpr = turnTurns.id.count();
    final entityCountExpr = entityEntities.id.count();

    return (select(civCivilizations)..where((t) => t.id.equals(civId)))
        .watchSingleOrNull()
        .asyncMap((civ) async {
      if (civ == null) return null;

      final turnCount = await (selectOnly(turnTurns)
            ..addColumns([turnCountExpr])
            ..where(turnTurns.civId.equals(civId)))
          .map((row) => row.read(turnCountExpr) ?? 0)
          .getSingle();

      final entityCount = await (selectOnly(entityEntities)
            ..addColumns([entityCountExpr])
            ..where(entityEntities.civId.equals(civId)))
          .map((row) => row.read(entityCountExpr) ?? 0)
          .getSingle();

      return CivWithStats(
        civ: civ,
        turnCount: turnCount,
        entityCount: entityCount,
      );
    });
  }
}
