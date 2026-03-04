/// Filter state for the Subjects screen.
class SubjectFilterState {
  /// 'mj_to_pj' | 'pj_to_mj' | null (all directions)
  final String? direction;

  /// 'open' | 'resolved' | null (all statuses)
  final String? subjectStatus;

  final int? civId;

  const SubjectFilterState({
    this.direction,
    this.subjectStatus,
    this.civId,
  });

  SubjectFilterState copyWith({
    String? Function()? direction,
    String? Function()? subjectStatus,
    int? Function()? civId,
  }) {
    return SubjectFilterState(
      direction: direction != null ? direction() : this.direction,
      subjectStatus:
          subjectStatus != null ? subjectStatus() : this.subjectStatus,
      civId: civId != null ? civId() : this.civId,
    );
  }
}

class EntityFilterState {
  final String? entityType;
  final int? civId;
  final String searchQuery;

  const EntityFilterState({
    this.entityType,
    this.civId,
    this.searchQuery = '',
  });

  EntityFilterState copyWith({
    String? Function()? entityType,
    int? Function()? civId,
    String? searchQuery,
  }) {
    return EntityFilterState(
      entityType: entityType != null ? entityType() : this.entityType,
      civId: civId != null ? civId() : this.civId,
      searchQuery: searchQuery ?? this.searchQuery,
    );
  }
}

class TimelineFilterState {
  final int? civId;
  final String? turnType;

  const TimelineFilterState({this.civId, this.turnType});

  TimelineFilterState copyWith({
    int? Function()? civId,
    String? Function()? turnType,
  }) {
    return TimelineFilterState(
      civId: civId != null ? civId() : this.civId,
      turnType: turnType != null ? turnType() : this.turnType,
    );
  }
}
