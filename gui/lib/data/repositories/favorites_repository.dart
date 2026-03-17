import '../database.dart';

/// Repository for user favorites — raw SQL via Drift customSelect/customStatement.
/// No Drift codegen needed: no new table class, no new DAO in @DriftDatabase.
///
/// Favorites are identified by string keys "type_id" (e.g. "entity_42"),
/// stored as a Set<String> in the Riverpod provider for O(1) in-memory lookup.
///
/// Accepts a nullable [AurelmDatabase] — all methods are no-ops when db is null.
class FavoritesRepository {
  final AurelmDatabase? _db;

  const FavoritesRepository(this._db);

  /// Load all favorites → Set<"type_id"> (e.g. {"entity_42", "turn_7"}).
  Future<Set<String>> loadAll() async {
    final db = _db;
    if (db == null) return {};

    final rows = await db.customSelect(
      'SELECT type, entity_id, subject_id, turn_id FROM user_favorites',
    ).get();

    final result = <String>{};
    for (final r in rows) {
      final type = r.read<String>('type');
      final int? id = switch (type) {
        'entity' => r.read<int?>('entity_id'),
        'subject' => r.read<int?>('subject_id'),
        'turn' => r.read<int?>('turn_id'),
        _ => null,
      };
      if (id != null) result.add('${type}_$id');
    }
    return result;
  }

  /// Add a favorite. INSERT OR IGNORE — safe to call even if already favorited.
  Future<void> add(String type, int id, int? civId) async {
    final db = _db;
    if (db == null) return;

    final col = _col(type);
    await db.customStatement(
      'INSERT OR IGNORE INTO user_favorites (type, $col, civ_id, created_at)'
      ' VALUES (?, ?, ?, ?)',
      [type, id, civId, DateTime.now().toIso8601String()],
    );
  }

  /// Remove a favorite by type + id.
  Future<void> remove(String type, int id) async {
    final db = _db;
    if (db == null) return;

    await db.customStatement(
      'DELETE FROM user_favorites WHERE ${_col(type)} = ?',
      [id],
    );
  }

  /// Map type string → DB column name.
  static String _col(String type) => switch (type) {
        'entity' => 'entity_id',
        'subject' => 'subject_id',
        'turn' => 'turn_id',
        _ => throw ArgumentError('Unknown favorite type: $type'),
      };
}
