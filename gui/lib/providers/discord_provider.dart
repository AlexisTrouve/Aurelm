import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/discord_service.dart';
import 'database_provider.dart';
import 'enrollment_provider.dart';

/// Proxy for reaching Discord, or null for a direct connection.
///
/// Arthur connects directly and this stays null. It exists so a dev on a blocked
/// network — or the rare restricted user via Settings later — can route through one
/// without the wizard code caring.
final discordProxyProvider = StateProvider<String?>((ref) => null);

final discordServiceProvider = Provider<DiscordService>((ref) {
  return DiscordService(proxyUrl: ref.watch(discordProxyProvider));
});

/// One channel the user may bind to a civilization, with the display context we
/// keep so the app never has to show a raw channel ID again.
class MappableChannel {
  final String channelId;
  final String channelName;
  final String guildName;
  const MappableChannel({
    required this.channelId,
    required this.channelName,
    required this.guildName,
  });
}

enum DiscordStatus { idle, verifying, verified }

class DiscordConnectState {
  final DiscordStatus status;
  final DiscordVerifySuccess? result;
  final String? error;
  const DiscordConnectState({
    this.status = DiscordStatus.idle,
    this.result,
    this.error,
  });

  bool get isVerifying => status == DiscordStatus.verifying;

  /// The flat list of bindable text channels across every guild the bot is in.
  List<MappableChannel> get channels {
    final r = result;
    if (r == null) return const [];
    return [
      for (final g in r.guilds)
        for (final c in g.channels)
          MappableChannel(
            channelId: c.id,
            channelName: c.name,
            guildName: g.name,
          ),
    ];
  }
}

/// Drives the Discord step: verify a token, then persist the token + the channel→
/// civ mappings the user made.
///
/// COMMENT: the token is only sealed at [save], once the user commits the step —
/// re-verifying a different token beforehand shouldn't leave a stale secret behind.
/// Civs are written through the existing CivilizationDao (upsert by name), so the
/// bot's sync — which reads civ_civilizations WHERE discord_channel_id IS NOT NULL —
/// picks them up with no extra plumbing.
class DiscordConnectNotifier extends StateNotifier<DiscordConnectState> {
  final Ref _ref;
  DiscordConnectNotifier(this._ref) : super(const DiscordConnectState());

  Future<void> verify(String token) async {
    if (state.isVerifying) return;
    state = const DiscordConnectState(status: DiscordStatus.verifying);

    final result = await _ref.read(discordServiceProvider).verify(token);
    switch (result) {
      case DiscordVerifySuccess():
        state = DiscordConnectState(
          status: DiscordStatus.verified,
          result: result,
        );
      case DiscordVerifyError(:final failure):
        state = DiscordConnectState(
          status: DiscordStatus.idle,
          error: DiscordService.messageFor(failure),
        );
    }
  }

  void clearError() {
    if (state.error != null) state = const DiscordConnectState();
  }

  /// Seal [token] and write each mapping (channelId → civ name/player). Returns
  /// false if there's no database yet — step 2 must have run first.
  ///
  /// [mappings] is channelId → (civName, player). Only entries with a non-empty
  /// civ name are written; a channel the user left blank is simply not tracked.
  Future<bool> save({
    required String token,
    required Map<String, ({String civName, String player})> mappings,
  }) async {
    final db = _ref.read(databaseProvider);
    if (db == null) return false;

    await _ref.read(keyStoreProvider).writeDiscordToken(token.trim());

    final byId = {for (final c in state.channels) c.channelId: c};
    for (final entry in mappings.entries) {
      final civName = entry.value.civName.trim();
      if (civName.isEmpty) continue;
      final ch = byId[entry.key];
      await db.civilizationDao.createCiv(
        name: civName,
        playerName: entry.value.player.trim().isEmpty ? null : entry.value.player.trim(),
        discordChannelId: entry.key,
        discordGuildName: ch?.guildName,
        discordChannelName: ch?.channelName,
      );
    }
    return true;
  }
}

final discordConnectProvider =
    StateNotifierProvider<DiscordConnectNotifier, DiscordConnectState>((ref) {
  return DiscordConnectNotifier(ref);
});
