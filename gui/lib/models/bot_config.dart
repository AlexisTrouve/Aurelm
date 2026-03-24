/// Mirror of aurelm_config.json for the bot configuration UI.

class ChannelConfig {
  final String channelId;
  final String civName;
  final String player;

  const ChannelConfig({
    required this.channelId,
    required this.civName,
    this.player = '',
  });

  factory ChannelConfig.fromMapEntry(String id, Map<String, dynamic> data) {
    return ChannelConfig(
      channelId: id,
      civName: data['civ_name'] as String? ?? '',
      player: data['player'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'civ_name': civName,
        if (player.isNotEmpty) 'player': player,
      };
}

class BotConfig {
  final int botPort;
  final String? proxy;
  final String? wikiDir;
  final List<String> gmAuthors;
  final List<String> gmDiscordIds; // Discord user IDs of GM accounts (immutable)
  final String llmProvider; // 'ollama' | 'claude_proxy' | 'openrouter'
  final String ollamaModel; // actually the selected model name regardless of provider
  final String? anthropicBaseUrl;
  final String anthropicApiKey;
  final String discordToken;
  final List<ChannelConfig> channels;

  const BotConfig({
    this.botPort = 8473,
    this.proxy,
    this.wikiDir,
    this.gmAuthors = const ['Arthur Ignatus'],
    this.gmDiscordIds = const [],
    this.llmProvider = 'ollama',
    this.ollamaModel = 'qwen3:14b',
    this.anthropicBaseUrl,
    this.anthropicApiKey = '',
    this.discordToken = '',
    this.channels = const [],
  });

  factory BotConfig.fromJson(Map<String, dynamic> json) {
    final channelsRaw = (json['channels'] as Map<String, dynamic>?) ?? {};
    return BotConfig(
      botPort: json['bot_port'] as int? ?? 8473,
      proxy: json['proxy'] as String?,
      wikiDir: json['wiki_dir'] as String?,
      gmAuthors:
          List<String>.from(json['gm_authors'] as List? ?? ['Arthur Ignatus']),
      gmDiscordIds:
          List<String>.from(json['gm_discord_ids'] as List? ?? []),
      llmProvider: json['llm_provider'] as String? ?? 'ollama',
      ollamaModel: json['ollama_model'] as String? ?? 'qwen3:14b',
      anthropicBaseUrl: json['anthropic_base_url'] as String?,
      anthropicApiKey: json['anthropic_api_key'] as String? ?? '',
      discordToken: json['discord_token'] as String? ?? '',
      channels: channelsRaw.entries
          .map((e) => ChannelConfig.fromMapEntry(
              e.key, e.value as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    final channelsMap = <String, dynamic>{};
    for (final ch in channels) {
      channelsMap[ch.channelId] = ch.toJson();
    }
    return {
      'bot_port': botPort,
      if (proxy != null) 'proxy': proxy,
      if (wikiDir != null) 'wiki_dir': wikiDir,
      'gm_authors': gmAuthors,
      if (gmDiscordIds.isNotEmpty) 'gm_discord_ids': gmDiscordIds,
      'llm_provider': llmProvider,
      'ollama_model': ollamaModel,
      if (anthropicBaseUrl != null) 'anthropic_base_url': anthropicBaseUrl,
      if (anthropicApiKey.isNotEmpty) 'anthropic_api_key': anthropicApiKey,
      if (discordToken.isNotEmpty) 'discord_token': discordToken,
      'channels': channelsMap,
    };
  }

  BotConfig copyWith({
    int? botPort,
    String? Function()? proxy,
    List<String>? gmAuthors,
    List<String>? gmDiscordIds,
    String? llmProvider,
    String? ollamaModel,
    String? Function()? anthropicBaseUrl,
    String? anthropicApiKey,
    String? discordToken,
    List<ChannelConfig>? channels,
  }) {
    return BotConfig(
      botPort: botPort ?? this.botPort,
      proxy: proxy != null ? proxy() : this.proxy,
      wikiDir: wikiDir,
      gmAuthors: gmAuthors ?? this.gmAuthors,
      gmDiscordIds: gmDiscordIds ?? this.gmDiscordIds,
      llmProvider: llmProvider ?? this.llmProvider,
      ollamaModel: ollamaModel ?? this.ollamaModel,
      anthropicBaseUrl:
          anthropicBaseUrl != null ? anthropicBaseUrl() : this.anthropicBaseUrl,
      anthropicApiKey: anthropicApiKey ?? this.anthropicApiKey,
      discordToken: discordToken ?? this.discordToken,
      channels: channels ?? this.channels,
    );
  }
}
