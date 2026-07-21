// Unit tests for the packaged-vs-dev launcher resolution.
//
// WHY these exist: CI never launches the actual GUI EXE, so the code Arthur's
// machine runs to find + spawn the bot (resolveLauncherFor / isPackagedAt) would
// otherwise ship unproven. These simulate both layouts on disk and assert the
// decision — the half-present-install trap included.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;

import 'package:aurelm_gui/services/bot_service.dart';

void main() {
  late Directory tmp;

  setUp(() => tmp = Directory.systemTemp.createTempSync('aurelm_launcher'));
  tearDown(() => tmp.deleteSync(recursive: true));

  /// Build the packaged layout: <exeDir>/python/python.exe + <exeDir>/app.
  String _makePackaged() {
    final exeDir = Directory(p.join(tmp.path, 'install'))..createSync();
    Directory(p.join(exeDir.path, 'python')).createSync();
    File(p.join(exeDir.path, 'python', 'python.exe')).createSync();
    Directory(p.join(exeDir.path, 'app')).createSync();
    return exeDir.path;
  }

  group('resolveLauncherFor', () {
    // Separator-agnostic: the code builds paths with '/', valid on Windows but not
    // string-equal to p.join's backslashes.
    String norm(String s) => s.replaceAll('\\', '/');

    test('packaged layout → the bundled interpreter + app cwd', () {
      final exeDir = _makePackaged();
      final r = BotService.resolveLauncherFor(exeDir, p.join(tmp.path, 'db', 'aurelm.db'));

      expect(norm(r.executable), norm(p.join(exeDir, 'python', 'python.exe')));
      expect(r.leadingArgs, isEmpty);
      expect(norm(r.workingDir), norm(p.join(exeDir, 'app')));
    });

    test('no bundle → the dev launcher (py -3.12) + repo root cwd', () {
      // exeDir with neither python/ nor app/.
      final exeDir = Directory(p.join(tmp.path, 'devexe'))..createSync();
      // A repo-shaped tree: <root>/bot exists, DB sits under it.
      final root = Directory(p.join(tmp.path, 'repo'))..createSync();
      Directory(p.join(root.path, 'bot')).createSync();
      final dbPath = p.join(root.path, 'aurelm.db');

      final r = BotService.resolveLauncherFor(exeDir.path, dbPath);

      expect(r.executable, 'py');
      expect(r.leadingArgs, ['-3.12']);
      expect(r.workingDir, root.path);
    });

    test('half-present bundle (python but no app) falls back to dev, not a broken '
        'packaged launch', () {
      final exeDir = Directory(p.join(tmp.path, 'half'))..createSync();
      Directory(p.join(exeDir.path, 'python')).createSync();
      File(p.join(exeDir.path, 'python', 'python.exe')).createSync();
      // No app/ dir.

      final r = BotService.resolveLauncherFor(exeDir.path, p.join(tmp.path, 'x', 'a.db'));
      expect(r.executable, 'py', reason: 'must not try the bundled python without app/');
    });
  });

  group('isPackagedAt', () {
    test('true only when BOTH python.exe and app/ exist', () {
      expect(BotService.isPackagedAt(_makePackaged()), isTrue);

      final half = Directory(p.join(tmp.path, 'half2'))..createSync();
      Directory(p.join(half.path, 'python')).createSync();
      File(p.join(half.path, 'python', 'python.exe')).createSync();
      expect(BotService.isPackagedAt(half.path), isFalse,
          reason: 'python without app/ is not a usable bundle');

      final empty = Directory(p.join(tmp.path, 'empty'))..createSync();
      expect(BotService.isPackagedAt(empty.path), isFalse);
    });

    test('isPackagedAt agrees with resolveLauncherFor on the same dir', () {
      final exeDir = _makePackaged();
      final packaged = BotService.isPackagedAt(exeDir);
      final r = BotService.resolveLauncherFor(exeDir, p.join(tmp.path, 'a.db'));
      // If reported packaged, the launcher must use the bundled python (not `py`).
      expect(packaged && r.executable != 'py', isTrue);
    });
  });
}
