import 'package:drift/drift.dart';

import '../database.dart';
import '../tables/civilizations.dart';
import '../tables/turns.dart';
import '../tables/entities.dart';
import '../tables/mentions.dart';
import '../../models/turn_with_entities.dart';

part 'turn_dao.g.dart';

@DriftAccessor(
    tables: [TurnTurns, TurnSegments, CivCivilizations, EntityMentions, EntityEntities])
class TurnDao extends DatabaseAccessor<AurelmDatabase> with _$TurnDaoMixin {
  TurnDao(super.db);

  Stream<List<TurnWithEntities>> watchTimeline({int? civId, int limit = 100}) {
    var query = select(turnTurns).join([
      innerJoin(
          civCivilizations, civCivilizations.id.equalsExp(turnTurns.civId)),
    ]);

    if (civId != null) {
      query.where(turnTurns.civId.equals(civId));
    }

    query
      ..orderBy([OrderingTerm.desc(turnTurns.turnNumber)])
      ..limit(limit);

    return query.watch().asyncMap((rows) async {
      final results = <TurnWithEntities>[];
      for (final row in rows) {
        final turn = row.readTable(turnTurns);
        final civ = row.readTable(civCivilizations);

        final mentionCount = await _countMentionsForTurn(turn.id);
        final segTypes = await _segmentTypesForTurn(turn.id);

        results.add(TurnWithEntities(
          turn: turn,
          civName: civ.name,
          entityCount: mentionCount,
          segmentTypes: segTypes,
        ));
      }
      return results;
    });
  }

  Future<int> _countMentionsForTurn(int turnId) async {
    final countExpr = entityMentions.id.count();
    final row = await (selectOnly(entityMentions)
          ..addColumns([countExpr])
          ..where(entityMentions.turnId.equals(turnId)))
        .getSingle();
    return row.read(countExpr) ?? 0;
  }

  Future<List<String>> _segmentTypesForTurn(int turnId) async {
    final segs = await (select(turnSegments)
          ..where((t) => t.turnId.equals(turnId))
          ..orderBy([(t) => OrderingTerm.asc(t.segmentOrder)]))
        .get();
    return segs.map((s) => s.segmentType).toSet().toList();
  }

  Stream<TurnRow?> watchTurn(int turnId) {
    return (select(turnTurns)..where((t) => t.id.equals(turnId)))
        .watchSingleOrNull();
  }

  Stream<List<SegmentRow>> watchSegments(int turnId) {
    return (select(turnSegments)
          ..where((t) => t.turnId.equals(turnId))
          ..orderBy([(t) => OrderingTerm.asc(t.segmentOrder)]))
        .watch();
  }

  Future<TurnRow?> getTurnByCivAndNumber(int civId, int turnNumber) {
    return (select(turnTurns)
          ..where(
              (t) => t.civId.equals(civId) & t.turnNumber.equals(turnNumber)))
        .getSingleOrNull();
  }
}
