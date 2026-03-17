import 'package:drift/drift.dart' show Variable;

import '../database.dart';

/// A candidate name that the GM hasn't resolved yet.
class UnresolvedCivName {
  final String name;
  final int mentionCount;

  const UnresolvedCivName({required this.name, required this.mentionCount});
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
  Future<List<UnresolvedCivName>> loadUnresolved() async {
    final rows = await _db.customSelect('''
      SELECT e.canonical_name AS name, COUNT(*) AS mention_count
      FROM entity_entities e
      JOIN entity_mentions em ON em.entity_id = e.id
      WHERE e.entity_type = 'civilization'
        AND e.disabled = 0
        -- not already a canonical civ name
        AND LOWER(e.canonical_name) NOT IN (
            SELECT LOWER(name) FROM civ_civilizations
        )
        -- not already an alias
        AND LOWER(e.canonical_name) NOT IN (
            SELECT LOWER(alias_name) FROM civ_aliases
        )
        -- not dismissed
        AND e.canonical_name NOT IN (
            SELECT alias_name FROM civ_alias_dismissed
        )
      GROUP BY e.canonical_name
      ORDER BY mention_count DESC
    ''').get();

    return rows
        .map((r) => UnresolvedCivName(
              name: r.read<String>('name'),
              mentionCount: r.read<int>('mention_count'),
            ))
        .toList();
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
