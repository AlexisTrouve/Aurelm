import '../database.dart';

/// One agent-authored memory row (see migration 039 `agent_memory`).
///
/// These are memories the bot writes for itself from GM feedback (via the
/// saveMemory tool). This UI is the GM's review surface — edit / delete / toggle.
class AgentMemory {
  final int id;
  final String memKey;
  final String description;
  final String content;
  final int? civId;
  final String? civName; // joined for display, null = global memory
  final String memType; // 'fact' | 'preference'
  final int? sourceTurn; // anchor turn NUMBER ("as of T<n>"), null = permanent
  final bool active;
  final String updatedAt;

  const AgentMemory({
    required this.id,
    required this.memKey,
    required this.description,
    required this.content,
    required this.civId,
    required this.civName,
    required this.memType,
    required this.sourceTurn,
    required this.active,
    required this.updatedAt,
  });
}

/// Repository for agent memories — raw SQL via Drift customSelect/customStatement.
/// No Drift codegen needed (the table is added by SQL migration, not @DriftDatabase).
///
/// Accepts a nullable [AurelmDatabase]; every method is a safe no-op when null.
class AgentMemoryRepository {
  final AurelmDatabase? _db;

  const AgentMemoryRepository(this._db);

  /// All memories (active first, newest first), with the civ name joined in.
  /// Includes inactive ("forgotten") ones so the GM can review or restore them.
  Future<List<AgentMemory>> loadAll() async {
    final db = _db;
    if (db == null) return [];

    final rows = await db.customSelect(
      'SELECT m.id, m.mem_key, m.description, m.content, m.civ_id, '
      '       c.name AS civ_name, m.mem_type, t.turn_number AS anchor_turn, '
      '       m.active, m.updated_at '
      'FROM agent_memory m '
      'LEFT JOIN civ_civilizations c ON c.id = m.civ_id '
      'LEFT JOIN turn_turns t ON t.id = m.source_turn '
      'ORDER BY m.active DESC, m.updated_at DESC',
    ).get();

    return [
      for (final r in rows)
        AgentMemory(
          id: r.read<int>('id'),
          memKey: r.read<String>('mem_key'),
          description: r.read<String?>('description') ?? '',
          content: r.read<String?>('content') ?? '',
          civId: r.read<int?>('civ_id'),
          civName: r.read<String?>('civ_name'),
          memType: r.read<String?>('mem_type') ?? 'fact',
          sourceTurn: r.read<int?>('anchor_turn'),
          active: r.read<int>('active') != 0,
          updatedAt: r.read<String?>('updated_at') ?? '',
        ),
    ];
  }

  /// Edit a memory's human-facing fields (the GM correcting what the bot stored).
  Future<void> update(
    int id, {
    required String description,
    required String content,
    required String memType,
  }) async {
    final db = _db;
    if (db == null) return;
    await db.customStatement(
      'UPDATE agent_memory SET description = ?, content = ?, mem_type = ?, '
      'updated_at = ? WHERE id = ?',
      [description, content, memType, DateTime.now().toIso8601String(), id],
    );
  }

  /// Toggle active — mirrors the bot's forgetMemory (active=0) and lets the GM
  /// restore a memory (active=1). Inactive memories are not recalled.
  Future<void> setActive(int id, bool active) async {
    final db = _db;
    if (db == null) return;
    await db.customStatement(
      'UPDATE agent_memory SET active = ?, updated_at = ? WHERE id = ?',
      [active ? 1 : 0, DateTime.now().toIso8601String(), id],
    );
  }

  /// Permanently remove a memory (the GM discarding it for good).
  Future<void> delete(int id) async {
    final db = _db;
    if (db == null) return;
    await db.customStatement('DELETE FROM agent_memory WHERE id = ?', [id]);
  }
}
