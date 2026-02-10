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
