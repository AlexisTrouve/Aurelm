import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';

/// A text channel the bot can see in a guild.
class DiscordChannel {
  final String id;
  final String name;
  const DiscordChannel({required this.id, required this.name});
}

/// A guild the bot has been invited to, with its text channels.
class DiscordGuild {
  final String id;
  final String name;
  final List<DiscordChannel> channels;
  const DiscordGuild({required this.id, required this.name, required this.channels});
}

/// Why verifying a Discord token failed.
enum DiscordFailure {
  /// 401 — the token is wrong or was reset.
  invalidToken,

  /// Couldn't reach Discord (offline, or blocked without a proxy).
  network,

  /// Reachable but answered unexpectedly.
  server,
}

sealed class DiscordVerifyResult {}

class DiscordVerifySuccess extends DiscordVerifyResult {
  final String botName;
  final String applicationId;

  /// True when the Message Content intent is on. Without it the bot connects but
  /// reads empty message bodies — the single most common silent failure.
  final bool hasMessageContent;

  /// Guilds the bot is already in (empty → it needs inviting).
  final List<DiscordGuild> guilds;

  DiscordVerifySuccess({
    required this.botName,
    required this.applicationId,
    required this.hasMessageContent,
    required this.guilds,
  });
}

class DiscordVerifyError extends DiscordVerifyResult {
  final DiscordFailure failure;
  DiscordVerifyError(this.failure);
}

/// Talks to the Discord REST API to validate a bot token and enumerate the
/// servers/channels the bot can see — everything the setup wizard needs to map
/// channels to civilizations without the user ever handling a raw channel ID.
///
/// WHY a proxy is optional: Arthur reaches Discord directly and passes none. A dev
/// on a blocked network (or the rare restricted user) can route through one. The
/// shipped default is no proxy.
class DiscordService {
  static const _base = 'https://discord.com/api/v10';
  final String? proxyUrl;

  DiscordService({this.proxyUrl});

  /// Message Content lives in two application flag bits: 1<<18 when the intent is
  /// approved for a verified app, 1<<19 ("LIMITED") for an unverified app under
  /// 100 servers — which is Arthur's case. Checking only 1<<18, as the docs
  /// suggest, would wrongly report a working intent as disabled. Accept either.
  static const _messageContentBit = 1 << 18;
  static const _messageContentLimitedBit = 1 << 19;

  http.Client _client() {
    final proxy = proxyUrl;
    if (proxy == null || proxy.isEmpty) return http.Client();
    // Dart's HttpClient honours findProxy; the `http` package does not proxy on
    // its own, so wrap a configured HttpClient in an IOClient.
    final httpClient = HttpClient()..findProxy = (_) => 'PROXY ${_hostPort(proxy)}';
    return IOClient(httpClient);
  }

  static String _hostPort(String url) =>
      url.replaceFirst(RegExp(r'^https?://'), '').replaceAll(RegExp(r'/+$'), '');

  Future<Map<String, String>> _headers(String token) async => {
        'Authorization': 'Bot ${token.trim()}',
        'User-Agent': 'Aurelm (https://github.com/AlexisTrouve/Aurelm, 0.1)',
      };

  /// Validate [token] and gather the bot's identity, intent, guilds and channels.
  Future<DiscordVerifyResult> verify(String token) async {
    if (token.trim().isEmpty) return DiscordVerifyError(DiscordFailure.invalidToken);
    final client = _client();
    try {
      final headers = await _headers(token);

      // 1. Identity — a 401 here means the token itself is bad; stop early.
      final meResp = await client
          .get(Uri.parse('$_base/users/@me'), headers: headers)
          .timeout(const Duration(seconds: 20));
      if (meResp.statusCode == 401) {
        return DiscordVerifyError(DiscordFailure.invalidToken);
      }
      if (meResp.statusCode != 200) {
        return DiscordVerifyError(DiscordFailure.server);
      }
      final botName =
          (jsonDecode(meResp.body) as Map<String, dynamic>)['username'] as String? ?? '?';

      // 2. Application flags → Message Content intent.
      final appResp = await client
          .get(Uri.parse('$_base/applications/@me'), headers: headers)
          .timeout(const Duration(seconds: 20));
      final appJson = appResp.statusCode == 200
          ? jsonDecode(appResp.body) as Map<String, dynamic>
          : <String, dynamic>{};
      final flags = (appJson['flags'] as int?) ?? 0;
      final appId = appJson['id'] as String? ?? '';
      final hasMessageContent =
          flags & (_messageContentBit | _messageContentLimitedBit) != 0;

      // 3. Guilds + their text channels.
      final guildsResp = await client
          .get(Uri.parse('$_base/users/@me/guilds'), headers: headers)
          .timeout(const Duration(seconds: 20));
      final guilds = <DiscordGuild>[];
      if (guildsResp.statusCode == 200) {
        final raw = jsonDecode(guildsResp.body) as List;
        for (final g in raw.cast<Map<String, dynamic>>()) {
          final gid = g['id'] as String;
          final channels = await _channels(client, headers, gid);
          guilds.add(DiscordGuild(
            id: gid,
            name: g['name'] as String? ?? '?',
            channels: channels,
          ));
        }
      }

      return DiscordVerifySuccess(
        botName: botName,
        applicationId: appId,
        hasMessageContent: hasMessageContent,
        guilds: guilds,
      );
    } on TimeoutException {
      return DiscordVerifyError(DiscordFailure.network);
    } catch (_) {
      return DiscordVerifyError(DiscordFailure.network);
    } finally {
      client.close();
    }
  }

  /// Text channels (type 0) of a guild, best-effort — a guild we can't read just
  /// contributes no channels rather than failing the whole verification.
  Future<List<DiscordChannel>> _channels(
      http.Client client, Map<String, String> headers, String guildId) async {
    try {
      final resp = await client
          .get(Uri.parse('$_base/guilds/$guildId/channels'), headers: headers)
          .timeout(const Duration(seconds: 20));
      if (resp.statusCode != 200) return const [];
      final raw = jsonDecode(resp.body) as List;
      return [
        for (final c in raw.cast<Map<String, dynamic>>())
          if (c['type'] == 0)
            DiscordChannel(id: c['id'] as String, name: c['name'] as String? ?? '?'),
      ];
    } catch (_) {
      return const [];
    }
  }

  /// A one-click invite URL for a bot the user still has to add to their server.
  /// Permissions 66560 = View Channels (1024) + Read Message History (65536) —
  /// read-only, which is all Aurelm ever needs.
  static String inviteUrl(String applicationId) =>
      'https://discord.com/oauth2/authorize'
      '?client_id=$applicationId&scope=bot&permissions=66560';

  /// User-facing French message for a failure.
  static String messageFor(DiscordFailure failure) => switch (failure) {
        DiscordFailure.invalidToken =>
          'Token invalide. Vérifie que tu as bien copié le token du bot.',
        DiscordFailure.network =>
          'Impossible de joindre Discord. Vérifie ta connexion et réessaie.',
        DiscordFailure.server =>
          'Discord a répondu de façon inattendue. Réessaie dans un moment.',
      };
}
