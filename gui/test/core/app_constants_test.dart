import 'package:flutter_test/flutter_test.dart';

import 'package:aurelm_gui/core/constants/app_constants.dart';

void main() {
  group('AppConstants', () {
    test('has the full entity-type vocabulary', () {
      // Locks the exact set (not just a count) so a future add/remove is a
      // deliberate test change, not a silent drift — this test had rotted at 7
      // while the vocab grew to 10 (person..belief, per the domain Key Concepts).
      const expected = {
        'person', 'place', 'technology', 'institution', 'resource',
        'creature', 'event', 'civilization', 'caste', 'belief',
      };
      expect(AppConstants.entityTypes.toSet(), expected);
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
