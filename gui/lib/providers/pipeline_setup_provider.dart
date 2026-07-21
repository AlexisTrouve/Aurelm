import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/bot_config_service.dart';
import '../services/ollama_service.dart';
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
/// config already defaults to, so choosing it changes nothing surprising. Mirrors
/// the recommended entry in the model registry.
const kDefaultOllamaModel = 'qwen3:14b';

final ollamaServiceProvider = Provider<OllamaService>((ref) => OllamaService());

/// Snapshot of the local Ollama install: is it reachable, and which models are
/// pulled. An empty list with reachable=false means Ollama isn't running/installed.
class OllamaStatus {
  final bool reachable;
  final List<String> models;
  const OllamaStatus({required this.reachable, required this.models});

  bool hasModel(String name) =>
      models.any((m) => m == name || m.startsWith('$name:'));
}

/// Probes the locally running Ollama. Reachability is whether /api/tags answered,
/// NOT whether any model is installed — a fresh Ollama has none, and treating that
/// as "not detected" would hide the download UI in exactly its target state.
final ollamaStatusProvider = FutureProvider<OllamaStatus>((ref) async {
  final probe = await BotConfigService.probeOllama();
  return OllamaStatus(reachable: probe.reachable, models: probe.models);
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

// --------------------------------------------------------------------------- //
// Model download (Ollama pull)
// --------------------------------------------------------------------------- //

enum PullStatus { idle, downloading, done, error }

class PullState {
  final PullStatus status;

  /// Model currently being pulled (or the one that finished/failed).
  final String? model;

  /// 0.0–1.0 during a byte-counted phase, null for indeterminate phases.
  final double? fraction;

  /// Ollama's current phase text, or a failure message.
  final String? message;

  const PullState({
    this.status = PullStatus.idle,
    this.model,
    this.fraction,
    this.message,
  });

  bool get isDownloading => status == PullStatus.downloading;
}

/// Downloads a model through Ollama, exposing live progress. The wizard does NOT
/// install Ollama itself — this only pulls a model into an already-running Ollama.
class OllamaPullNotifier extends StateNotifier<PullState> {
  final Ref _ref;
  StreamSubscription<PullProgress>? _sub;

  OllamaPullNotifier(this._ref) : super(const PullState());

  /// Start pulling [model]. Safe to call again after done/error; ignored while a
  /// pull is already running.
  void download(String model) {
    if (state.isDownloading) return;
    state = PullState(status: PullStatus.downloading, model: model, message: 'Démarrage…');
    _sub?.cancel();
    _sub = _ref.read(ollamaServiceProvider).pull(model).listen((p) {
      if (p.error != null) {
        state = PullState(status: PullStatus.error, model: model, message: p.error);
        _sub?.cancel();
      } else if (p.done) {
        state = PullState(status: PullStatus.done, model: model);
        // The installed-models list changed — let the status probe refresh so the
        // panel flips to "prêt".
        _ref.invalidate(ollamaStatusProvider);
        _sub?.cancel();
      } else {
        state = PullState(
          status: PullStatus.downloading,
          model: model,
          fraction: p.fraction,
          message: p.status,
        );
      }
    }, onError: (Object e) {
      state = PullState(status: PullStatus.error, model: model, message: '$e');
    });
  }

  void reset() {
    _sub?.cancel();
    state = const PullState();
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}

final ollamaPullProvider =
    StateNotifierProvider<OllamaPullNotifier, PullState>((ref) {
  return OllamaPullNotifier(ref);
});
