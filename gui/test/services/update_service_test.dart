// Update client: version comparison, manifest handling, and the two rules that
// matter — never block the app, never execute an unverified binary.
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:aurelm_gui/services/update_service.dart';

late Directory _dlDir;

UpdateService _svc(Future<http.Response> Function(http.Request) handler) => UpdateService(
      client: MockClient(handler),
      manifestUrl: 'https://x/latest.json',
      tempDirProvider: () async => _dlDir,
    );

http.Response _manifest(Map<String, dynamic> j) =>
    http.Response(jsonEncode(j), 200, headers: {'content-type': 'application/json'});

void main() {
  setUp(() => _dlDir = Directory.systemTemp.createTempSync('aurelm_upd'));
  tearDown(() { try { _dlDir.deleteSync(recursive: true); } catch (_) {} });

  group('compareVersions', () {
    test('compares numerically, not lexically', () {
      // The bug this guards: "0.10.0" < "0.9.0" as strings would silently stop
      // offering updates after the 9th minor.
      expect(UpdateService.compareVersions('0.10.0', '0.9.0'), greaterThan(0));
      expect(UpdateService.compareVersions('1.0.0', '0.99.99'), greaterThan(0));
      expect(UpdateService.compareVersions('0.2.0', '0.2.0'), 0);
      expect(UpdateService.compareVersions('0.1.9', '0.2.0'), lessThan(0));
    });

    test('tolerates missing parts and build suffixes', () {
      expect(UpdateService.compareVersions('1.2', '1.2.0'), 0);
      expect(UpdateService.compareVersions('1.2.3+7', '1.2.3'), 0);
      expect(UpdateService.compareVersions('1.3.0-beta', '1.2.9'), greaterThan(0));
    });
  });

  group('check', () {
    test('offers a strictly newer version', () async {
      final svc = _svc((_) async => _manifest({
            'version': '0.3.0',
            'url': 'https://x/Aurelm-Setup-0.3.0.exe',
            'sha256': 'ab' * 32,
            'notes': 'des trucs',
          }));
      final info = await svc.check(currentVersion: '0.2.0');
      expect(info, isNotNull);
      expect(info!.version, '0.3.0');
      expect(info.notes, 'des trucs');
    });

    test('returns null when already up to date', () async {
      final svc = _svc((_) async =>
          _manifest({'version': '0.2.0', 'url': 'https://x/a.exe', 'sha256': 'ab' * 32}));
      expect(await svc.check(currentVersion: '0.2.0'), isNull);
    });

    test('a manifest without a sha256 is refused, not half-trusted', () async {
      final svc = _svc((_) async => _manifest({'version': '9.9.9', 'url': 'https://x/a.exe'}));
      expect(await svc.check(currentVersion: '0.1.0'), isNull);
    });

    test('never throws when the update host is down — an outage is not an app error',
        () async {
      for (final handler in <Future<http.Response> Function(http.Request)>[
        (_) async => throw const SocketException('VPS down'),
        (_) async => http.Response('nope', 502),
        (_) async => http.Response('<html>not json</html>', 200),
        (_) async => http.Response('[]', 200), // valid JSON, wrong shape
      ]) {
        expect(await _svc(handler).check(currentVersion: '0.1.0'), isNull);
      }
    });

    test('a slow server does not hang the caller', () async {
      final svc = _svc((_) async {
        await Future<void>.delayed(const Duration(seconds: 5));
        return _manifest({'version': '9.9.9', 'url': 'https://x/a.exe', 'sha256': 'ab' * 32});
      });
      final sw = Stopwatch()..start();
      final info = await svc.check(
          currentVersion: '0.1.0', timeout: const Duration(milliseconds: 150));
      sw.stop();
      expect(info, isNull);
      expect(sw.elapsed, lessThan(const Duration(seconds: 3)));
    });
  });

  group('download integrity', () {
    final payload = utf8.encode('installer-bytes');
    final goodHash = sha256.convert(payload).toString();

    test('accepts a binary whose hash matches the manifest', () async {
      final svc = _svc((_) async => http.Response.bytes(payload, 200));
      final file = await svc.download(UpdateInfo(
          version: '0.3.0', url: 'https://x/Aurelm-Setup-0.3.0.exe', sha256: goodHash));
      expect(await file.readAsBytes(), payload);
      await file.delete();
    });

    test('REJECTS a tampered binary and deletes it', () async {
      final svc = _svc((_) async => http.Response.bytes(utf8.encode('evil'), 200));
      final expected = File('${_dlDir.path}${Platform.pathSeparator}Aurelm-Setup-0.3.0.exe');
      await expectLater(
        svc.download(UpdateInfo(
            version: '0.3.0', url: 'https://x/Aurelm-Setup-0.3.0.exe', sha256: goodHash)),
        throwsA(isA<UpdateIntegrityError>()),
      );
      // A hash-mismatched installer must not be left on disk where it could be run.
      expect(expected.existsSync(), isFalse);
    });
  });

  group('installAndExit', () {
    test('stops the bot BEFORE launching the installer', () async {
      // Ordering is the whole point: the embedded python.exe holds handles inside
      // {app}\python, so the installer cannot replace those files until it is stopped.
      final order = <String>[];
      var quit = false;
      await UpdateService().installAndExit(
        File('C:/tmp/Aurelm-Setup-1.0.0.exe'),
        onBeforeExit: () async => order.add('bot-stopped'),
        launcher: (p) async => order.add('launched:$p'),
        quit: () => quit = true,
      );
      expect(order, ['bot-stopped', 'launched:C:/tmp/Aurelm-Setup-1.0.0.exe']);
      expect(quit, isTrue, reason: 'the app must exit so the files are released');
    });

    test('a bot that refuses to stop does not block the update', () async {
      var launched = false;
      await UpdateService().installAndExit(
        File('C:/tmp/x.exe'),
        onBeforeExit: () async => throw Exception('bot stuck'),
        launcher: (_) async => launched = true,
        quit: () {},
      );
      expect(launched, isTrue);
    });

    test('does NOT quit when the installer fails to launch', () async {
      // Quitting without having started an installer would look like a crash and
      // leave nothing updated: the error must surface instead.
      var quit = false;
      await expectLater(
        UpdateService().installAndExit(
          File('C:/tmp/x.exe'),
          launcher: (_) async => throw const ProcessException('x.exe', [], 'nope'),
          quit: () => quit = true,
        ),
        throwsA(isA<ProcessException>()),
      );
      expect(quit, isFalse);
    });
  });
}
