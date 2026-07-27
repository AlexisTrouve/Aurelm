import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'sync_service.dart';

class BotService {
  Process? _process;
  final _logController = StreamController<String>.broadcast();
  bool _running = false;
  // Set synchronously at the top of start(). `_running` only flips true AFTER the
  // ~15s health wait, so without this a second start() in that window would see
  // "not running", spawn a duplicate bot fighting for port 8473, and orphan the
  // first process — with the secrets handed to both.
  bool _starting = false;

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
    // Guard synchronously, before any await, against a re-entrant start().
    if (_running || _starting) return _running;
    _starting = true;

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
    } finally {
      _starting = false;
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

  /// Walk up from [startDir] to the nearest ancestor holding a `bot/` package.
  /// Returns null if none is found before the filesystem root. Cap of 10 because
  /// the dev EXE is deep (`<repo>/gui/build/windows/x64/runner/Debug`).
  static String? _findBotRootFrom(String startDir) {
    var dir = Directory(startDir);
    for (var i = 0; i < 10; i++) {
      if (Directory('${dir.path}/bot').existsSync()) return dir.path;
      final parent = dir.parent;
      if (parent.path == dir.path) break; // reached the filesystem root
      dir = parent;
    }
    return null;
  }

  /// Walk up from the DB path to the project root (the nearest ancestor with a
  /// `bot/` dir). Static so resolveLauncherFor stays a pure, testable function.
  static String findProjectRoot(String dbPath) {
    final dbDir = Directory(dbPath).parent.path;
    return _findBotRootFrom(dbDir) ?? dbDir;
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
          String dbPath) =>
      resolveLauncherFor(File(Platform.resolvedExecutable).parent.path, dbPath);

  /// Pure launcher resolution, split out so CI can unit-test the packaged-vs-dev
  /// decision (P2: the GUI EXE is never launched in CI, so this logic would
  /// otherwise ship unproven). Given [exeDir] and [dbPath], pick the interpreter,
  /// its leading args, and the cwd.
  static ({String executable, List<String> leadingArgs, String workingDir})
      resolveLauncherFor(String exeDir, String dbPath) {
    final bundledPython = File('$exeDir/python/python.exe');
    final bundledApp = Directory('$exeDir/app');

    if (bundledPython.existsSync() && bundledApp.existsSync()) {
      return (
        executable: bundledPython.path,
        leadingArgs: const <String>[],
        workingDir: bundledApp.path,
      );
    }

    // Dev checkout: the Windows launcher picks the right interpreter. The bot
    // package lives in the repo — find the repo root from the EXE location first
    // (the GUI exe is nested inside `<repo>/gui/build/…`). WHY not from the DB:
    // the wizard's default DB is `Documents\Aurelm\aurelm.db`, OUTSIDE the repo, so
    // a DB-relative search finds no `bot/` and `py -m bot` dies with "No module
    // named bot" (the exact first-run crash). Fall back to a DB-relative search
    // (dev DBs kept inside the repo), then to the DB's own dir.
    final root = _findBotRootFrom(exeDir) ?? findProjectRoot(dbPath);
    return (
      executable: 'py',
      leadingArgs: const <String>['-3.12'],
      workingDir: root,
    );
  }

  /// True when [exeDir] holds a packaged bundle. Must match resolveLauncherFor's
  /// packaged test exactly (both python AND app), or a half-present install would
  /// report packaged while the launcher falls back to the dev `py` that isn't there.
  static bool isPackagedAt(String exeDir) =>
      File('$exeDir/python/python.exe').existsSync() &&
      Directory('$exeDir/app').existsSync();

  /// True when running from a packaged bundle rather than a dev checkout.
  static bool get isPackaged =>
      isPackagedAt(File(Platform.resolvedExecutable).parent.path);
}
