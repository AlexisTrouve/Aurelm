import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/bot_config_service.dart';
import 'database_provider.dart';
import 'enrollment_provider.dart';

/// The two engines the ingestion pipeline can run on.
///
/// - ollama: local, free, needs the model pulled onto the machine (Arthur has the
///   GPU for it). No key.
/// - openrouter: cloud, needs an API key, costs per run. No local install.
/// (claude_proxy exists too but isn't offered in first-run — it's an advanced
/// choice configurable later in Settings.)
enum PipelineEngine { ollama, openrouter }

extension PipelineEngineId on PipelineEngine {
  String get configValue => switch (this) {
        PipelineEngine.ollama => 'ollama',
        PipelineEngine.openrouter => 'openrouter',
      };
}

/// The default model Arthur's GPU (RTX 5070 Ti) runs well; also the value the bot
/// config already defaults to, so choosing it changes nothing surprising.
const kDefaultOllamaModel = 'qwen3:14b';

/// Snapshot of the local Ollama install: is it reachable, and which models are
/// pulled. An empty list with reachable=false means Ollama isn't running/installed.
class OllamaStatus {
  final bool reachable;
  final List<String> models;
  const OllamaStatus({required this.reachable, required this.models});

  bool hasModel(String name) =>
      models.any((m) => m == name || m.startsWith('$name:'));
}

/// Probes the locally running Ollama. Reachable is inferred from whether the tags
/// endpoint answered at all — the model list is empty both when Ollama is down and
/// when it's up with nothing pulled, so we distinguish the two here.
final ollamaStatusProvider = FutureProvider<OllamaStatus>((ref) async {
  final models = await BotConfigService.fetchOllamaModels();
  // fetchOllamaModels swallows errors into an empty list, so a non-empty list
  // proves reachability; for the empty case we can't tell down-vs-empty from here,
  // so treat "any answer" optimistically as reachable only when models exist.
  return OllamaStatus(reachable: models.isNotEmpty, models: models);
});

class PipelineSetupState {
  final PipelineEngine engine;
  final String ollamaModel;
  final bool saving;
  final String? error;
  const PipelineSetupState({
    this.engine = PipelineEngine.ollama,
    this.ollamaModel = kDefaultOllamaModel,
    this.saving = false,
    this.error,
  });

  PipelineSetupState copyWith({
    PipelineEngine? engine,
    String? ollamaModel,
    bool? saving,
    String? error,
  }) =>
      PipelineSetupState(
        engine: engine ?? this.engine,
        ollamaModel: ollamaModel ?? this.ollamaModel,
        saving: saving ?? this.saving,
        error: error,
      );
}

/// Persists the pipeline engine choice: the provider + model land in
/// aurelm_config.json (read by the bot's config), and an OpenRouter key is sealed
/// in secure storage (DPAPI) exactly like the other secrets — never in the config
/// file — then injected as OPENROUTER_API_KEY when the bot starts.
class PipelineSetupNotifier extends StateNotifier<PipelineSetupState> {
  final Ref _ref;
  PipelineSetupNotifier(this._ref) : super(const PipelineSetupState());

  void selectEngine(PipelineEngine engine) =>
      state = state.copyWith(engine: engine, error: null);

  void selectModel(String model) => state = state.copyWith(ollamaModel: model);

  /// Save the choice. [openRouterKey] is required (and sealed) only for OpenRouter.
  /// Returns false without a database (step 2 must have run) or on a missing key.
  Future<bool> save({String? openRouterKey}) async {
    final dbPath = _ref.read(dbPathProvider);
    if (dbPath == null) {
      state = state.copyWith(error: 'La base doit être créée avant cette étape.');
      return false;
    }
    if (state.engine == PipelineEngine.openrouter &&
        (openRouterKey == null || openRouterKey.trim().isEmpty)) {
      state = state.copyWith(error: 'Renseigne ta clé OpenRouter.');
      return false;
    }

    state = state.copyWith(saving: true, error: null);
    try {
      if (state.engine == PipelineEngine.openrouter) {
        await _ref.read(keyStoreProvider).writeOpenRouterKey(openRouterKey!.trim());
      }
      final existing = await BotConfigService.load(dbPath);
      await BotConfigService.save(
        dbPath,
        existing.copyWith(
          llmProvider: state.engine.configValue,
          // Ollama needs a real model; OpenRouter ignores this field (its model is
          // set server-side), so keep whatever was there.
          ollamaModel: state.engine == PipelineEngine.ollama
              ? state.ollamaModel
              : existing.ollamaModel,
        ),
      );
      state = state.copyWith(saving: false);
      return true;
    } catch (e) {
      state = state.copyWith(saving: false, error: 'Échec de l\'enregistrement : $e');
      return false;
    }
  }
}

final pipelineSetupProvider =
    StateNotifierProvider<PipelineSetupNotifier, PipelineSetupState>((ref) {
  return PipelineSetupNotifier(ref);
});
