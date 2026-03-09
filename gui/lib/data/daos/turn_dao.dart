import 'dart:convert';

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
    String? selectedTag,
    int limit = 100,
  }) {
    var query = select(turnTurns).join([
      innerJoin(
          civCivilizations, civCivilizations.id.equalsExp(turnTurns.civId)),
    ]);

    if (civId != null) {
      query.where(turnTurns.civId.equals(civId));
    }
    if (turnType != null) {
      query.where(turnTurns.turnType.equals(turnType));
    }
    // Tag filter: thematic_tags is a JSON array string — LIKE match on the tag value
    if (selectedTag != null) {
      query.where(turnTurns.thematicTags.like('%"$selectedTag"%'));
    }

    query
      ..orderBy([OrderingTerm.desc(turnTurns.turnNumber)])
      ..limit(limit);

    return query.watch().asyncMap((rows) async {
      final results = <TurnWithEntities>[];
      for (final row in rows) {
        final turn = row.readTable(turnTurns);
        final civ = row.readTable(civCivilizations);

        // Fetch all turn metadata in parallel for performance
        final gmCount = _countMentionsBySource(turn.id, 'gm');
        final pjCount = _countMentionsBySource(turn.id, 'pj');
        final segTypes = _segmentTypesForTurn(turn.id);
        final hasPj = _hasPjSegments(turn.id);
        final resolved = await Future.wait([gmCount, pjCount, segTypes, hasPj]);

        final gm = resolved[0] as int;
        final pj = resolved[1] as int;
        final segs = resolved[2] as List<String>;
        final pjContent = resolved[3] as bool;

        results.add(TurnWithEntities(
          turn: turn,
          civName: civ.name,
          entityCount: gm + pj,
          gmEntityCount: gm,
          pjEntityCount: pj,
          segmentTypes: segs,
          hasPjContent: pjContent,
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

  /// Counts mentions by source ('gm' or 'pj') for a given turn.
  Future<int> _countMentionsBySource(int turnId, String source) async {
    final countExpr = entityMentions.id.count();
    final row = await (selectOnly(entityMentions)
          ..addColumns([countExpr])
          ..where(entityMentions.turnId.equals(turnId) &
              entityMentions.source.equals(source)))
        .getSingle();
    return row.read(countExpr) ?? 0;
  }

  /// Returns true if the turn has at least one segment with source='pj'.
  Future<bool> _hasPjSegments(int turnId) async {
    final result = await (select(turnSegments)
          ..where((s) => s.turnId.equals(turnId) & s.source.equals('pj'))
          ..limit(1))
        .get();
    return result.isNotEmpty;
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

  /// Returns all unique thematic tags across all turns, sorted by frequency desc.
  Future<List<String>> allThematicTags() async {
    final rows = await (selectOnly(turnTurns)
          ..addColumns([turnTurns.thematicTags])
          ..where(turnTurns.thematicTags.isNotNull()))
        .get();

    final freq = <String, int>{};
    for (final row in rows) {
      final raw = row.read(turnTurns.thematicTags);
      if (raw == null) continue;
      for (final tag in (jsonDecode(raw) as List).cast<String>()) {
        freq[tag] = (freq[tag] ?? 0) + 1;
      }
    }
    // Sort by frequency descending, return tag names
    final sorted = freq.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return sorted.map((e) => e.key).toList();
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
