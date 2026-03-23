/// Bot & Discord configuration section for the settings screen.
/// Tokens, LLM provider/model, bot port. Channel binding is done in civ detail.

import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/bot_config.dart';
import '../../providers/bot_config_provider.dart';
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

  void _syncFromConfig(BotConfig cfg) {
    if (_initialized) return;
    _initialized = true;
    _discordTokenCtrl.text = cfg.discordToken;
    _anthropicKeyCtrl.text = cfg.anthropicApiKey;
    _llmProvider = cfg.llmProvider;
    _selectedModel = cfg.ollamaModel;
    _botPortCtrl.text = cfg.botPort.toString();
  }

  BotConfig _buildConfig(BotConfig base) {
    return base.copyWith(
      botPort: int.tryParse(_botPortCtrl.text.trim()) ?? base.botPort,
      discordToken: _discordTokenCtrl.text.trim(),
      anthropicApiKey: _anthropicKeyCtrl.text.trim(),
      llmProvider: _llmProvider,
      ollamaModel: _selectedModel,
    );
  }

  Future<void> _save(BotConfig base) async {
    setState(() => _saving = true);
    try {
      await ref.read(botConfigProvider.notifier).save(_buildConfig(base));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Config sauvegardee')));
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

  String? _appIdFromToken(String token) {
    final parts = token.split('.');
    if (parts.length < 3) return null;
    try {
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
    const perms = 68608;
    final url =
        'https://discord.com/api/oauth2/authorize?client_id=$appId&permissions=$perms&scope=bot';
    Process.run('cmd', ['/c', 'start', url]);
  }

  @override
  Widget build(BuildContext context) {
    final configAsync = ref.watch(botConfigProvider);

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
            _buildSettingsCard(context),
            const SizedBox(height: 12),
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
            _secretField('Discord Bot Token', _discordTokenCtrl, _showToken,
                () => setState(() => _showToken = !_showToken)),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _discordTokenCtrl.text.trim().isEmpty
                  ? null
                  : _openInviteUrl,
              icon: const Icon(Icons.open_in_new, size: 16),
              label: const Text('Inviter le bot sur Discord'),
            ),
            const SizedBox(height: 16),
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

  Widget _buildLlmSelector(BuildContext context) {
    final List<_ModelInfo> modelInfos;
    final String recommendedId;
    switch (_llmProvider) {
      case 'ollama':
        modelInfos = _ollamaModels
            .map((m) => _ModelInfo(m, 'Gratuit (local)',
                recommended: m.contains('qwen3') && m.contains('14b')))
            .toList();
        recommendedId = 'qwen3:14b';
      case 'claude_proxy':
        modelInfos = _claudeProxyModels;
        recommendedId = 'claude-haiku-4-5-20251001';
      case 'openrouter':
        modelInfos = _openrouterModels;
        recommendedId = 'qwen/qwen3-14b';
      default:
        modelInfos = [];
        recommendedId = '';
    }

    final modelIds = modelInfos.map((m) => m.id).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SegmentedButton<String>(
          segments: const [
            ButtonSegment(value: 'ollama', label: Text('Ollama')),
            ButtonSegment(value: 'claude_proxy', label: Text('Claude Proxy')),
            ButtonSegment(value: 'openrouter', label: Text('OpenRouter')),
          ],
          selected: {_llmProvider},
          onSelectionChanged: (sel) {
            final newProvider = sel.first;
            final newRecommended = switch (newProvider) {
              'ollama' => 'qwen3:14b',
              'claude_proxy' => 'claude-haiku-4-5-20251001',
              'openrouter' => 'qwen/qwen3-14b',
              _ => '',
            };
            setState(() {
              _llmProvider = newProvider;
              _selectedModel = newRecommended;
            });
          },
        ),
        const SizedBox(height: 8),
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
        else if (_llmProvider == 'ollama' && modelInfos.isEmpty)
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
            value: modelIds.contains(_selectedModel) ? _selectedModel : null,
            decoration: InputDecoration(
              labelText: 'Modele',
              isDense: true,
              border: const OutlineInputBorder(),
              helperText: 'Recommande: $recommendedId',
              helperStyle: const TextStyle(fontSize: 11),
            ),
            items: modelInfos
                .map((m) => DropdownMenuItem(
                      value: m.id,
                      child: Text.rich(
                        TextSpan(children: [
                          if (m.recommended)
                            const WidgetSpan(
                              child: Icon(Icons.star, size: 14,
                                  color: Colors.amber),
                              alignment: PlaceholderAlignment.middle,
                            ),
                          if (m.recommended) const TextSpan(text: ' '),
                          TextSpan(text: m.id,
                              style: const TextStyle(fontSize: 13)),
                          TextSpan(text: '  ${m.price}',
                              style: TextStyle(
                                  fontSize: 11, color: Colors.grey[500])),
                        ]),
                      ),
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

// Model catalog with prices per M tokens (input/output)
class _ModelInfo {
  final String id;
  final String price;
  final bool recommended;
  const _ModelInfo(this.id, this.price, {this.recommended = false});
}

const _openrouterModels = [
  _ModelInfo('qwen/qwen3-14b', '\$0.10 / \$0.30', recommended: true),
  _ModelInfo('qwen/qwen3-8b', '\$0.05 / \$0.15'),
  _ModelInfo('qwen/qwen3-30b-a3b', '\$0.15 / \$0.45'),
  _ModelInfo('meta-llama/llama-3.1-8b-instruct', '\$0.05 / \$0.08'),
  _ModelInfo('mistralai/mistral-nemo-12b', '\$0.13 / \$0.13'),
];

const _claudeProxyModels = [
  _ModelInfo('claude-haiku-4-5-20251001', '\$1.00 / \$5.00'),
  _ModelInfo('claude-sonnet-4-5-20250514', '\$3.00 / \$15.00'),
];
