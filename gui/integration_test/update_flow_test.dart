// E2E for the one action the whole update feature exists for: Arthur CLICKS the
// button and the app updates itself.
//
// Every piece was covered in isolation (manifest fetch, hash verify, install
// ordering) but the chain through the real running app never was. Here the real
// AurelmApp boots, the banner appears by itself, we tap "Installer", a real file is
// downloaded and hashed, and we assert the installer would have been launched — with
// the launch/quit injected so the harness is not killed by exit(0).
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:aurelm_gui/app.dart';
import 'package:aurelm_gui/providers/bot_provider.dart';
import 'package:aurelm_gui/providers/database_provider.dart';
import 'package:aurelm_gui/providers/enrollment_provider.dart';
import 'package:aurelm_gui/providers/update_provider.dart';
import 'package:aurelm_gui/services/update_service.dart';

final _installerBytes = utf8.encode('a-fake-but-real-file-standing-in-for-the-installer');
final _installerSha = sha256.convert(_installerBytes).toString();

/// Serves a manifest announcing a version far above whatever is compiled in, plus the
/// binary it points at, so the app really has an update to find.
http.Client _fakeDist({String? sha}) => MockClient((req) async {
      if (req.url.path.endsWith('.json')) {
        return http.Response(
          jsonEncode({
            'version': '999.0.0',
            'url': 'https://dist.test/aurelm/Aurelm-Setup-999.0.0.exe',
            'sha256': sha ?? _installerSha,
            'notes': 'la mise a jour de test',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      return http.Response.bytes(_installerBytes, 200);
    });

Future<void> _pumpFor(WidgetTester tester, {int frames = 20}) async {
  for (var i = 0; i < frames; i++) {
    await tester.pump(const Duration(milliseconds: 200));
  }
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  /// Boot the real app. [activated] false leaves it on the setup wizard, which is the
  /// point of one of the tests below.
  Future<List<String>> boot(
    WidgetTester tester, {
    required bool activated,
    String? sha,
    Directory? dlDir,
  }) async {
    final events = <String>[];
    // A realistic desktop window: the default 800x600 test viewport is smaller than
    // any real one, and the banner legitimately takes ~40px off the top.
    await tester.binding.setSurfaceSize(const Size(1400, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPrefsProvider.overrideWithValue(prefs),
          autoStartBotProvider.overrideWith((ref) async {}),
          setupCompleteProvider.overrideWith((ref) async => activated),
          updateServiceProvider.overrideWithValue(UpdateService(
            client: _fakeDist(sha: sha),
            manifestUrl: 'https://dist.test/aurelm/latest.json',
            tempDirProvider: () async => dlDir ?? Directory.systemTemp,
          )),
          // The irreversible step, captured instead of performed.
          installerLauncherProvider
              .overrideWithValue((path) async => events.add('launched:$path')),
          appQuitProvider.overrideWithValue(() => events.add('quit')),
        ],
        child: const AurelmApp(),
      ),
    );
    await _pumpFor(tester);
    return events;
  }

  testWidgets('the banner appears on its own and CLICKING it performs the update',
      (tester) async {
    final dir = Directory.systemTemp.createTempSync('aurelm_e2e_upd');
    addTearDown(() {
      try {
        dir.deleteSync(recursive: true);
      } catch (_) {}
    });

    final events = await boot(tester, activated: true, dlDir: dir);

    // 1. The startup check ran by itself and the banner is on screen.
    expect(find.textContaining('999.0.0'), findsOneWidget,
        reason: 'the automatic check must surface the new version unprompted');
    expect(find.textContaining('la mise a jour de test'), findsOneWidget);

    // 2. Arthur clicks.
    await tester.tap(find.text('Installer'));
    await _pumpFor(tester, frames: 25);

    // 3. The binary was downloaded, its hash verified, and the installer launched.
    expect(events.where((e) => e.startsWith('launched:')), isNotEmpty,
        reason: 'clicking Installer must end with the installer being launched');
    expect(events, contains('quit'),
        reason: 'the app must quit so the installer can replace its files');
    expect(events.indexWhere((e) => e.startsWith('launched:')) < events.indexOf('quit'),
        isTrue, reason: 'launch before quit');
  });

  testWidgets('a TAMPERED download is refused and the app does NOT quit',
      (tester) async {
    final dir = Directory.systemTemp.createTempSync('aurelm_e2e_bad');
    addTearDown(() {
      try {
        dir.deleteSync(recursive: true);
      } catch (_) {}
    });

    // Manifest advertises a hash the served bytes do not match.
    final events = await boot(tester, activated: true, sha: 'de' * 32, dlDir: dir);

    await tester.tap(find.text('Installer'));
    await _pumpFor(tester, frames: 25);

    expect(events, isEmpty,
        reason: 'nothing may be launched and the app must not quit on a bad hash');
    expect(find.textContaining('sha256'), findsOneWidget,
        reason: 'the integrity failure must be shown to the user, not swallowed');
  });

  testWidgets('an UN-ACTIVATED instance still gets offered the update',
      (tester) async {
    // The banner used to live inside the navigation shell, which sits behind the
    // activation gate: an instance stuck on the wizard would never learn a fix exists.
    await boot(tester, activated: false);

    expect(find.textContaining('999.0.0'), findsOneWidget,
        reason: 'the update check must not be gated behind activation');
  });
}
