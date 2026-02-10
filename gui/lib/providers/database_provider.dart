import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/constants/app_constants.dart';
import '../data/database.dart';

const _dbPathPrefKey = 'aurelm_db_path';

final sharedPrefsProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('Override in main with SharedPreferences.getInstance()');
});

final dbPathProvider = StateNotifierProvider<DbPathNotifier, String?>((ref) {
  final prefs = ref.watch(sharedPrefsProvider);
  return DbPathNotifier(prefs);
});

class DbPathNotifier extends StateNotifier<String?> {
  final SharedPreferences _prefs;

  DbPathNotifier(this._prefs) : super(null) {
    _init();
  }

  void _init() {
    // Check env var first
    final envPath = Platform.environment[AppConstants.envDbPathKey];
    if (envPath != null && File(envPath).existsSync()) {
      state = envPath;
      return;
    }
    // Fallback to saved preference
    final savedPath = _prefs.getString(_dbPathPrefKey);
    if (savedPath != null && File(savedPath).existsSync()) {
      state = savedPath;
    }
  }

  void setPath(String path) {
    state = path;
    _prefs.setString(_dbPathPrefKey, path);
  }
}

final databaseProvider = Provider<AurelmDatabase?>((ref) {
  final dbPath = ref.watch(dbPathProvider);
  if (dbPath == null) return null;

  final db = AurelmDatabase.open(dbPath);
  ref.onDispose(() => db.close());
  return db;
});
