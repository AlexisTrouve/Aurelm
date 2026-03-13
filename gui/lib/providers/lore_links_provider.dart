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
  final subjects = await (db.select(db.subjectSubjects)
        ..where((s) =>
            s.status.isIn(const ['open', 'resolved'])))
      .get();
  for (final s in subjects) {
    map.putIfAbsent(
      s.title,
      () => LoreLink(
        id: s.id,
        type: LoreLinkType.subject,
        route: '/subjects/${s.id}',
      ),
    );
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
// Cached lore-linked text — avoids re-running regex on every widget rebuild.
// Keyed by raw content string, invalidated when loreLinksProvider changes.
// ---------------------------------------------------------------------------

/// Holds the cached link map identity + transformed text cache.
/// When loreLinksProvider yields a new map object, the cache is wiped.
Map<String, LoreLink>? _lastLoreLinks;
final _loreLinkedTextCache = <String, String>{};

/// Returns [rawContent] with lore links injected, using a simple cache.
/// Cache auto-clears when the underlying lore link map changes.
final loreLinkTextProvider =
    Provider.family<String, String>((ref, rawContent) {
  final loreLinksAsync = ref.watch(loreLinksProvider);
  final loreLinks = loreLinksAsync.valueOrNull;

  // No links available yet — return raw content
  if (loreLinks == null || loreLinks.isEmpty) return rawContent;

  // If the link map instance changed, wipe the cache
  if (!identical(loreLinks, _lastLoreLinks)) {
    _loreLinkedTextCache.clear();
    _lastLoreLinks = loreLinks;
  }

  // Check cache
  final cached = _loreLinkedTextCache[rawContent];
  if (cached != null) return cached;

  // Compute and cache
  final result = injectLoreLinks(rawContent, loreLinks);
  _loreLinkedTextCache[rawContent] = result;
  return result;
});
