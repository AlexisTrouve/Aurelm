import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:window_manager/window_manager.dart';

import 'app.dart';
import 'providers/database_provider.dart';

/// Log file path — read by Claude to diagnose crashes without screenshots.
final _logFile = File(r'C:\Users\alexi\Documents\projects\Aurelm\flutter_errors.log');

void _log(String msg) {
  final line = '[${DateTime.now().toIso8601String()}] $msg\n';
  _logFile.writeAsStringSync(line, mode: FileMode.append, flush: true);
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Always create/reset log on launch — exists even if no errors.
  _logFile.writeAsStringSync('[${DateTime.now().toIso8601String()}] APP STARTED\n', flush: true);

  // Catch Flutter framework errors (build exceptions, layout errors, etc.)
  // and write them to the log file + show in-widget instead of generic "something went wrong".
  FlutterError.onError = (FlutterErrorDetails details) {
    _log('FLUTTER ERROR:\n${details.exceptionAsString()}\n${details.stack}');
    FlutterError.presentError(details); // still prints to console
  };

  // Show real error + stack in red box instead of "An error occurred" gray box.
  ErrorWidget.builder = (FlutterErrorDetails details) {
    _log('BUILD ERROR:\n${details.exceptionAsString()}\n${details.stack}');
    return SingleChildScrollView(
      padding: const EdgeInsets.all(12),
      child: SelectableText(
        'BUILD ERROR:\n${details.exceptionAsString()}\n\n${details.stack}',
        style: const TextStyle(fontSize: 11, color: Colors.red, fontFamily: 'monospace'),
      ),
    );
  };

  await windowManager.ensureInitialized();
  const windowOptions = WindowOptions(
    size: Size(1280, 800),
    minimumSize: Size(900, 600),
    center: true,
    title: 'Aurelm — GM Dashboard',
    backgroundColor: Colors.transparent,
  );
  windowManager.waitUntilReadyToShow(windowOptions, () async {
    await windowManager.show();
    await windowManager.focus();
  });

  final prefs = await SharedPreferences.getInstance();

  runApp(
    ProviderScope(
      overrides: [
        sharedPrefsProvider.overrideWithValue(prefs),
      ],
      // Catches all Riverpod provider errors (DB queries, streams, etc.)
      observers: [_ErrorLogger()],
      child: const AurelmApp(),
    ),
  );
}

/// Riverpod observer — logs every provider error to flutter_errors.log.
/// This catches SQLite errors, stream failures, async provider crashes.
class _ErrorLogger extends ProviderObserver {
  @override
  void providerDidFail(
    ProviderBase<Object?> provider,
    Object error,
    StackTrace stackTrace,
    ProviderContainer container,
  ) {
    _log('PROVIDER ERROR [${provider.name ?? provider.runtimeType}]:\n$error\n$stackTrace');
  }
}
