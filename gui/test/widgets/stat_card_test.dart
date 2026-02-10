import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:aurelm_gui/widgets/common/stat_card.dart';

void main() {
  group('StatCard', () {
    testWidgets('displays label and value', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: StatCard(
              icon: Icons.history,
              label: 'Turns',
              value: '14',
              color: Colors.blue,
            ),
          ),
        ),
      );

      expect(find.text('Turns'), findsOneWidget);
      expect(find.text('14'), findsOneWidget);
    });

    testWidgets('displays subtitle when provided', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: StatCard(
              icon: Icons.category,
              label: 'Entities',
              value: '199',
              subtitle: 'across all civs',
              color: Colors.green,
            ),
          ),
        ),
      );

      expect(find.text('across all civs'), findsOneWidget);
    });
  });
}
