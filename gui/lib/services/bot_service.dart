import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'sync_service.dart';

class BotService {
  Process? _process;
  final _logController = StreamController<String>.broadcast();
  bool _running = false;

  Stream<String> get logStream => _logController.stream;
  bool get isRunning => _running;

  Future<bool> start({
    required String dbPath,
    int port = 8473,
    // Interpreter overrides. Normally null: [_resolveLauncher] picks the bundled
    // interpreter when packaged and the dev one otherwise, so callers don't have
    // to know which environment they're in.
    String? pythonPath,
    List<String>? pythonArgs,
    // Secrets read from the OS-sealed KeyStore by the caller.
    String? apiKey,
    String? discordToken,
    String? openRouterKey,
  }) async {
    if (_running) return true;

    try {
      final launcher = _resolveLauncher(dbPath);
      final executable = pythonPath ?? launcher.executable;
      final leadingArgs = pythonArgs ?? launcher.leadingArgs;
      _logController.add('[BOT] launching via $executable (cwd ${launcher.workingDir})');

      // Hand secrets to the bot through the environment instead of a file.
      // config.py reads ETHERYALE_API_KEY and DISCORD_BOT_TOKEN from the env first,
      // so the Python side needs no change and never touches secure storage: a
      // secret exists sealed (DPAPI) or in this child's memory, never in plaintext
      // on disk. Passing null skips the whole map so Dart still inherits the parent
      // environment (PATH etc.); a partial map would replace it, so build one map.
      final env = <String, String>{};
      if (apiKey != null && apiKey.isNotEmpty) env['ETHERYALE_API_KEY'] = apiKey;
      if (discordToken != null && discordToken.isNotEmpty) {
        env['DISCORD_BOT_TOKEN'] = discordToken;
      }
      if (openRouterKey != null && openRouterKey.isNotEmpty) {
        env['OPENROUTER_API_KEY'] = openRouterKey;
      }

      _process = await Process.start(
        executable,
        [...leadingArgs, '-m', 'bot', '--db', dbPath, '--port', '$port'],
        workingDirectory: launcher.workingDir,
        // Dart merges this with the parent environment by default
        // (includeParentEnvironment: true), so PATH etc. are preserved.
        environment: env.isEmpty ? null : env,
      );

      _process!.stdout
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen((line) => _logController.add('[BOT] $line'));

      _process!.stderr
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen((line) => _logController.add('[BOT ERR] $line'));

      _process!.exitCode.then((code) {
        _running = false;
        _logController.add('[BOT] Process exited with code $code');
      });

      // Wait for the HTTP server to be ready
      final syncService = SyncService(port: port);
      for (var i = 0; i < 30; i++) {
        await Future.delayed(const Duration(milliseconds: 500));
        if (await syncService.healthCheck()) {
          _running = true;
          return true;
        }
      }

      // Timeout waiting for health check
      stop();
      return false;
    } catch (e) {
      _logController.add('[BOT] Failed to start: $e');
      return false;
    }
  }

  void stop() {
    _process?.kill();
    _process = null;
    _running = false;
  }

  void dispose() {
    stop();
    _logController.close();
  }

  /// Create + migrate the database, then return — no server, no Discord.
  ///
  /// WHY the wizard needs this: Flutter's Drift layer only creates a handful of its
  /// own tables; the ~35 core tables are built by the bot's SQL migrations. Opening
  /// a fresh DB in the app before those run leaves every civ/entity query failing.
  /// This runs `-m bot --migrate-only` and awaits a clean exit, so the wizard can
  /// guarantee a complete schema before pointing the app at the file.
  Future<bool> migrate({required String dbPath}) async {
    final launcher = _resolveLauncher(dbPath);
    try {
      final result = await Process.run(
        launcher.executable,
        [...launcher.leadingArgs, '-m', 'bot', '--db', dbPath, '--migrate-only'],
        workingDirectory: launcher.workingDir,
      );
      if (result.exitCode != 0) {
        _logController.add('[MIGRATE] failed (${result.exitCode}): ${result.stderr}');
        return false;
      }
      return true;
    } catch (e) {
      _logController.add('[MIGRATE] could not launch: $e');
      return false;
    }
  }

  String _findProjectRoot(String dbPath) {
    // Walk up from DB path to find the project root (contains bot/ directory)
    var dir = Directory(dbPath).parent;
    for (var i = 0; i < 5; i++) {
      if (Directory('${dir.path}/bot').existsSync()) {
        return dir.path;
      }
      dir = dir.parent;
    }
    return Directory(dbPath).parent.path;
  }

  /// How to launch the bot: the interpreter, its leading args, and the cwd.
  ///
  /// WHY this exists: a packaged install has no system Python and no repo layout,
  /// while a dev checkout has both and no bundle. Detecting which one we're in
  /// here keeps that knowledge in one place instead of leaking `py -3.12` into
  /// callers (where it was hardcoded, and would silently fail on a user machine).
  ///
  /// COMMENT: the packaged layout is `<exe dir>/python/python.exe` +
  /// `<exe dir>/app/{bot,pipeline}`, produced by scripts/build_distribution.ps1.
  /// The bundle resolves its own imports through `python312._pth`, so the cwd is
  /// not what makes `-m bot` work there — we still point it at `app/` so relative
  /// paths and logs land somewhere sensible.
  ({String executable, List<String> leadingArgs, String workingDir}) _resolveLauncher(
      String dbPath) {
    final exeDir = File(Platform.resolvedExecutable).parent.path;
    final bundledPython = File('$exeDir/python/python.exe');
    final bundledApp = Directory('$exeDir/app');

    if (bundledPython.existsSync() && bundledApp.existsSync()) {
      return (
        executable: bundledPython.path,
        leadingArgs: const <String>[],
        workingDir: bundledApp.path,
      );
    }

    // Dev checkout: the Windows launcher picks the right interpreter, and the
    // sources live next to the database.
    return (
      executable: 'py',
      leadingArgs: const <String>['-3.12'],
      workingDir: _findProjectRoot(dbPath),
    );
  }

  /// True when running from a packaged bundle rather than a dev checkout.
  static bool get isPackaged {
    final exeDir = File(Platform.resolvedExecutable).parent.path;
    return File('$exeDir/python/python.exe').existsSync();
  }
}
