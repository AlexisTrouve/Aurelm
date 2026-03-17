import 'package:drift/drift.dart' show Variable;

import '../database.dart';

/// A candidate name that the GM hasn't resolved yet.
class UnresolvedCivName {
  final String name;
  final int mentionCount;
  /// Sample mention contexts: "Tour X: [context snippet]"
  final List<String> passages;

  const UnresolvedCivName({
    required this.name,
    required this.mentionCount,
    this.passages = const [],
  });
}

/// A known alias for a civ.
class CivAliasEntry {
  final int id;
  final int civId;
  final String aliasName;

  const CivAliasEntry({
    required this.id,
    required this.civId,
    required this.aliasName,
  });
}

/// Raw-SQL repository for civ alias management.
///
/// Sits alongside CivRelationsRepository — no Drift codegen, pure customSelect /
/// customStatement. The GM uses this through CivAliasResolverScreen to map
/// LLM-extracted "civilization" entity names to canonical civ entries.
class CivAliasRepository {
  final AurelmDatabase _db;
  CivAliasRepository(this._db);

  // ---------------------------------------------------------------------------
  // Unresolved names — feed the resolver UI
  // ---------------------------------------------------------------------------

  /// All distinct entity names of type "civilization" that are not yet mapped
  /// to any civ (neither by canonical name, alias, nor dismissed).
  /// Ordered by mention count descending so the most relevant appear first.
  /// Each item includes up to 3 mention passages to help the GM identify the civ.
  Future<List<UnresolvedCivName>> loadUnresolved() async {
    final rows = await _db.customSelect('''
      SELECT e.canonical_name AS name, COUNT(*) AS mention_count
      FROM entity_entities e
      JOIN entity_mentions em ON em.entity_id = e.id
      WHERE e.entity_type = 'civilization'
        AND e.disabled = 0
        AND LOWER(e.canonical_name) NOT IN (SELECT LOWER(name) FROM civ_civilizations)
        AND LOWER(e.canonical_name) NOT IN (SELECT LOWER(alias_name) FROM civ_aliases)
        AND e.canonical_name NOT IN (SELECT alias_name FROM civ_alias_dismissed)
      GROUP BY e.canonical_name
      ORDER BY mention_count DESC
    ''').get();

    final result = <UnresolvedCivName>[];
    for (final r in rows) {
      final name = r.read<String>('name');
      final count = r.read<int>('mention_count');

      // Load up to 3 mention passages with their turn number
      final passageRows = await _db.customSelect('''
        SELECT t.turn_number, em.mention_text
        FROM entity_mentions em
        JOIN entity_entities e ON e.id = em.entity_id
        JOIN turn_turns t ON t.id = em.turn_id
        WHERE e.canonical_name = ? AND e.entity_type = 'civilization'
        ORDER BY t.turn_number DESC
        LIMIT 3
      ''', variables: [Variable.withString(name)]).get();

      final passages = passageRows.map((p) {
        final turnNum = p.read<int>('turn_number');
        final text = p.read<String?>('mention_text') ?? '';
        return 'Tour $turnNum: $text';
      }).toList();

      result.add(UnresolvedCivName(name: name, mentionCount: count, passages: passages));
    }
    return result;
  }

  /// Count of unresolved civ names — used for the dashboard badge.
  Future<int> loadUnresolvedCount() async {
    final row = await _db.customSelect('''
      SELECT COUNT(DISTINCT e.canonical_name) AS n
      FROM entity_entities e
      JOIN entity_mentions em ON em.entity_id = e.id
      WHERE e.entity_type = 'civilization'
        AND e.disabled = 0
        AND LOWER(e.canonical_name) NOT IN (SELECT LOWER(name) FROM civ_civilizations)
        AND LOWER(e.canonical_name) NOT IN (SELECT LOWER(alias_name) FROM civ_aliases)
        AND e.canonical_name NOT IN (SELECT alias_name FROM civ_alias_dismissed)
    ''').getSingleOrNull();
    return row?.read<int>('n') ?? 0;
  }

  // ---------------------------------------------------------------------------
  // Alias management
  // ---------------------------------------------------------------------------

  /// Map [aliasName] to [civId]. Idempotent (UNIQUE index on alias_name).
  Future<void> addAlias(int civId, String aliasName) async {
    await _db.customStatement(
      'INSERT OR IGNORE INTO civ_aliases (civ_id, alias_name) VALUES (?, ?)',
      [civId, aliasName],
    );
  }

  /// Delete an alias by its row id.
  Future<void> deleteAlias(int aliasId) async {
    await _db.customStatement(
      'DELETE FROM civ_aliases WHERE id = ?',
      [aliasId],
    );
  }

  /// All aliases for a given civ — shown in CivDetailScreen.
  Future<List<CivAliasEntry>> loadAliasesForCiv(int civId) async {
    final rows = await _db.customSelect(
      'SELECT id, civ_id, alias_name FROM civ_aliases WHERE civ_id = ? ORDER BY alias_name',
      variables: [Variable.withInt(civId)],
    ).get();

    return rows
        .map((r) => CivAliasEntry(
              id: r.read<int>('id'),
              civId: r.read<int>('civ_id'),
              aliasName: r.read<String>('alias_name'),
            ))
        .toList();
  }

  // ---------------------------------------------------------------------------
  // Dismissed false positives
  // ---------------------------------------------------------------------------

  /// Mark [name] as a false positive — won't appear in the resolver again.
  Future<void> dismiss(String name) async {
    await _db.customStatement(
      'INSERT OR IGNORE INTO civ_alias_dismissed (alias_name) VALUES (?)',
      [name],
    );
  }

  /// Remove a dismissal (GM made a mistake).
  Future<void> undismiss(String name) async {
    await _db.customStatement(
      'DELETE FROM civ_alias_dismissed WHERE alias_name = ?',
      [name],
    );
  }
}
