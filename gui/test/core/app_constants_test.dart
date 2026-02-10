import 'package:flutter_test/flutter_test.dart';

import 'package:aurelm_gui/core/constants/app_constants.dart';

void main() {
  group('AppConstants', () {
    test('has 7 entity types', () {
      expect(AppConstants.entityTypes.length, 7);
      expect(AppConstants.entityTypes, contains('person'));
      expect(AppConstants.entityTypes, contains('creature'));
    });

    test('has 5 segment types', () {
      expect(AppConstants.segmentTypes.length, 5);
      expect(AppConstants.segmentTypes, contains('narrative'));
      expect(AppConstants.segmentTypes, contains('ooc'));
    });

    test('has 4 turn types', () {
      expect(AppConstants.turnTypes.length, 4);
      expect(AppConstants.turnTypes, contains('standard'));
      expect(AppConstants.turnTypes, contains('crisis'));
    });
  });
}
