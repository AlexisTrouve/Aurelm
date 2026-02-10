import 'package:flutter_test/flutter_test.dart';

import 'package:aurelm_gui/models/filter_state.dart';

void main() {
  group('EntityFilterState', () {
    test('default state has no filters', () {
      const state = EntityFilterState();
      expect(state.entityType, isNull);
      expect(state.civId, isNull);
      expect(state.searchQuery, isEmpty);
    });

    test('copyWith updates entityType', () {
      const state = EntityFilterState();
      final updated = state.copyWith(entityType: () => 'person');
      expect(updated.entityType, 'person');
      expect(updated.civId, isNull);
    });

    test('copyWith clears entityType with null', () {
      const state = EntityFilterState(entityType: 'person');
      final updated = state.copyWith(entityType: () => null);
      expect(updated.entityType, isNull);
    });

    test('copyWith updates searchQuery', () {
      const state = EntityFilterState();
      final updated = state.copyWith(searchQuery: 'argile');
      expect(updated.searchQuery, 'argile');
    });
  });

  group('TimelineFilterState', () {
    test('default state has no filters', () {
      const state = TimelineFilterState();
      expect(state.civId, isNull);
      expect(state.turnType, isNull);
    });

    test('copyWith updates civId', () {
      const state = TimelineFilterState();
      final updated = state.copyWith(civId: () => 1);
      expect(updated.civId, 1);
    });

    test('copyWith updates turnType', () {
      const state = TimelineFilterState();
      final updated = state.copyWith(turnType: () => 'crisis');
      expect(updated.turnType, 'crisis');
    });
  });
}
