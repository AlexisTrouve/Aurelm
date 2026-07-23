// The banner is the only thing that tells Arthur an update exists, and until now it
// rendered in no test at all (the E2E boots with updates disabled on purpose).
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:aurelm_gui/core/constants/app_constants.dart';
import 'package:aurelm_gui/providers/update_provider.dart';
import 'package:aurelm_gui/services/update_service.dart';
import 'package:aurelm_gui/widgets/common/update_banner.dart';

Widget _app(String servedVersion) => ProviderScope(
      overrides: [
        updateServiceProvider.overrideWithValue(UpdateService(
          manifestUrl: 'https://x/latest.json',
          client: MockClient((_) async => http.Response(
                jsonEncode({
                  'version': servedVersion,
                  'url': 'https://x/Aurelm-Setup-$servedVersion.exe',
                  'sha256': 'ab' * 32,
                  'notes': 'corrections diverses',
                }),
                200,
                headers: {'content-type': 'application/json'},
              )),
        )),
      ],
      // NoSplash: tapping a Material button in a widget test otherwise tries to load
      // the ink_sparkle shader asset, which is unavailable in the test harness.
      child: MaterialApp(
        theme: ThemeData(splashFactory: NoSplash.splashFactory),
        home: const Scaffold(body: UpdateBanner()),
      ),
    );

void main() {
  testWidgets('shows the version and its notes once the startup check finds one',
      (tester) async {
    await tester.pumpWidget(_app('99.0.0'));
    await tester.pump(); // let the fire-and-forget startup check land
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.textContaining('99.0.0'), findsOneWidget);
    expect(find.textContaining('corrections diverses'), findsOneWidget);
    expect(find.text('Installer'), findsOneWidget);
    expect(find.text('Plus tard'), findsOneWidget);
  });

  testWidgets('renders nothing when already up to date', (tester) async {
    await tester.pumpWidget(_app(AppConstants.appVersion));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Installer'), findsNothing);
    expect(find.byType(Material).evaluate().length, lessThan(3),
        reason: 'the banner must occupy no space when there is no update');
  });

  testWidgets('"Plus tard" hides it for the session', (tester) async {
    await tester.pumpWidget(_app('99.0.0'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('Plus tard'), findsOneWidget);

    await tester.tap(find.text('Plus tard'));
    await tester.pump();

    expect(find.text('Installer'), findsNothing);
    expect(find.textContaining('99.0.0'), findsNothing);
  });
}
