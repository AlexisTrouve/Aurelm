/// Filter state for the Subjects screen.
class SubjectFilterState {
  /// 'mj_to_pj' | 'pj_to_mj' | null (all directions)
  final String? direction;

  /// 'open' | 'resolved' | null (all statuses)
  final String? subjectStatus;

  final int? civId;

  /// Domain tag filter (militaire, politique, …) — null = no filter
  final String? selectedTag;

  /// When true, only favorited subjects are shown
  final bool favoritesOnly;

  const SubjectFilterState({
    this.direction,
    this.subjectStatus,
    this.civId,
    this.selectedTag,
    this.favoritesOnly = false,
  });

  SubjectFilterState copyWith({
    String? Function()? direction,
    String? Function()? subjectStatus,
    int? Function()? civId,
    String? Function()? selectedTag,
    bool? favoritesOnly,
  }) {
    return SubjectFilterState(
      direction: direction != null ? direction() : this.direction,
      subjectStatus:
          subjectStatus != null ? subjectStatus() : this.subjectStatus,
      civId: civId != null ? civId() : this.civId,
      selectedTag: selectedTag != null ? selectedTag() : this.selectedTag,
      favoritesOnly: favoritesOnly ?? this.favoritesOnly,
    );
  }
}

class EntityFilterState {
  final String? entityType;
  final int? civId;
  final String searchQuery;
  // When true, hidden entities appear in the list (with a visual badge)
  final bool showHidden;
  // Semantic tag filter (migration 013) — null = no filter
  final String? selectedTag;
  // When true, only favorited entities are shown
  final bool favoritesOnly;

  const EntityFilterState({
    this.entityType,
    this.civId,
    this.searchQuery = '',
    this.showHidden = false,
    this.selectedTag,
    this.favoritesOnly = false,
  });

  EntityFilterState copyWith({
    String? Function()? entityType,
    int? Function()? civId,
    String? searchQuery,
    bool? showHidden,
    String? Function()? selectedTag,
    bool? favoritesOnly,
  }) {
    return EntityFilterState(
      entityType: entityType != null ? entityType() : this.entityType,
      civId: civId != null ? civId() : this.civId,
      searchQuery: searchQuery ?? this.searchQuery,
      showHidden: showHidden ?? this.showHidden,
      selectedTag: selectedTag != null ? selectedTag() : this.selectedTag,
      favoritesOnly: favoritesOnly ?? this.favoritesOnly,
    );
  }
}

class TimelineFilterState {
  final int? civId;
  final String? turnType;
  /// Thematic tag filter — if set, only turns containing this tag are shown
  final String? selectedTag;
  /// Turn number range filter (inclusive). null = no bound.
  final int? fromTurn;
  final int? toTurn;
  /// When true, only favorited turns are shown
  final bool favoritesOnly;

  const TimelineFilterState({
    this.civId,
    this.turnType,
    this.selectedTag,
    this.fromTurn,
    this.toTurn,
    this.favoritesOnly = false,
  });

  TimelineFilterState copyWith({
    int? Function()? civId,
    String? Function()? turnType,
    String? Function()? selectedTag,
    int? Function()? fromTurn,
    int? Function()? toTurn,
    bool? favoritesOnly,
  }) {
    return TimelineFilterState(
      civId: civId != null ? civId() : this.civId,
      turnType: turnType != null ? turnType() : this.turnType,
      selectedTag: selectedTag != null ? selectedTag() : this.selectedTag,
      fromTurn: fromTurn != null ? fromTurn() : this.fromTurn,
      toTurn: toTurn != null ? toTurn() : this.toTurn,
      favoritesOnly: favoritesOnly ?? this.favoritesOnly,
    );
  }
}
