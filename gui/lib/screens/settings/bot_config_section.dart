/// Bot & Discord configuration section for the settings screen.
/// Reads/writes aurelm_config.json and allows channel → civ mapping.

import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/database.dart';
import '../../models/bot_config.dart';
import '../../providers/bot_config_provider.dart';
import '../../providers/database_provider.dart';
import '../../services/bot_config_service.dart';

class BotConfigSection extends ConsumerStatefulWidget {
  const BotConfigSection({super.key});

  @override
  ConsumerState<BotConfigSection> createState() => _BotConfigSectionState();
}

class _BotConfigSectionState extends ConsumerState<BotConfigSection> {
  final _discordTokenCtrl = TextEditingController();
  final _anthropicKeyCtrl = TextEditingController();
  final _botPortCtrl = TextEditingController();

  bool _showToken = false;
  bool _showApiKey = false;
  bool _initialized = false;
  bool _saving = false;

  // LLM provider + model
  String _llmProvider = 'ollama';
  String _selectedModel = 'qwen3:14b';
  List<String> _ollamaModels = [];
  bool _loadingModels = false;

  // Mutable working copy of channels
  List<_ChannelEntry> _channels = [];

  // Discord channels fetched from the running bot
  List<Map<String, dynamic>>? _discordChannels;
  bool _fetchingChannels = false;

  @override
  void initState() {
    super.initState();
    _detectOllamaModels();
  }

  Future<void> _detectOllamaModels() async {
    setState(() => _loadingModels = true);
    _ollamaModels = await BotConfigService.fetchOllamaModels();
    if (mounted) setState(() => _loadingModels = false);
  }

  @override
  void dispose() {
    _discordTokenCtrl.dispose();
    _anthropicKeyCtrl.dispose();
    _botPortCtrl.dispose();
    super.dispose();
  }

  /// Populate controllers from loaded config (once).
  void _syncFromConfig(BotConfig cfg) {
    if (_initialized) return;
    _initialized = true;
    _discordTokenCtrl.text = cfg.discordToken;
    _anthropicKeyCtrl.text = cfg.anthropicApiKey;
    _llmProvider = cfg.llmProvider;
    _selectedModel = cfg.ollamaModel;
    _botPortCtrl.text = cfg.botPort.toString();
    _channels = cfg.channels
        .map((c) => _ChannelEntry(c.channelId, c.civName, c.player))
        .toList();
  }

  /// Build a BotConfig from the current form state.
  BotConfig _buildConfig(BotConfig base) {
    return base.copyWith(
      botPort: int.tryParse(_botPortCtrl.text.trim()) ?? base.botPort,
      discordToken: _discordTokenCtrl.text.trim(),
      anthropicApiKey: _anthropicKeyCtrl.text.trim(),
      llmProvider: _llmProvider,
      ollamaModel: _selectedModel,
      channels: _channels
          .where((c) => c.channelId.isNotEmpty && c.civName.isNotEmpty)
          .map((c) => ChannelConfig(
                channelId: c.channelId,
                civName: c.civName,
                player: c.player,
              ))
          .toList(),
    );
  }

  Future<void> _save(BotConfig base) async {
    setState(() => _saving = true);
    try {
      await ref.read(botConfigProvider.notifier).save(_buildConfig(base));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Config saved')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  /// Decode the bot's application ID from the Discord token (base64 first segment).
  String? _appIdFromToken(String token) {
    final parts = token.split('.');
    if (parts.length < 3) return null;
    try {
      // Discord token first segment = base64-encoded user/bot ID
      final padded = base64.normalize(parts[0]);
      return utf8.decode(base64.decode(padded));
    } catch (_) {
      return null;
    }
  }

  void _openInviteUrl() {
    final appId = _appIdFromToken(_discordTokenCtrl.text.trim());
    if (appId == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Token invalide - impossible de generer le lien')));
      return;
    }
    // Bot permissions: read messages, send messages, read message history
    const perms = 68608;
    final url =
        'https://discord.com/api/oauth2/authorize?client_id=$appId&permissions=$perms&scope=bot';
    Process.run('cmd', ['/c', 'start', url]);
  }

  Future<void> _fetchChannels() async {
    setState(() => _fetchingChannels = true);
    final port = int.tryParse(_botPortCtrl.text.trim()) ?? 8473;
    final channels = await BotConfigService.fetchDiscordChannels(port: port);
    setState(() {
      _discordChannels = channels;
      _fetchingChannels = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final configAsync = ref.watch(botConfigProvider);
    final db = ref.read(databaseProvider);

    return configAsync.when(
      loading: () => const Card(
          child: Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: CircularProgressIndicator()))),
      error: (e, _) => Card(
          child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text('Config error: $e'))),
      data: (cfg) {
        _syncFromConfig(cfg);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSecretsCard(context),
            const SizedBox(height: 12),
            _buildChannelsCard(context, db),
            const SizedBox(height: 12),
            _buildSettingsCard(context),
            const SizedBox(height: 12),
            // Save button
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.icon(
                onPressed: _saving ? null : () => _save(cfg),
                icon: _saving
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.save),
                label: const Text('Sauvegarder'),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildSecretsCard(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Connexion', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 12),
            // Discord token
            _secretField('Discord Bot Token', _discordTokenCtrl, _showToken,
                () => setState(() => _showToken = !_showToken)),
            const SizedBox(height: 8),
            // Invite button
            OutlinedButton.icon(
              onPressed: _discordTokenCtrl.text.trim().isEmpty
                  ? null
                  : _openInviteUrl,
              icon: const Icon(Icons.open_in_new, size: 16),
              label: const Text('Inviter le bot sur Discord'),
            ),
            const SizedBox(height: 16),
            // Anthropic API key
            _secretField('Anthropic API Key', _anthropicKeyCtrl, _showApiKey,
                () => setState(() => _showApiKey = !_showApiKey)),
          ],
        ),
      ),
    );
  }

  Widget _secretField(String label, TextEditingController ctrl, bool visible,
      VoidCallback onToggle) {
    return TextField(
      controller: ctrl,
      obscureText: !visible,
      decoration: InputDecoration(
        labelText: label,
        isDense: true,
        border: const OutlineInputBorder(),
        suffixIcon: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: Icon(visible ? Icons.visibility_off : Icons.visibility,
                  size: 18),
              onPressed: onToggle,
            ),
            IconButton(
              icon: const Icon(Icons.copy, size: 18),
              tooltip: 'Copier',
              onPressed: () =>
                  Clipboard.setData(ClipboardData(text: ctrl.text)),
            ),
          ],
        ),
      ),
      style: const TextStyle(fontSize: 13, fontFamily: 'monospace'),
    );
  }

  Widget _buildChannelsCard(BuildContext context, AurelmDatabase? db) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text('Channels Discord',
                    style: Theme.of(context).textTheme.titleSmall),
                const Spacer(),
                // Fetch channels from running bot
                TextButton.icon(
                  onPressed: _fetchingChannels ? null : _fetchChannels,
                  icon: _fetchingChannels
                      ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.refresh, size: 16),
                  label: const Text('Charger depuis Discord'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            // Channel rows
            ..._channels.asMap().entries.map((entry) =>
                _buildChannelRow(entry.key, entry.value, db)),
            const SizedBox(height: 8),
            // Add from fetched Discord channels or manually
            Row(
              children: [
                if (_discordChannels != null && _discordChannels!.isNotEmpty)
                  Expanded(child: _buildAddFromDiscord()),
                if (_discordChannels != null && _discordChannels!.isNotEmpty)
                  const SizedBox(width: 8),
                TextButton.icon(
                  onPressed: () {
                    setState(() =>
                        _channels.add(_ChannelEntry('', '', '')));
                  },
                  icon: const Icon(Icons.add, size: 16),
                  label: const Text('Ajouter manuellement'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChannelRow(int index, _ChannelEntry entry, AurelmDatabase? db) {
    // Find Discord channel name if available
    final discordName = _discordChannels
        ?.where((c) => c['id'] == entry.channelId)
        .firstOrNull?['name'];
    final label = discordName != null
        ? '#$discordName'
        : (entry.channelId.isNotEmpty
            ? 'ID: ${entry.channelId}'
            : 'Nouveau...');

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          // Channel identifier
          SizedBox(
            width: 160,
            child: Text(label,
                style: const TextStyle(fontSize: 12),
                overflow: TextOverflow.ellipsis),
          ),
          const Icon(Icons.arrow_forward, size: 14),
          const SizedBox(width: 8),
          // Civ name
          SizedBox(
            width: 140,
            child: TextField(
              controller: TextEditingController(text: entry.civName),
              decoration: const InputDecoration(
                hintText: 'Civilisation',
                isDense: true,
                border: OutlineInputBorder(),
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              ),
              style: const TextStyle(fontSize: 12),
              onChanged: (v) => entry.civName = v,
            ),
          ),
          const SizedBox(width: 8),
          // Player name
          SizedBox(
            width: 120,
            child: TextField(
              controller: TextEditingController(text: entry.player),
              decoration: const InputDecoration(
                hintText: 'Joueur',
                isDense: true,
                border: OutlineInputBorder(),
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              ),
              style: const TextStyle(fontSize: 12),
              onChanged: (v) => entry.player = v,
            ),
          ),
          const SizedBox(width: 4),
          // Create civ in DB button
          IconButton(
            icon: const Icon(Icons.group_add, size: 16),
            tooltip: 'Creer cette civ en base',
            onPressed: entry.civName.isEmpty || db == null
                ? null
                : () => _createCivFromChannel(entry, db),
          ),
          // Remove
          IconButton(
            icon: const Icon(Icons.remove_circle_outline,
                size: 16, color: Colors.red),
            tooltip: 'Retirer',
            onPressed: () => setState(() => _channels.removeAt(index)),
          ),
        ],
      ),
    );
  }

  /// Dropdown to pick from Discord channels fetched from the running bot.
  Widget _buildAddFromDiscord() {
    // Filter out channels already bound
    final boundIds = _channels.map((c) => c.channelId).toSet();
    final available = _discordChannels!
        .where((c) => !boundIds.contains(c['id']))
        .toList();

    if (available.isEmpty) {
      return const Text('Tous les channels sont lies',
          style: TextStyle(fontSize: 11, color: Colors.grey));
    }

    return DropdownButton<String>(
      hint: const Text('Ajouter un channel...', style: TextStyle(fontSize: 12)),
      isExpanded: true,
      items: available
          .map((c) => DropdownMenuItem(
                value: c['id'] as String,
                child: Text(
                  '#${c['name']} (${c['guild_name']})',
                  style: const TextStyle(fontSize: 12),
                ),
              ))
          .toList(),
      onChanged: (channelId) {
        if (channelId == null) return;
        setState(() => _channels.add(_ChannelEntry(channelId, '', '')));
      },
    );
  }

  /// Create a new civ in the DB linked to this channel.
  Future<void> _createCivFromChannel(
      _ChannelEntry entry, AurelmDatabase db) async {
    try {
      await db.civilizationDao.createCiv(
        name: entry.civName.trim(),
        playerName: entry.player.trim().isEmpty ? null : entry.player.trim(),
        discordChannelId: entry.channelId,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('Civ "${entry.civName}" creee')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Erreur: $e')));
      }
    }
  }

  Widget _buildLlmSelector(BuildContext context) {
    // Models for the current provider
    final List<String> models;
    final String recommended;
    switch (_llmProvider) {
      case 'ollama':
        models = _ollamaModels;
        recommended = 'qwen3:14b';
      case 'claude_proxy':
        models = _claudeProxyModels.toList();
        recommended = 'claude-haiku-4-5-20251001';
      case 'openrouter':
        models = _openrouterModels.toList();
        recommended = 'qwen/qwen3-14b';
      default:
        models = [];
        recommended = '';
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Provider tabs
        SegmentedButton<String>(
          segments: const [
            ButtonSegment(value: 'ollama', label: Text('Ollama')),
            ButtonSegment(value: 'claude_proxy', label: Text('Claude Proxy')),
            ButtonSegment(value: 'openrouter', label: Text('OpenRouter')),
          ],
          selected: {_llmProvider},
          onSelectionChanged: (sel) {
            setState(() {
              _llmProvider = sel.first;
              // Auto-select recommended model for provider
              _selectedModel = recommended;
            });
          },
        ),
        const SizedBox(height: 8),
        // Model dropdown
        if (_llmProvider == 'ollama' && _loadingModels)
          const Padding(
            padding: EdgeInsets.all(8),
            child: Row(children: [
              SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2)),
              SizedBox(width: 8),
              Text('Detection des modeles Ollama...',
                  style: TextStyle(fontSize: 12)),
            ]),
          )
        else if (_llmProvider == 'ollama' && models.isEmpty)
          Padding(
            padding: const EdgeInsets.all(8),
            child: Row(children: [
              const Icon(Icons.warning_amber, size: 16, color: Colors.orange),
              const SizedBox(width: 8),
              const Expanded(
                child: Text('Ollama non detecte ou aucun modele installe.',
                    style: TextStyle(fontSize: 12)),
              ),
              TextButton(
                onPressed: _detectOllamaModels,
                child: const Text('Reessayer'),
              ),
            ]),
          )
        else
          DropdownButtonFormField<String>(
            value: models.contains(_selectedModel) ? _selectedModel : null,
            decoration: InputDecoration(
              labelText: 'Modele',
              isDense: true,
              border: const OutlineInputBorder(),
              helperText: 'Recommande: $recommended',
              helperStyle: const TextStyle(fontSize: 11),
            ),
            items: models
                .map((m) => DropdownMenuItem(
                      value: m,
                      child: Text(m, style: const TextStyle(fontSize: 13)),
                    ))
                .toList(),
            onChanged: (v) {
              if (v != null) setState(() => _selectedModel = v);
            },
          ),
      ],
    );
  }

  Widget _buildSettingsCard(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Parametres', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 12),
            // Bot port
            SizedBox(
              width: 120,
              child: TextField(
                controller: _botPortCtrl,
                decoration: const InputDecoration(
                  labelText: 'Bot Port',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
                style: const TextStyle(fontSize: 13),
                keyboardType: TextInputType.number,
              ),
            ),
            const SizedBox(height: 16),
            // LLM Provider + Model
            Text('LLM Provider',
                style: Theme.of(context).textTheme.labelMedium),
            const SizedBox(height: 8),
            _buildLlmSelector(context),
          ],
        ),
      ),
    );
  }
}

// OpenRouter recommended models for pipeline extraction
const _openrouterModels = [
  'qwen/qwen3-14b',
  'qwen/qwen3-8b',
  'qwen/qwen3-30b-a3b',
  'meta-llama/llama-3.1-8b-instruct',
  'mistralai/mistral-nemo-12b',
];

// Claude Proxy models (etheryale.com)
const _claudeProxyModels = [
  'claude-haiku-4-5-20251001',
  'claude-sonnet-4-5-20250514',
];

/// Mutable working copy of a channel binding.
class _ChannelEntry {
  String channelId;
  String civName;
  String player;

  _ChannelEntry(this.channelId, this.civName, this.player);
}
