/// Provider for bot configuration (aurelm_config.json).
/// Reloads automatically when the DB path changes.

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/bot_config.dart';
import '../services/bot_config_service.dart';
import 'database_provider.dart';

class BotConfigNotifier extends StateNotifier<AsyncValue<BotConfig>> {
  final String? _dbPath;

  BotConfigNotifier(this._dbPath) : super(const AsyncValue.loading()) {
    _load();
  }

  Future<void> _load() async {
    if (_dbPath == null) {
      state = const AsyncValue.data(BotConfig());
      return;
    }
    try {
      final config = await BotConfigService.load(_dbPath);
      state = AsyncValue.data(config);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  /// Save config to disk and update in-memory state.
  Future<void> save(BotConfig config) async {
    if (_dbPath == null) return;
    await BotConfigService.save(_dbPath, config);
    state = AsyncValue.data(config);
  }
}

final botConfigProvider =
    StateNotifierProvider<BotConfigNotifier, AsyncValue<BotConfig>>((ref) {
  final dbPath = ref.watch(dbPathProvider);
  return BotConfigNotifier(dbPath);
});
