// The update controller: one flow behind two surfaces (shell banner + Settings card).
// The rule that matters most here — the STARTUP auto-check must never break or delay
// the launch, whatever the update host does.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:aurelm_gui/core/constants/app_constants.dart';
import 'package:aurelm_gui/providers/update_provider.dart';
import 'package:aurelm_gui/services/update_service.dart';

ProviderContainer _container(Future<http.Response> Function(http.Request) handler) {
  final c = ProviderContainer(overrides: [
    updateServiceProvider.overrideWithValue(
      UpdateService(client: MockClient(handler), manifestUrl: 'https://x/latest.json'),
    ),
  ]);
  addTearDown(c.dispose);
  return c;
}

http.Response _manifest(String version) => http.Response(
      jsonEncode({
        'version': version,
        'url': 'https://x/Aurelm-Setup-$version.exe',
        'sha256': 'ab' * 32,
        'notes': 'des corrections',
      }),
      200,
      headers: {'content-type': 'application/json'},
    );

/// Let the fire-and-forget startup check settle.
Future<void> _settle() => Future<void>.delayed(const Duration(milliseconds: 50));

void main() {
  test('auto-checks at creation and surfaces a newer version', () async {
    final c = _container((_) async => _manifest('99.0.0'));
    c.read(updateControllerProvider); // creating the controller starts the check
    await _settle();

    final s = c.read(updateControllerProvider);
    expect(s.available, isNotNull);
    expect(s.available!.version, '99.0.0');
    expect(s.showBanner, isTrue, reason: 'the shell banner must appear on its own');
  });

  test('stays silent when already up to date', () async {
    final c = _container((_) async => _manifest(AppConstants.appVersion));
    c.read(updateControllerProvider);
    await _settle();

    final s = c.read(updateControllerProvider);
    expect(s.available, isNull);
    expect(s.showBanner, isFalse);
    expect(s.status, isNull, reason: 'a silent startup check must not chatter');
    expect(s.error, isNull);
  });

  test('a dead update host cannot break startup', () async {
    for (final handler in <Future<http.Response> Function(http.Request)>[
      (_) async => throw const SocketException('VPS down'),
      (_) async => http.Response('boom', 500),
      (_) async => http.Response('not json', 200),
    ]) {
      final c = _container(handler);
      c.read(updateControllerProvider);
      await _settle();

      final s = c.read(updateControllerProvider);
      expect(s.showBanner, isFalse);
      expect(s.error, isNull, reason: 'an update outage is not an application error');
      expect(s.busy, isFalse);
    }
  });

  test('dismiss hides the banner without forgetting the update', () async {
    final c = _container((_) async => _manifest('99.0.0'));
    c.read(updateControllerProvider);
    await _settle();

    c.read(updateControllerProvider.notifier).dismiss();
    final s = c.read(updateControllerProvider);
    expect(s.showBanner, isFalse, reason: 'dismissed for the session');
    expect(s.available, isNotNull,
        reason: 'Settings must still offer it after the banner is dismissed');
  });

  test('a manual check reports the outcome, unlike the silent one', () async {
    final c = _container((_) async => _manifest(AppConstants.appVersion));
    c.read(updateControllerProvider);
    await _settle();
    expect(c.read(updateControllerProvider).status, isNull);

    await c.read(updateControllerProvider.notifier).check();
    expect(c.read(updateControllerProvider).status, contains('Aucune mise à jour'));
  });
}
