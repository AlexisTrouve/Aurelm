import 'package:drift/drift.dart';

import '../database.dart';
import '../tables/subjects.dart';
import '../tables/turns.dart';
import '../tables/civilizations.dart';
import '../../models/filter_state.dart';
import '../../models/subject_with_details.dart';

part 'subject_dao.g.dart';

@DriftAccessor(tables: [
  SubjectSubjects,
  SubjectOptions,
  SubjectResolutions,
  TurnTurns,
  CivCivilizations,
])
class SubjectDao extends DatabaseAccessor<AurelmDatabase>
    with _$SubjectDaoMixin {
  SubjectDao(super.db);

  // ---------------------------------------------------------------------------
  // List queries
  // ---------------------------------------------------------------------------

  /// Stream of subjects, optionally filtered by direction, status, and civ.
  /// Joins with turn_turns for turn_number and civ_civilizations for civ_name.
  Stream<List<SubjectWithDetails>> watchSubjects(SubjectFilterState filters) {
    var query = select(subjectSubjects).join([
      innerJoin(turnTurns, turnTurns.id.equalsExp(subjectSubjects.sourceTurnId)),
      innerJoin(civCivilizations,
          civCivilizations.id.equalsExp(subjectSubjects.civId)),
    ]);

    // Apply direction filter
    if (filters.direction != null) {
      query.where(subjectSubjects.direction.equals(filters.direction!));
    }
    // Apply status filter
    if (filters.subjectStatus != null) {
      query.where(subjectSubjects.status.equals(filters.subjectStatus!));
    }
    // Apply civ filter
    if (filters.civId != null) {
      query.where(subjectSubjects.civId.equals(filters.civId!));
    }
    // Apply tag filter — tags stored as JSON array, use LIKE '%"tag"%'
    if (filters.selectedTag != null) {
      query.where(
        subjectSubjects.tags.like('%"${filters.selectedTag!}"%'),
      );
    }

    // Most recent turns first, then by subject id
    query.orderBy([
      OrderingTerm.desc(turnTurns.turnNumber),
      OrderingTerm.desc(subjectSubjects.id),
    ]);

    return query.watch().asyncMap((rows) async {
      final results = <SubjectWithDetails>[];
      for (final row in rows) {
        final subject = row.readTable(subjectSubjects);
        final turn = row.readTable(turnTurns);
        final civ = row.readTable(civCivilizations);

        final options = await _loadOptions(subject.id);
        final (best, bestTurn, count) = await _loadBestResolution(subject.id);

        results.add(SubjectWithDetails(
          subject: subject,
          sourceTurnId: turn.id,
          sourceTurnNumber: turn.turnNumber,
          civName: civ.name,
          options: options,
          bestResolution: best,
          bestResolutionTurnNumber: bestTurn,
          resolutionCount: count,
        ));
      }
      return results;
    });
  }

  // ---------------------------------------------------------------------------
  // Detail query
  // ---------------------------------------------------------------------------

  /// Full subject detail with all resolution attempts.
  Stream<SubjectDetail?> watchSubjectDetail(int subjectId) {
    return (select(subjectSubjects)
          ..where((s) => s.id.equals(subjectId)))
        .watchSingleOrNull()
        .asyncMap((subject) async {
      if (subject == null) return null;

      // Load source turn number (null for GM-created subjects)
      final turn = subject.sourceTurnId == null
          ? null
          : await (select(turnTurns)
                ..where((t) => t.id.equals(subject.sourceTurnId!)))
              .getSingleOrNull();
      final civ = await (select(civCivilizations)
            ..where((c) => c.id.equals(subject.civId)))
          .getSingleOrNull();

      final options = await _loadOptions(subject.id);
      final (best, bestTurn, count) = await _loadBestResolution(subject.id);

      // All resolutions ordered by confidence desc then by turn desc
      final resRows = await (select(subjectResolutions).join([
        innerJoin(turnTurns,
            turnTurns.id.equalsExp(subjectResolutions.resolvedByTurnId)),
      ])
            ..where(subjectResolutions.subjectId.equals(subject.id))
            ..orderBy([
              OrderingTerm.desc(subjectResolutions.confidence),
              OrderingTerm.desc(turnTurns.turnNumber),
            ]))
          .get();

      final allResolutions = resRows
          .map((r) => ResolutionWithTurn(
                resolution: r.readTable(subjectResolutions),
                turnId: r.readTable(turnTurns).id,
                turnNumber: r.readTable(turnTurns).turnNumber,
              ))
          .toList();

      return SubjectDetail(
        subject: subject,
        sourceTurnId: turn?.id ?? 0,
        sourceTurnNumber: turn?.turnNumber ?? 0,
        civName: civ?.name ?? 'Unknown',
        options: options,
        bestResolution: best,
        bestResolutionTurnNumber: bestTurn,
        resolutionCount: count,
        allResolutions: allResolutions,
      );
    });
  }

  // ---------------------------------------------------------------------------
  // Stats
  // ---------------------------------------------------------------------------

  /// Open / resolved counts for a civ (for dashboard summary).
  Stream<Map<String, int>> watchSubjectStats(int civId) {
    final countExpr = subjectSubjects.id.count();
    final query = selectOnly(subjectSubjects)
      ..addColumns([subjectSubjects.status, countExpr])
      ..where(subjectSubjects.civId.equals(civId))
      ..groupBy([subjectSubjects.status]);

    return query.watch().map((rows) {
      final map = <String, int>{};
      for (final row in rows) {
        final status = row.read(subjectSubjects.status);
        final count = row.read(countExpr);
        if (status != null && count != null) map[status] = count;
      }
      return map;
    });
  }

  // ---------------------------------------------------------------------------
  // Mutations
  // ---------------------------------------------------------------------------

  /// Manually update a subject's status. Valid values: 'open', 'resolved', 'abandoned', 'superseded'.
  Future<void> updateSubjectStatus(int subjectId, String status) {
    return (update(subjectSubjects)..where((s) => s.id.equals(subjectId)))
        .write(SubjectSubjectsCompanion(
          status: Value(status),
          updatedAt: Value(DateTime.now().toIso8601String()),
        ));
  }

  /// Create a new GM-created subject (no source turn).
  Future<int> createSubject({
    required int civId,
    required String direction,
    required String title,
    required String category,
    String? description,
    List<String> tags = const [],
  }) {
    final now = DateTime.now().toIso8601String();
    return into(subjectSubjects).insert(
      SubjectSubjectsCompanion.insert(
        civId: civId,
        direction: direction,
        title: title,
        category: category,
        description: Value(description),
        tags: Value('[${tags.map((t) => '"$t"').join(',')}]'),
        createdAt: now,
        updatedAt: now,
      ),
    );
  }

  /// Update editable fields of an existing subject (GM edit).
  Future<void> updateSubject({
    required int subjectId,
    String? title,
    String? description,
    String? direction,
    String? category,
    String? status,
    List<String>? tags,
  }) {
    return (update(subjectSubjects)..where((s) => s.id.equals(subjectId)))
        .write(SubjectSubjectsCompanion(
          title: title != null ? Value(title) : const Value.absent(),
          description:
              description != null ? Value(description) : const Value.absent(),
          direction:
              direction != null ? Value(direction) : const Value.absent(),
          category: category != null ? Value(category) : const Value.absent(),
          status: status != null ? Value(status) : const Value.absent(),
          tags: tags != null
              ? Value('[${tags.map((t) => '"$t"').join(',')}]')
              : const Value.absent(),
          updatedAt: Value(DateTime.now().toIso8601String()),
        ));
  }

  /// Add a resolution attempt manually (GM-entered resolution).
  Future<void> addResolution({
    required int subjectId,
    required int resolvedByTurnId,
    required String resolutionText,
    double confidence = 1.0,
    int? chosenOptionId,
  }) {
    return into(subjectResolutions).insert(
      SubjectResolutionsCompanion.insert(
        subjectId: subjectId,
        resolvedByTurnId: resolvedByTurnId,
        resolutionText: resolutionText,
        confidence: Value(confidence),
        chosenOptionId: Value(chosenOptionId),
        createdAt: DateTime.now().toIso8601String(),
      ),
    );
  }

  /// Add an option to a subject.
  Future<void> addOption({
    required int subjectId,
    required int optionNumber,
    required String label,
    String? description,
    bool isLibre = false,
  }) {
    return into(subjectOptions).insert(
      SubjectOptionsCompanion.insert(
        subjectId: subjectId,
        optionNumber: optionNumber,
        label: label,
        description: Value(description),
        isLibre: Value(isLibre),
      ),
    );
  }

  /// Remove an option.
  Future<void> removeOption(int optionId) {
    return (delete(subjectOptions)
          ..where((o) => o.id.equals(optionId)))
        .go();
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  Future<List<SubjectOptionRow>> _loadOptions(int subjectId) {
    return (select(subjectOptions)
          ..where((o) => o.subjectId.equals(subjectId))
          ..orderBy([(o) => OrderingTerm.asc(o.optionNumber)]))
        .get();
  }

  /// Returns (best resolution, turn number of that resolution, total count).
  Future<(SubjectResolutionRow?, int?, int)> _loadBestResolution(
      int subjectId) async {
    final rows = await (select(subjectResolutions).join([
      innerJoin(turnTurns,
          turnTurns.id.equalsExp(subjectResolutions.resolvedByTurnId)),
    ])
          ..where(subjectResolutions.subjectId.equals(subjectId))
          ..orderBy([OrderingTerm.desc(subjectResolutions.confidence)])
          ..limit(1))
        .get();

    if (rows.isEmpty) return (null, null, 0);

    // Count total resolutions separately
    final countExpr = subjectResolutions.id.count();
    final countRow = await (selectOnly(subjectResolutions)
          ..addColumns([countExpr])
          ..where(subjectResolutions.subjectId.equals(subjectId)))
        .getSingle();
    final total = countRow.read(countExpr) ?? 0;

    return (
      rows.first.readTable(subjectResolutions),
      rows.first.readTable(turnTurns).turnNumber,
      total,
    );
  }
}
