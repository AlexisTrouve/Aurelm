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

  Stream<List<TurnWithEntities>> watchTimeline({
    int? civId,
    String? turnType,
    int limit = 100,
  }) {
    var query = select(turnTurns).join([
      innerJoin(
          civCivilizations, civCivilizations.id.equalsExp(turnTurns.civId)),
    ]);

    if (civId != null) {
      query.where(turnTurns.civId.equals(civId));
    }
    // Apply turnType filter (was previously ignored — fix)
    if (turnType != null) {
      query.where(turnTurns.turnType.equals(turnType));
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

  /// Enriched turn for detail page: turn + civ name + all segments.
  Stream<TurnDetailData?> watchTurnDetail(int turnId) {
    return (select(turnTurns).join([
      innerJoin(civCivilizations,
          civCivilizations.id.equalsExp(turnTurns.civId)),
    ])
          ..where(turnTurns.id.equals(turnId)))
        .watchSingleOrNull()
        .asyncMap((row) async {
      if (row == null) return null;

      final turn = row.readTable(turnTurns);
      final civ = row.readTable(civCivilizations);

      final segments = await (select(turnSegments)
            ..where((s) => s.turnId.equals(turnId))
            ..orderBy([(s) => OrderingTerm.asc(s.segmentOrder)]))
          .get();

      final mentionCount = await _countMentionsForTurn(turnId);

      return TurnDetailData(
        turn: turn,
        civName: civ.name,
        segments: segments,
        entityCount: mentionCount,
      );
    });
  }
}

/// Data holder for turn detail page.
class TurnDetailData {
  final TurnRow turn;
  final String civName;
  final List<SegmentRow> segments;
  final int entityCount;

  const TurnDetailData({
    required this.turn,
    required this.civName,
    required this.segments,
    required this.entityCount,
  });
}
