import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:aurelm_gui/widgets/common/entity_type_badge.dart';

void main() {
  group('EntityTypeBadge', () {
    testWidgets('displays entity type text', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: EntityTypeBadge(entityType: 'person')),
        ),
      );

      expect(find.text('person'), findsOneWidget);
    });

    testWidgets('renders compact variant', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EntityTypeBadge(entityType: 'technology', compact: true),
          ),
        ),
      );

      expect(find.text('technology'), findsOneWidget);
    });
  });
}
