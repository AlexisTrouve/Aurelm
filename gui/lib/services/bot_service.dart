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
    String pythonPath = 'python',
  }) async {
    if (_running) return true;

    try {
      _process = await Process.start(
        pythonPath,
        ['-m', 'bot', '--db', dbPath, '--port', '$port'],
        workingDirectory: _findProjectRoot(dbPath),
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
}
