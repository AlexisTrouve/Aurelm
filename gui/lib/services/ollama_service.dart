import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:path/path.dart' as p;

/// One progress update while a model is downloading.
class PullProgress {
  /// Ollama's status text, e.g. "pulling manifest", "downloading …", "success".
  final String status;

  /// 0.0–1.0 during a download phase, or null when the phase has no byte counts
  /// (manifest, verifying) — the UI shows an indeterminate bar then.
  final double? fraction;

  /// True on the terminal success message.
  final bool done;

  /// Non-null if the pull failed (network, unknown model, Ollama down).
  final String? error;

  const PullProgress({
    required this.status,
    this.fraction,
    this.done = false,
    this.error,
  });
}

/// The phases of installing the Ollama runtime itself (distinct from pulling a model
/// into an already-running Ollama).
enum InstallPhase { downloading, installing, starting, done, error }

/// One progress update while INSTALLING Ollama (download → silent install → start).
class InstallProgress {
  final InstallPhase phase;

  /// 0.0–1.0 during the download when the server sends a content length, else null
  /// (the UI shows an indeterminate bar).
  final double? fraction;

  /// Non-null when [phase] is error.
  final String? error;

  const InstallProgress(this.phase, {this.fraction, this.error});
}

/// Drives model downloads (and, when needed, the Ollama runtime install itself)
/// through the locally running Ollama.
///
/// WHAT: `pull` streams `POST /api/pull` so the wizard shows a real progress bar;
/// `installOllama` downloads and silently installs the Ollama runtime when it is not
/// present (so a fresh machine — Arthur's — needs no manual step).
///
/// COMMENT: `/api/pull` emits one JSON object per line. Download phases carry
/// `total` + `completed` byte counts; other phases (manifest, verifying) don't, so
/// fraction is null there. The stream ends with `{"status":"success"}`.
class OllamaService {
  static const _base = 'http://localhost:11434';

  /// The official Windows installer. A stable URL that 302-redirects to the CDN;
  /// the http client follows redirects by default.
  static const installerUrl = 'https://ollama.com/download/OllamaSetup.exe';

  /// Silent-install flags. Isolated as a constant because the ONE thing this feature
  /// can't be validated for on a machine that already has Ollama is the exact silent
  /// switch — Ollama's recent installer is Inno-Setup-based, so /VERYSILENT applies.
  static const installerArgs = <String>[
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'
  ];

  final http.Client Function() _clientFactory;
  // Seams so the install flow is testable without the network or a real installer.
  final Future<int> Function(String exePath, List<String> args) _runProcess;
  final Future<bool> Function() _probeReachable;
  final Directory Function() _downloadDir;
  final Future<void> Function(String exePath) _startProcess;
  final String? Function() _localAppData;

  OllamaService({
    http.Client Function()? clientFactory,
    Future<int> Function(String, List<String>)? runProcess,
    Future<bool> Function()? probeReachable,
    Directory Function()? downloadDir,
    Future<void> Function(String)? startProcess,
    String? Function()? localAppData,
  })  : _clientFactory = clientFactory ?? http.Client.new,
        _runProcess = runProcess ?? _defaultRunProcess,
        _probeReachable = probeReachable ?? _defaultProbe,
        _downloadDir = downloadDir ?? (() => Directory.systemTemp),
        _startProcess = startProcess ?? _defaultStartProcess,
        _localAppData = localAppData ??
            (() => Platform.environment['LOCALAPPDATA']);

  static Future<int> _defaultRunProcess(String exe, List<String> args) async =>
      (await Process.run(exe, args)).exitCode;

  /// Launch DETACHED (not awaited): the Ollama tray app keeps running after we return.
  static Future<void> _defaultStartProcess(String exe) async {
    await Process.start(exe, const <String>[],
        mode: ProcessStartMode.detached);
  }

  static Future<bool> _defaultProbe() async {
    try {
      final r = await http.get(Uri.parse('$_base/api/tags'))
          .timeout(const Duration(seconds: 3));
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// Path to the installed Ollama tray app (Windows, per-user default), or null when
  /// Ollama is not installed. This is what distinguishes "installed but stopped" (just
  /// start it) from "absent" (download + install) — the wizard must not confuse them.
  String? installedExePath() {
    final base = _localAppData();
    if (base == null) return null;
    final exe = p.join(base, 'Programs', 'Ollama', 'ollama app.exe');
    return File(exe).existsSync() ? exe : null;
  }

  bool get isInstalled => installedExePath() != null;

  /// Start the ALREADY-INSTALLED Ollama and wait until it answers. Use when the binary
  /// is present but not running (e.g. after a reboot) — starting it is instant and
  /// beats telling the user to reinstall. Yields the same phases as install so the UI
  /// is uniform. Errors if Ollama isn't actually installed.
  Stream<InstallProgress> startLocal({
    int pollAttempts = 20,
    Duration pollInterval = const Duration(seconds: 1),
  }) async* {
    final exe = installedExePath();
    if (exe == null) {
      yield const InstallProgress(InstallPhase.error,
          error: 'Ollama n\'est pas installé.');
      return;
    }
    yield const InstallProgress(InstallPhase.starting);
    try {
      await _startProcess(exe);
    } catch (e) {
      yield InstallProgress(InstallPhase.error, error: 'Démarrage d\'Ollama: $e');
      return;
    }
    for (var i = 0; i < pollAttempts; i++) {
      if (await _probeReachable()) {
        yield const InstallProgress(InstallPhase.done);
        return;
      }
      await Future.delayed(pollInterval);
    }
    yield const InstallProgress(InstallPhase.error,
        error: 'Ollama démarré mais ne répond pas (localhost:11434).');
  }

  /// Download + silently install the Ollama runtime, then wait for it to answer.
  ///
  /// A ~700 MB download followed by an install and a service start: the wizard shows
  /// the phase (download fraction, then indeterminate) and offers a "later" escape.
  /// On [InstallPhase.done] the caller re-probes Ollama and proceeds to the model pull.
  ///
  /// [pollAttempts]/[pollInterval] bound the wait for Ollama to answer after install
  /// (defaults ~30s); tests pass small values.
  Stream<InstallProgress> installOllama({
    int pollAttempts = 30,
    Duration pollInterval = const Duration(seconds: 1),
  }) async* {
    final client = _clientFactory();
    String exePath;
    // -- 1. Download the installer, streaming so we can show real progress. --------
    try {
      yield const InstallProgress(InstallPhase.downloading, fraction: 0);
      final resp = await client
          .send(http.Request('GET', Uri.parse(installerUrl)))
          .timeout(const Duration(seconds: 60));
      if (resp.statusCode != 200) {
        yield InstallProgress(InstallPhase.error,
            error: 'Téléchargement d\'Ollama échoué (HTTP ${resp.statusCode}).');
        return;
      }
      final total = resp.contentLength;
      final file = File(p.join(_downloadDir().path, 'OllamaSetup.exe'));
      final sink = file.openWrite();
      var received = 0;
      await for (final chunk in resp.stream) {
        sink.add(chunk);
        received += chunk.length;
        yield InstallProgress(InstallPhase.downloading,
            fraction: (total != null && total > 0) ? received / total : null);
      }
      await sink.close();
      exePath = file.path;
    } on TimeoutException {
      yield const InstallProgress(InstallPhase.error,
          error: 'Téléchargement d\'Ollama: le serveur ne répond pas.');
      return;
    } catch (e) {
      yield InstallProgress(InstallPhase.error,
          error: 'Téléchargement d\'Ollama: $e');
      return;
    } finally {
      client.close();
    }

    // -- 2. Run the installer silently (blocks until it finishes). -----------------
    yield const InstallProgress(InstallPhase.installing);
    final int code;
    try {
      code = await _runProcess(exePath, installerArgs);
    } catch (e) {
      yield InstallProgress(InstallPhase.error, error: 'Installation d\'Ollama: $e');
      return;
    }
    if (code != 0) {
      yield InstallProgress(InstallPhase.error,
          error: 'Installation d\'Ollama a échoué (code $code).');
      return;
    }

    // -- 3. Ollama auto-starts after install; wait until it answers. ----------------
    yield const InstallProgress(InstallPhase.starting);
    for (var i = 0; i < pollAttempts; i++) {
      if (await _probeReachable()) {
        yield const InstallProgress(InstallPhase.done);
        return;
      }
      await Future.delayed(pollInterval);
    }
    yield const InstallProgress(InstallPhase.error,
        error: 'Ollama installé mais ne répond pas (localhost:11434).');
  }

  /// Pull [model] (e.g. `qwen3:14b`), yielding progress until done or error.
  ///
  /// A 9 GB pull can take many minutes; the caller keeps the wizard responsive and
  /// offers a "do it later" escape rather than blocking on completion.
  Stream<PullProgress> pull(String model) async* {
    final client = _clientFactory();
    try {
      final req = http.Request('POST', Uri.parse('$_base/api/pull'))
        ..headers['Content-Type'] = 'application/json'
        ..body = jsonEncode({'name': model, 'stream': true});

      final resp = await client.send(req).timeout(const Duration(seconds: 30));
      if (resp.statusCode != 200) {
        yield PullProgress(status: 'error', error: 'HTTP ${resp.statusCode}');
        return;
      }

      await for (final line in resp.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())) {
        if (line.trim().isEmpty) continue;
        Map<String, dynamic> obj;
        try {
          obj = jsonDecode(line) as Map<String, dynamic>;
        } catch (_) {
          continue; // skip a malformed line rather than abort the download
        }

        if (obj['error'] != null) {
          yield PullProgress(status: 'error', error: obj['error'].toString());
          return;
        }

        final status = obj['status'] as String? ?? '';
        final total = (obj['total'] as num?)?.toDouble();
        final completed = (obj['completed'] as num?)?.toDouble();
        final fraction = (total != null && total > 0 && completed != null)
            ? (completed / total).clamp(0.0, 1.0)
            : null;

        final done = status == 'success';
        yield PullProgress(status: status, fraction: fraction, done: done);
        if (done) return;
      }
    } on TimeoutException {
      yield const PullProgress(
          status: 'error', error: 'Ollama ne répond pas (localhost:11434).');
    } catch (e) {
      yield PullProgress(status: 'error', error: e.toString());
    } finally {
      client.close();
    }
  }
}
