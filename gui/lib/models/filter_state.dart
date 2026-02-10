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
