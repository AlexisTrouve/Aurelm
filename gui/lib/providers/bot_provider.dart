import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/app_constants.dart';
import '../services/bot_service.dart';
import '../services/sync_service.dart';
import 'database_provider.dart';
import 'enrollment_provider.dart';

final botServiceProvider = Provider<BotService>((ref) {
  final service = BotService();
  ref.onDispose(() => service.dispose());
  return service;
});

final syncServiceProvider = Provider<SyncService>((ref) {
  return SyncService(port: AppConstants.botDefaultPort);
});

/// Auto-starts the bot on app launch if it's not already running.
///
/// Watch this provider from the root widget so it activates at startup.
/// Uses the configured DB path — no-op if no DB is selected yet.
/// Silent: failures are swallowed (bot may not be installed or path wrong).
final autoStartBotProvider = FutureProvider<void>((ref) async {
  final dbPath = ref.watch(dbPathProvider);
  if (dbPath == null) return; // No DB configured yet

  // Check if already running before spawning a process
  final syncService = ref.read(syncServiceProvider);
  final alreadyRunning = await syncService.healthCheck();
  if (alreadyRunning) return;

  // Secrets come from the OS-sealed store and are handed to the bot through its
  // environment — they never land in a file the bot reads. The key is null before
  // activation (agent stays disabled, /chat → 503); the Discord token is null when
  // the user skipped that step (bot runs HTTP-only, no gateway).
  final keyStore = ref.read(keyStoreProvider);
  final apiKey = await keyStore.readKey();
  final discordToken = await keyStore.readDiscordToken();

  // No interpreter hardcoded here: BotService detects a packaged bundle (its own
  // embedded Python) and falls back to the dev launcher otherwise. Passing
  // 'py -3.12' from here used to guarantee failure on a machine without Python.
  await ref.read(botServiceProvider).start(
    dbPath: dbPath,
    apiKey: apiKey,
    discordToken: discordToken,
  );
});

// Whether the bot HTTP server is reachable
final botHealthProvider = StreamProvider<bool>((ref) {
  final syncService = ref.watch(syncServiceProvider);
  return Stream.periodic(const Duration(seconds: 5), (_) async {
    return await syncService.healthCheck();
  }).asyncMap((future) => future);
});

// Sync state
enum SyncStatus { idle, syncing, success, error }

class SyncState {
  final SyncStatus status;
  final Map<String, dynamic>? result;
  final String? error;

  const SyncState({
    this.status = SyncStatus.idle,
    this.result,
    this.error,
  });

  SyncState copyWith({
    SyncStatus? status,
    Map<String, dynamic>? result,
    String? error,
  }) {
    return SyncState(
      status: status ?? this.status,
      result: result ?? this.result,
      error: error ?? this.error,
    );
  }
}

final syncStateProvider =
    StateNotifierProvider<SyncStateNotifier, SyncState>((ref) {
  final syncService = ref.watch(syncServiceProvider);
  return SyncStateNotifier(syncService);
});

class SyncStateNotifier extends StateNotifier<SyncState> {
  final SyncService _syncService;

  SyncStateNotifier(this._syncService) : super(const SyncState());

  Future<void> triggerSync() async {
    if (state.status == SyncStatus.syncing) return;
    state = state.copyWith(status: SyncStatus.syncing, error: null);
    try {
      await _syncService.triggerSync(); // returns 202 immediately
      state = state.copyWith(status: SyncStatus.success, result: {});
    } catch (e) {
      state = state.copyWith(status: SyncStatus.error, error: e.toString());
    }
  }
}
