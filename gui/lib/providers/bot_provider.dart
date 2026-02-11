import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/app_constants.dart';
import '../services/bot_service.dart';
import '../services/sync_service.dart';

final botServiceProvider = Provider<BotService>((ref) {
  final service = BotService();
  ref.onDispose(() => service.dispose());
  return service;
});

final syncServiceProvider = Provider<SyncService>((ref) {
  return SyncService(port: AppConstants.botDefaultPort);
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
      final result = await _syncService.triggerSync();
      state = state.copyWith(status: SyncStatus.success, result: result);
    } catch (e) {
      state = state.copyWith(status: SyncStatus.error, error: e.toString());
    }
  }
}
