import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:aurelm_gui/widgets/common/empty_state.dart';

void main() {
  group('EmptyState', () {
    testWidgets('displays message and icon', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyState(
              icon: Icons.storage,
              message: 'No data available',
            ),
          ),
        ),
      );

      expect(find.text('No data available'), findsOneWidget);
      expect(find.byIcon(Icons.storage), findsOneWidget);
    });

    testWidgets('displays subtitle when provided', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyState(
              icon: Icons.category,
              message: 'No entities',
              subtitle: 'Try adjusting filters',
            ),
          ),
        ),
      );

      expect(find.text('Try adjusting filters'), findsOneWidget);
    });

    testWidgets('displays action widget when provided', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EmptyState(
              icon: Icons.storage,
              message: 'No database',
              action: ElevatedButton(
                onPressed: () {},
                child: const Text('Configure'),
              ),
            ),
          ),
        ),
      );

      expect(find.text('Configure'), findsOneWidget);
    });
  });
}
