import 'dart:io';

import 'package:aurelm_gui/services/ollama_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:path/path.dart' as p;

/// The automatic Ollama runtime install (download → silent install → start) is the
/// piece a fresh machine (Arthur's) needs. The real download/installer can't run in a
/// unit test, so the service exposes seams (http client, run-process, reachability
/// probe, download dir) and these lock the orchestration + every failure path.
void main() {
  late Directory tmp;
  setUp(() => tmp = Directory.systemTemp.createTempSync('ollama_install_test'));
  tearDown(() => tmp.deleteSync(recursive: true));

  // A streaming mock that returns [status] and a 6-byte body in two chunks.
  http.Client Function() mkClient(int status) => () => MockClient.streaming(
        (req, body) async => http.StreamedResponse(
          Stream.fromIterable(<List<int>>[
            [1, 2, 3],
            [4, 5, 6]
          ]),
          status,
          contentLength: 6,
        ),
      );

  OllamaService mkSvc({
    int status = 200,
    Future<int> Function(String, List<String>)? run,
    Future<bool> Function()? probe,
  }) =>
      OllamaService(
        clientFactory: mkClient(status),
        runProcess: run ?? (_, __) async => 0,
        probeReachable: probe ?? () async => true,
        downloadDir: () => tmp,
      );

  Future<List<InstallProgress>> runInstall(OllamaService svc) => svc
      .installOllama(pollAttempts: 3, pollInterval: const Duration(milliseconds: 1))
      .toList();

  test('happy path: download (with fractions) → install → start → done', () async {
    final steps = await runInstall(mkSvc());
    final phases = steps.map((s) => s.phase).toList();

    expect(phases.first, InstallPhase.downloading);
    expect(phases, contains(InstallPhase.installing));
    expect(phases, contains(InstallPhase.starting));
    expect(phases.last, InstallPhase.done);

    // The download reported real fractions (3/6 then 6/6) from the content length.
    final fracs = steps
        .where((s) => s.phase == InstallPhase.downloading && s.fraction != null)
        .map((s) => s.fraction!)
        .toList();
    expect(fracs, containsAllInOrder(<double>[0.5, 1.0]));

    // The installer bytes were actually written to disk before running it.
    expect(File('${tmp.path}/OllamaSetup.exe').existsSync(), isTrue);
  });

  test('the recommended silent flags are passed to the installer', () async {
    List<String>? seen;
    await runInstall(mkSvc(run: (exe, args) async {
      seen = args;
      return 0;
    }));
    expect(seen, OllamaService.installerArgs);
    expect(seen, contains('/VERYSILENT'));
  });

  test('a failed download surfaces an error, never a silent success', () async {
    final steps = await runInstall(mkSvc(status: 404));
    expect(steps.last.phase, InstallPhase.error);
    expect(steps.last.error, contains('404'));
    // It never claims to have installed anything.
    expect(steps.map((s) => s.phase), isNot(contains(InstallPhase.done)));
  });

  test('a non-zero installer exit is an error', () async {
    final steps = await runInstall(mkSvc(run: (_, __) async => 2));
    expect(steps.last.phase, InstallPhase.error);
    expect(steps.last.error, contains('2'));
  });

  test('installed but never answering → error after the poll budget', () async {
    final steps = await runInstall(mkSvc(probe: () async => false));
    expect(steps.last.phase, InstallPhase.error);
    expect(steps.last.error, contains('ne répond pas'));
  });

  // --- Installed-but-stopped: START it, never re-download. ---------------------

  // Lays down (or not) the Ollama tray app under a fake LOCALAPPDATA, and builds a
  // service whose local-start seam records the exe it was asked to launch.
  ({OllamaService svc, List<String> started}) mkStartSvc({
    required bool installed,
    Future<bool> Function()? probe,
  }) {
    final started = <String>[];
    if (installed) {
      final ollamaDir = Directory(p.join(tmp.path, 'Programs', 'Ollama'))
        ..createSync(recursive: true);
      File(p.join(ollamaDir.path, 'ollama app.exe')).writeAsStringSync('x');
    }
    final svc = OllamaService(
      clientFactory: mkClient(200),
      startProcess: (exe) async => started.add(exe),
      probeReachable: probe ?? () async => true,
      localAppData: () => tmp.path,
    );
    return (svc: svc, started: started);
  }

  Future<List<InstallProgress>> runStart(OllamaService svc) => svc
      .startLocal(pollAttempts: 3, pollInterval: const Duration(milliseconds: 1))
      .toList();

  test('isInstalled reflects the presence of the Ollama tray app', () {
    expect(mkStartSvc(installed: false).svc.isInstalled, isFalse);
    expect(mkStartSvc(installed: true).svc.isInstalled, isTrue);
  });

  test('startLocal launches the installed app (no download) and reports done', () async {
    final t = mkStartSvc(installed: true);
    final steps = await runStart(t.svc);

    expect(steps.map((s) => s.phase),
        containsAllInOrder([InstallPhase.starting, InstallPhase.done]));
    // It never entered a download phase — starting is not re-installing.
    expect(steps.map((s) => s.phase), isNot(contains(InstallPhase.downloading)));
    expect(t.started.single, endsWith('ollama app.exe'));
  });

  test('startLocal on a machine without Ollama errors (does not pretend)', () async {
    final steps = await runStart(mkStartSvc(installed: false).svc);
    expect(steps.last.phase, InstallPhase.error);
    expect(steps.last.error, contains('pas installé'));
  });

  test('startLocal: started but never answering → error after the budget', () async {
    final steps = await runStart(mkStartSvc(installed: true, probe: () async => false).svc);
    expect(steps.last.phase, InstallPhase.error);
    expect(steps.last.error, contains('ne répond pas'));
  });
}
