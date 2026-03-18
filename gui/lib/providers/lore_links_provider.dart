import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:drift/drift.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../utils/lore_linker.dart';
import 'database_provider.dart';

/// Provides a map of lore names -> LoreLink, sorted by name length descending.
/// Loads all active entities + aliases, civilizations, open/resolved subjects,
/// and turns from the DB. Rebuilt when the database provider changes.
final loreLinksProvider = FutureProvider<Map<String, LoreLink>>((ref) async {
  final db = ref.watch(databaseProvider);
  if (db == null) return {};

  final map = <String, LoreLink>{};

  // --- Entities: canonical names of active (non-disabled) entities ---
  final entities = await (db.select(db.entityEntities)
        ..where((e) => e.disabled.equals(false)))
      .get();
  for (final e in entities) {
    map[e.canonicalName] = LoreLink(
      id: e.id,
      type: LoreLinkType.entity,
      route: '/entities/${e.id}',
    );
  }

  // --- Aliases: redirect to the parent entity ---
  final aliases = await db.customSelect(
    '''
    SELECT ea.alias, ea.entity_id
    FROM entity_aliases ea
    JOIN entity_entities ee ON ee.id = ea.entity_id
    WHERE ee.disabled = 0
    ''',
    readsFrom: {db.entityAliases, db.entityEntities},
  ).get();
  for (final row in aliases) {
    final alias = row.read<String>('alias');
    final entityId = row.read<int>('entity_id');
    // Don't overwrite if the canonical name already has this key
    map.putIfAbsent(
      alias,
      () => LoreLink(
        id: entityId,
        type: LoreLinkType.entity,
        route: '/entities/$entityId',
      ),
    );
  }

  // --- Civilizations ---
  final civs = await db.select(db.civCivilizations).get();
  for (final c in civs) {
    map.putIfAbsent(
      c.name,
      () => LoreLink(
        id: c.id,
        type: LoreLinkType.civ,
        route: '/civs/${c.id}',
      ),
    );
  }

  // --- Subjects (open + resolved) ---
  // Linked by title AND by "#N" (subject id shorthand used by the agent).
  final subjects = await (db.select(db.subjectSubjects)
        ..where((s) =>
            s.status.isIn(const ['open', 'resolved'])))
      .get();
  for (final s in subjects) {
    final link = LoreLink(
      id: s.id,
      type: LoreLinkType.subject,
      route: '/subjects/${s.id}',
    );
    map.putIfAbsent(s.title, () => link);
    // "#18" format — agent often references subjects this way
    map.putIfAbsent('#${s.id}', () => link);
  }

  // --- Turns: "Tour N" and "T0N" patterns ---
  // Group turns by turn_number to detect multi-civ ambiguity.
  // If only one civ has turn N -> use that turn's DB id directly.
  // If multiple civs have turn N -> use negative turn_number as sentinel
  // (the chat link handler shows a civ picker for negative IDs).
  final turns = await db.select(db.turnTurns).get();
  final turnsByNumber = <int, List<int>>{}; // turn_number -> [turn_ids]
  for (final t in turns) {
    turnsByNumber.putIfAbsent(t.turnNumber, () => []).add(t.id);
  }
  for (final entry in turnsByNumber.entries) {
    final n = entry.key;
    final ids = entry.value;
    // If exactly one civ has this turn number, link directly to that turn
    // Otherwise use -turnNumber as sentinel for the civ picker
    final id = ids.length == 1 ? ids.first : -n;
    final route = ids.length == 1 ? '/turns/${ids.first}' : '/turns/pick/$n';

    final link = LoreLink(id: id, type: LoreLinkType.turn, route: route);
    // "Tour 5" style
    map.putIfAbsent('Tour $n', () => link);
    // "T05" style (zero-padded)
    final padded = n.toString().padLeft(2, '0');
    map.putIfAbsent('T$padded', () => link);
    // "T5" style (non-padded) — only add if different from padded
    final bare = 'T$n';
    if (bare != 'T$padded') {
      map.putIfAbsent(bare, () => link);
    }
  }

  // Sort by key length descending so longest matches are applied first
  final sorted = Map.fromEntries(
    map.entries.toList()..sort((a, b) => b.key.length.compareTo(a.key.length)),
  );

  return sorted;
});

// ---------------------------------------------------------------------------
// Cached lore-linked text — 2-layer cache:
//   1. In-memory Map (fast path, dies with the process)
//   2. SQLite _lore_link_cache table (persists across restarts)
// Regex runs in a background isolate to avoid blocking the main thread.
// ---------------------------------------------------------------------------

/// In-memory fast path — avoids DB roundtrip on repeated lookups.
int _lastLoreLinksSize = -1;
final _memCache = <String, String>{};

/// MD5 hash of raw text — used as DB key to avoid storing huge text blobs.
String _textHash(String text) =>
    md5.convert(utf8.encode(text)).toString();

/// Top-level function for compute() — must be static/top-level for isolates.
String _computeLoreLinks(_LoreLinkPayload payload) {
  return injectLoreLinks(payload.text, payload.links);
}

/// Payload for the isolate — compute() requires a single argument.
class _LoreLinkPayload {
  final String text;
  final Map<String, LoreLink> links;
  const _LoreLinkPayload(this.text, this.links);
}

/// Async provider: checks mem cache -> DB cache -> compute in isolate.
/// Widget shows raw text while loading, swaps in linked text when ready.
final loreLinkTextProvider =
    FutureProvider.family<String, String>((ref, rawContent) async {
  final loreLinksAsync = ref.watch(loreLinksProvider);
  final loreLinks = loreLinksAsync.valueOrNull;
  final db = ref.watch(databaseProvider);

  // No links available yet — return raw content immediately
  if (loreLinks == null || loreLinks.isEmpty) return rawContent;

  final entityCount = loreLinks.length;

  // If entity set changed, wipe both caches
  if (entityCount != _lastLoreLinksSize) {
    _memCache.clear();
    _lastLoreLinksSize = entityCount;
    // Wipe DB cache for stale entity counts
    if (db != null) {
      try {
        await db.customStatement(
          'DELETE FROM _lore_link_cache WHERE entity_count != ?',
          [entityCount],
        );
      } catch (_) {}
    }
  }

  // Layer 1: in-memory cache (instant)
  final memCached = _memCache[rawContent];
  if (memCached != null) return memCached;

  // Layer 2: DB cache (survives restarts)
  final hash = _textHash(rawContent);
  if (db != null) {
    try {
      final rows = await db.customSelect(
        'SELECT linked_text FROM _lore_link_cache WHERE text_hash = ? AND entity_count = ?',
        variables: [Variable(hash), Variable(entityCount)],
      ).get();
      if (rows.isNotEmpty) {
        final dbCached = rows.first.read<String>('linked_text');
        _memCache[rawContent] = dbCached;
        return dbCached;
      }
    } catch (_) {
      // Table might not exist yet on first run
    }
  }

  // Cache miss — compute in background isolate
  final result = await compute(
    _computeLoreLinks,
    _LoreLinkPayload(rawContent, loreLinks),
  );

  // Store in both caches
  _memCache[rawContent] = result;
  if (db != null) {
    try {
      await db.customStatement(
        'INSERT OR REPLACE INTO _lore_link_cache (text_hash, linked_text, entity_count) VALUES (?, ?, ?)',
        [hash, result, entityCount],
      );
    } catch (_) {}
  }

  return result;
});
