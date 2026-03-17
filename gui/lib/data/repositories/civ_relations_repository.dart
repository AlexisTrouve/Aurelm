import 'dart:convert';

import 'package:drift/drift.dart';

import '../database.dart';

/// A single unilateral inter-civ relationship: how [sourceCivId] perceives [targetCivId].
/// Populated by the pipeline's civ_relation_profiler (LLM-based).
class CivRelation {
  final int id;
  final int sourceCivId;
  final int targetCivId;
  final String sourceCivName;
  final String targetCivName;

  /// Opinion value — one of: allied | friendly | neutral | suspicious | hostile | unknown
  final String opinion;

  /// LLM-generated narrative description of the relationship.
  final String? description;

  /// List of treaty/agreement names detected by the LLM.
  final List<String> treaties;

  /// Turn number of the most recent mention that influenced this profile.
  final int? lastTurnNumber;

  /// Number of raw civ_mentions for this directional pair.
  final int mentionCount;

  const CivRelation({
    required this.id,
    required this.sourceCivId,
    required this.targetCivId,
    required this.sourceCivName,
    required this.targetCivName,
    required this.opinion,
    this.description,
    this.treaties = const [],
    this.lastTurnNumber,
    this.mentionCount = 0,
  });
}

/// Repository for inter-civ relation data — raw SQL, no Drift codegen needed.
class CivRelationsRepository {
  final AurelmDatabase _db;

  const CivRelationsRepository(this._db);

  /// Reactive stream of all [CivRelation] rows involving [civId]
  /// (either as source or target).
  Stream<List<CivRelation>> watchRelations(int civId) {
    return _db.customSelect(
      '''SELECT r.id, r.source_civ_id, r.target_civ_id,
                r.opinion, r.description, r.treaties,
                ca.name AS source_name, cb.name AS target_name,
                t.turn_number AS last_turn,
                (SELECT COUNT(*) FROM civ_mentions m
                 WHERE m.source_civ_id = r.source_civ_id
                   AND m.target_civ_id = r.target_civ_id) AS mention_count
         FROM civ_relations r
         JOIN civ_civilizations ca ON ca.id = r.source_civ_id
         JOIN civ_civilizations cb ON cb.id = r.target_civ_id
         LEFT JOIN turn_turns t ON t.id = r.last_turn_id
         WHERE r.source_civ_id = ? OR r.target_civ_id = ?
         ORDER BY r.updated_at DESC''',
      variables: [Variable.withInt(civId), Variable.withInt(civId)],
      readsFrom: {},
    ).watch().map(
          (rows) => rows.map((r) => _rowToRelation(r)).toList(),
        );
  }

  CivRelation _rowToRelation(dynamic r) {
    final treatiesRaw = r.read<String?>('treaties');
    final List<String> treaties = treatiesRaw != null
        ? (jsonDecode(treatiesRaw) as List).cast<String>()
        : [];
    return CivRelation(
      id: r.read<int>('id'),
      sourceCivId: r.read<int>('source_civ_id'),
      targetCivId: r.read<int>('target_civ_id'),
      sourceCivName: r.read<String>('source_name'),
      targetCivName: r.read<String>('target_name'),
      opinion: r.read<String>('opinion'),
      description: r.read<String?>('description'),
      treaties: treaties,
      lastTurnNumber: r.read<int?>('last_turn'),
      mentionCount: r.read<int>('mention_count'),
    );
  }
}
