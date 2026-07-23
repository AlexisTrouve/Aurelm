// LIVE test against the REAL distribution host (dist.etheryale.com).
//
// The unit tests mock the network; this one proves the deployed server actually
// serves what the shipped client expects — manifest shape, headers, binary transfer
// and the integrity gate — including a deliberately hostile case.
//
// Opt-in, so the default suite stays offline and fast:
//   AURELM_LIVE_DIST=1 flutter test test/services/update_service_live_test.dart
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:aurelm_gui/services/update_service.dart';

const _probeUrl = 'https://dist.etheryale.com/aurelm/probe.bin';
const _probeSha = '0538f3754463412c9ad021c76ba8f7b53682d8080fb51b30e335ad9217de1a66';

void main() {
  final live = Platform.environment['AURELM_LIVE_DIST'] == '1';

  group('live distribution host', skip: live ? null : 'set AURELM_LIVE_DIST=1', () {
    late Directory dir;
    setUp(() => dir = Directory.systemTemp.createTempSync('aurelm_live'));
    tearDown(() {
      try {
        dir.deleteSync(recursive: true);
      } catch (_) {}
    });

    UpdateService svc() => UpdateService(tempDirProvider: () async => dir);

    test('serves a well-formed manifest the client can parse', () async {
      // An older client must be offered the published version.
      final info = await svc().check(currentVersion: '0.0.1');
      expect(info, isNotNull, reason: 'the real manifest must parse and compare');
      expect(info!.sha256, matches(RegExp(r'^[0-9a-f]{64}$')),
          reason: 'a published release must carry a full sha256');
      expect(info.url, startsWith('https://'),
          reason: 'the installer must be fetched over TLS');
    });

    test('the current version is not offered an update', () async {
      expect(await svc().check(currentVersion: '999.0.0'), isNull);
    });

    test('downloads a real file from the host and accepts a matching hash', () async {
      final file = await svc()
          .download(const UpdateInfo(version: '9.9.9', url: _probeUrl, sha256: _probeSha));
      expect(file.existsSync(), isTrue);
      expect(file.lengthSync(), greaterThan(0));
    });

    test('HOSTILE: a wrong hash is rejected and the file is not kept', () async {
      // Simulates a tampered/substituted binary on the wire. The client must refuse
      // it — this is the gate that stops us executing something we did not publish.
      await expectLater(
        svc().download(UpdateInfo(
            version: '9.9.9', url: _probeUrl, sha256: 'de' * 32)),
        throwsA(isA<UpdateIntegrityError>()),
      );
      expect(File('${dir.path}${Platform.pathSeparator}probe.bin').existsSync(), isFalse,
          reason: 'a rejected binary must not be left on disk');
    });
  });
}
