import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;

import '../../models/ollama_models.dart';
import '../../providers/discord_provider.dart';
import '../../providers/enrollment_provider.dart';
import '../../providers/pipeline_setup_provider.dart';
import '../../services/discord_service.dart';
import '../../services/ollama_service.dart';

/// Opens a native "Save As" dialog for the database file, returning the chosen full
/// path (folder + filename) or null if cancelled.
///
/// WHY a seam (a top-level function var, not an inline call): the picker is a native
/// OS dialog that `flutter_test` cannot drive, so tests swap in a fake that returns a
/// fixed path. Reset it in tearDown. `saveFile` (not `pickFiles`) is deliberate — the
/// DB does not exist yet, so we let the user name a NEW file, not open an existing one.
typedef DbLocationPicker = Future<String?> Function({
  required String suggestedName,
  required String initialDirectory,
});

Future<String?> _nativeDbLocationPicker({
  required String suggestedName,
  required String initialDirectory,
}) =>
    FilePicker.platform.saveFile(
      dialogTitle: 'Emplacement de la base Aurelm',
      fileName: suggestedName,
      initialDirectory: initialDirectory.isEmpty ? null : initialDirectory,
    );

/// Overridable in tests; the native dialog in production.
DbLocationPicker dbLocationPicker = _nativeDbLocationPicker;

/// First-run wizard — the only moment Aurelm needs the network to set itself up.
///
/// WHAT: collects everything a fresh instance needs, in order:
///   1. Activation  — trade a one-time code for the etheryale API key (implemented)
///   2. Database    — create + migrate the local DB                   (implemented)
///   3. Discord     — bot token, verify, channel↔civ mapping       (implemented)
///   4. Pipeline    — Ollama (local) or OpenRouter (cloud) for ingestion (implemented)
///
/// WHY it sits above the router: until a key exists there is no bot, so the shell,
/// the database and the navigation rail have nothing to show. Gating here also
/// guarantees the bot is not auto-started key-less (which would leave /chat on 503).
///
/// COMMENT: every step now has a real side effect and owns its own forward button;
/// the last one marks `setup_complete`, which is what every later launch checks
/// (locally, offline) to decide whether the wizard runs at all.
class SetupWizard extends ConsumerStatefulWidget {
  const SetupWizard({super.key});

  @override
  ConsumerState<SetupWizard> createState() => _SetupWizardState();
}

class _SetupWizardState extends ConsumerState<SetupWizard> {
  int _step = 0;

  /// True until we've resolved which step to START on. WHY: the activation code is
  /// single-use and consumed the instant the key is sealed. If setup is interrupted
  /// AFTER activation but before the wizard finishes (setup_complete never flips),
  /// a naive restart would show the activation step again and ask for a code that is
  /// already burned — locking the user out. So on mount we skip activation when a key
  /// is already sealed. The later steps (DB migrate, Discord, pipeline) are idempotent
  /// and safe to re-run, so we only ever skip the one irreversible step.
  bool _resolvingStart = true;

  @override
  void initState() {
    super.initState();
    _resolveStartStep();
  }

  Future<void> _resolveStartStep() async {
    final hasKey = await ref.read(keyStoreProvider).hasKey();
    if (!mounted) return;
    setState(() {
      _step = hasKey ? 1 : 0; // key already sealed → resume past activation
      _resolvingStart = false;
    });
  }

  Future<void> _finish() async {
    await ref.read(keyStoreProvider).markSetupComplete();
    // Re-read the flag; the app swaps the wizard for the real UI when it flips.
    ref.invalidate(setupCompleteProvider);
  }

  @override
  Widget build(BuildContext context) {
    // Hold a spinner until the start step is known, so a returning user doesn't see
    // the activation step flash before we skip it.
    if (_resolvingStart) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final steps = <({String title, Widget body})>[
      (title: 'Activation', body: _ActivationStep(onDone: () => setState(() => _step = 1))),
      (title: 'Base', body: _DatabaseStep(onDone: () => setState(() => _step = 2))),
      (title: 'Discord', body: DiscordStep(onDone: () => setState(() => _step = 3))),
      // Last step: its own action finishes the whole wizard.
      (title: 'Analyse', body: PipelineStep(onDone: _finish)),
    ];

    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('Bienvenue dans Aurelm',
                    style: Theme.of(context).textTheme.headlineSmall,
                    textAlign: TextAlign.center),
                const SizedBox(height: 8),
                Text('Configuration initiale — une seule fois.',
                    style: Theme.of(context).textTheme.bodyMedium,
                    textAlign: TextAlign.center),
                const SizedBox(height: 28),
                _StepIndicator(
                    labels: [for (final s in steps) s.title], current: _step),
                const SizedBox(height: 28),
                steps[_step].body,
                const SizedBox(height: 24),
                // Every step now owns its forward action (each has a side effect:
                // redeem, migrate, Discord save, pipeline save), so the bar only
                // offers "Retour".
                _NavBar(
                  showBack: _step > 0,
                  onBack: () => setState(() => _step -= 1),
                  showForward: false,
                  isLast: _step == steps.length - 1,
                  onForward: () {},
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Step 1 — paste an activation code, get a sealed API key.
class _ActivationStep extends ConsumerStatefulWidget {
  final VoidCallback onDone;
  const _ActivationStep({required this.onDone});

  @override
  ConsumerState<_ActivationStep> createState() => _ActivationStepState();
}

class _ActivationStepState extends ConsumerState<_ActivationStep> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final ok = await ref.read(activationProvider.notifier).activate(_controller.text);
    if (ok && mounted) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(activationProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text("Colle le code d'activation qu'on t'a envoyé."),
        const SizedBox(height: 16),
        TextField(
          key: const Key('activation_code_field'),
          controller: _controller,
          // ONE field, not four boxes: the code is ~41 chars and meant to be pasted.
          // No length/format validation here — the server normalises case and
          // whitespace, and a client-side rule would reject a good code the day the
          // format changes.
          autofocus: true,
          enabled: !state.isSubmitting,
          onChanged: (_) => ref.read(activationProvider.notifier).clearError(),
          onSubmitted: (_) => state.isSubmitting ? null : _submit(),
          decoration: InputDecoration(
            labelText: "Code d'activation",
            hintText: 'AURELM-XXXX-XXXX-…',
            border: const OutlineInputBorder(),
            errorText: state.error,
            errorMaxLines: 3,
          ),
        ),
        const SizedBox(height: 20),
        FilledButton(
          key: const Key('activation_submit'),
          onPressed: state.isSubmitting ? null : _submit,
          child: state.isSubmitting
              ? const SizedBox(
                  height: 18, width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Activer'),
        ),
        const SizedBox(height: 12),
        Text(
          "Le code ne fonctionne qu'une fois. S'il est refusé, demande-en un nouveau.",
          style: Theme.of(context).textTheme.bodySmall,
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

/// Step 2 — create and migrate the local database.
class _DatabaseStep extends ConsumerStatefulWidget {
  final VoidCallback onDone;
  const _DatabaseStep({required this.onDone});

  @override
  ConsumerState<_DatabaseStep> createState() => _DatabaseStepState();
}

class _DatabaseStepState extends ConsumerState<_DatabaseStep> {
  String? _chosenPath; // null → use the default

  Future<void> _submit() async {
    final ok = await ref.read(dbSetupProvider.notifier).prepare(path: _chosenPath);
    if (ok && mounted) widget.onDone();
  }

  /// Let the user pick the DB folder AND filename via the native file explorer.
  /// Seeds the dialog with the current choice when there is one; otherwise a bare
  /// default name and no forced directory (the OS opens somewhere sensible). A cancel
  /// leaves the current choice untouched.
  ///
  /// WHY not seed from defaultDbPath(): resolving the documents dir is a platform call
  /// we don't want to block the picker on — the suggested filename is enough, and the
  /// real default is still applied at prepare() time when the user picks nothing.
  Future<void> _pickLocation() async {
    final base = _chosenPath;
    final chosen = await dbLocationPicker(
      suggestedName: base != null ? p.basename(base) : 'aurelm.db',
      initialDirectory: base != null ? p.dirname(base) : '',
    );
    if (chosen != null && chosen.trim().isNotEmpty && mounted) {
      setState(() => _chosenPath = chosen);
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(dbSetupProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          "Aurelm va créer sa base de données locale — c'est là que vivent tes "
          'civilisations, tours et entités.',
        ),
        const SizedBox(height: 16),
        // The resolved default, shown so the user knows where their data lands.
        FutureBuilder<String>(
          future: defaultDbPath(),
          builder: (context, snap) {
            final path = _chosenPath ?? snap.data ?? '…';
            return Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.folder_outlined, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(path,
                        style: Theme.of(context).textTheme.bodySmall,
                        overflow: TextOverflow.ellipsis),
                  ),
                ],
              ),
            );
          },
        ),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: OutlinedButton.icon(
            key: const Key('db_pick_location'),
            icon: const Icon(Icons.folder_open, size: 16),
            label: const Text("Changer l'emplacement / le nom…"),
            onPressed: state.isPreparing ? null : _pickLocation,
          ),
        ),
        const SizedBox(height: 12),
        FilledButton(
          key: const Key('db_submit'),
          onPressed: state.isPreparing ? null : _submit,
          child: state.isPreparing
              ? const SizedBox(
                  height: 18, width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Créer la base'),
        ),
        if (state.error != null) ...[
          const SizedBox(height: 12),
          Text(state.error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
              textAlign: TextAlign.center),
        ],
      ],
    );
  }
}

/// Step 3 — connect Arthur's OWN Discord bot and map its channels to civilizations.
///
/// WHY his own app and not a shared one: the bot reads the private messages of his
/// server; that access must belong to him, and a rotation of anyone else's token
/// must not break him. Discord exposes no API to create the app or flip the intent
/// for him — those are four clicks in his browser — so our value is that every step
/// is VERIFIED: a dead token or a forgotten Message Content intent (the two classic
/// silent failures) cannot slip through.
class DiscordStep extends ConsumerStatefulWidget {
  final VoidCallback onDone;
  const DiscordStep({super.key, required this.onDone});

  @override
  ConsumerState<DiscordStep> createState() => _DiscordStepState();
}

class _DiscordStepState extends ConsumerState<DiscordStep> {
  final _tokenCtrl = TextEditingController();
  // Per-channel civ-name + player inputs, created lazily once the channel list is
  // known (after a successful verify) and disposed together at the end.
  final Map<String, TextEditingController> _civCtrls = {};
  final Map<String, TextEditingController> _playerCtrls = {};
  bool _saving = false;
  String? _saveError;

  @override
  void dispose() {
    _tokenCtrl.dispose();
    for (final c in _civCtrls.values) {
      c.dispose();
    }
    for (final c in _playerCtrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  void _openUrl(String url) {
    // Same approach as the Settings screen — no url_launcher dependency.
    Process.run('cmd', ['/c', 'start', '""', url]);
  }

  Future<void> _verify() async {
    await ref.read(discordConnectProvider.notifier).verify(_tokenCtrl.text);
  }

  Future<void> _finish() async {
    setState(() {
      _saving = true;
      _saveError = null;
    });
    try {
      // Build the mapping from the CURRENT verified channels only — not from every
      // controller ever created. Otherwise a civ name typed against token A's
      // channels would be written as a phantom civ after switching to token B.
      final channels = ref.read(discordConnectProvider).channels;
      final mappings = <String, ({String civName, String player})>{};
      for (final ch in channels) {
        mappings[ch.channelId] = (
          civName: _civCtrls[ch.channelId]?.text ?? '',
          player: _playerCtrls[ch.channelId]?.text ?? '',
        );
      }

      // Two channels mapped to one civ name would silently lose a binding (createCiv
      // upserts by name). Refuse it with a clear message instead.
      final names = <String>{};
      for (final m in mappings.values) {
        final n = m.civName.trim();
        if (n.isEmpty) continue;
        if (!names.add(n.toLowerCase())) {
          setState(() {
            _saving = false;
            _saveError = 'Deux salons pointent vers « $n ». Donne un nom distinct à chaque civilisation.';
          });
          return;
        }
      }

      final ok = await ref.read(discordConnectProvider.notifier).save(
            token: _tokenCtrl.text,
            mappings: mappings,
          );
      if (!mounted) return;
      if (ok) {
        widget.onDone();
      } else {
        setState(() {
          _saving = false;
          _saveError = 'Enregistrement impossible. Réessaie.';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _saving = false;
          _saveError = 'Enregistrement impossible : $e';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(discordConnectProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Instructions — the manual, browser-side part Discord gives us no API for.
        const _NumberedHint(n: 1, text: 'Crée ton application Discord et un bot.'),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            icon: const Icon(Icons.open_in_new, size: 16),
            label: const Text('Ouvrir le portail développeur'),
            onPressed: () => _openUrl('https://discord.com/developers/applications'),
          ),
        ),
        const _NumberedHint(
          n: 2,
          text: 'Active l\'intent "Message Content" (sinon le bot lit des messages vides).',
        ),
        const _NumberedHint(n: 3, text: 'Colle le token du bot ci-dessous.'),
        const SizedBox(height: 12),
        TextField(
          key: const Key('discord_token_field'),
          controller: _tokenCtrl,
          obscureText: true,
          enabled: !state.isVerifying,
          onChanged: (_) => ref.read(discordConnectProvider.notifier).clearError(),
          decoration: InputDecoration(
            labelText: 'Token du bot',
            border: const OutlineInputBorder(),
            errorText: state.error,
            errorMaxLines: 2,
          ),
        ),
        const SizedBox(height: 12),
        FilledButton(
          key: const Key('discord_verify'),
          onPressed: state.isVerifying ? null : _verify,
          child: state.isVerifying
              ? const SizedBox(
                  height: 18, width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Vérifier'),
        ),
        if (state.result != null) ...[
          const SizedBox(height: 20),
          _VerifiedPanel(
            result: state.result!,
            civCtrls: _civCtrls,
            playerCtrls: _playerCtrls,
            onInvite: () =>
                _openUrl(DiscordService.inviteUrl(state.result!.applicationId)),
          ),
          const SizedBox(height: 16),
          FilledButton(
            key: const Key('discord_finish'),
            onPressed: _saving ? null : _finish,
            child: _saving
                ? const SizedBox(
                    height: 18, width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Enregistrer et continuer'),
          ),
          if (_saveError != null) ...[
            const SizedBox(height: 8),
            Text(_saveError!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
                textAlign: TextAlign.center),
          ],
        ],
      ],
    );
  }
}

/// The post-verify panel: bot identity, intent status, and either an invite call
/// to action (bot in no server) or the channel→civ mapping table.
class _VerifiedPanel extends StatelessWidget {
  final DiscordVerifySuccess result;
  final Map<String, TextEditingController> civCtrls;
  final Map<String, TextEditingController> playerCtrls;
  final VoidCallback onInvite;

  const _VerifiedPanel({
    required this.result,
    required this.civCtrls,
    required this.playerCtrls,
    required this.onInvite,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final channels = [
      for (final g in result.guilds)
        for (final c in g.channels) (guild: g.name, id: c.id, name: c.name),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _StatusLine(ok: true, text: 'Bot « ${result.botName} » — token valide'),
        _StatusLine(
          ok: result.hasMessageContent,
          text: result.hasMessageContent
              ? 'Intent Message Content actif'
              : 'Intent Message Content manquant — active-le dans le portail',
        ),
        if (channels.isEmpty) ...[
          const SizedBox(height: 12),
          const _StatusLine(ok: false, text: 'Le bot n\'est sur aucun serveur.'),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            key: const Key('discord_invite'),
            icon: const Icon(Icons.add, size: 16),
            label: const Text('Inviter le bot sur mon serveur'),
            onPressed: onInvite,
          ),
        ] else ...[
          const SizedBox(height: 16),
          Text('Associe tes salons aux civilisations',
              style: Theme.of(context).textTheme.titleSmall),
          Text('Laisse vide un salon que tu ne veux pas suivre.',
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 8),
          // The channel list can be long; keep the wizard from growing unbounded.
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 260),
            child: SingleChildScrollView(
              child: Column(
                children: [
                  for (final ch in channels)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          SizedBox(
                            width: 120,
                            child: Text('#${ch.name}',
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(color: scheme.onSurfaceVariant)),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: TextField(
                              key: Key('civ_${ch.id}'),
                              controller: civCtrls.putIfAbsent(
                                  ch.id, () => TextEditingController()),
                              decoration: const InputDecoration(
                                isDense: true,
                                hintText: 'Civilisation',
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: TextField(
                              controller: playerCtrls.putIfAbsent(
                                  ch.id, () => TextEditingController()),
                              decoration: const InputDecoration(
                                isDense: true,
                                hintText: 'Joueur',
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _NumberedHint extends StatelessWidget {
  final int n;
  final String text;
  const _NumberedHint({required this.n, required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 10,
            backgroundColor: Theme.of(context).colorScheme.primaryContainer,
            child: Text('$n', style: const TextStyle(fontSize: 11)),
          ),
          const SizedBox(width: 8),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}

class _StatusLine extends StatelessWidget {
  final bool ok;
  final String text;
  const _StatusLine({required this.ok, required this.text});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Icon(ok ? Icons.check_circle : Icons.warning_amber_rounded,
              size: 16, color: ok ? Colors.green : scheme.tertiary),
          const SizedBox(width: 8),
          Expanded(child: Text(text, style: Theme.of(context).textTheme.bodySmall)),
        ],
      ),
    );
  }
}

/// Step 4 — pick the ingestion engine: local Ollama or cloud OpenRouter.
///
/// WHY both stay: Ollama is free and private but needs the model pulled onto the
/// machine; OpenRouter needs no install but costs per run and wants a key. Arthur's
/// GPU makes Ollama the natural default, so we default to it and only ask for a key
/// on the OpenRouter branch.
class PipelineStep extends ConsumerStatefulWidget {
  final VoidCallback onDone;
  const PipelineStep({super.key, required this.onDone});

  @override
  ConsumerState<PipelineStep> createState() => _PipelineStepState();
}

class _PipelineStepState extends ConsumerState<PipelineStep> {
  final _keyCtrl = TextEditingController();

  @override
  void dispose() {
    _keyCtrl.dispose();
    super.dispose();
  }

  Future<void> _finish() async {
    final ok = await ref.read(pipelineSetupProvider.notifier).save(
          openRouterKey: _keyCtrl.text,
        );
    if (ok && mounted) widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(pipelineSetupProvider);
    final notifier = ref.read(pipelineSetupProvider.notifier);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('Comment veux-tu analyser les tours de jeu ?'),
        const SizedBox(height: 12),
        _EngineChoice(
          selected: state.engine == PipelineEngine.ollama,
          icon: Icons.computer,
          title: 'Ollama — local',
          subtitle: 'Gratuit et privé. Nécessite le modèle sur ta machine.',
          onTap: () => notifier.selectEngine(PipelineEngine.ollama),
        ),
        const SizedBox(height: 8),
        _EngineChoice(
          selected: state.engine == PipelineEngine.openrouter,
          icon: Icons.cloud_outlined,
          title: 'OpenRouter — cloud',
          subtitle: 'Aucune installation. Nécessite une clé API (payant à l\'usage).',
          onTap: () => notifier.selectEngine(PipelineEngine.openrouter),
        ),
        const SizedBox(height: 16),
        if (state.engine == PipelineEngine.ollama)
          const _OllamaPanel()
        else
          _OpenRouterPanel(controller: _keyCtrl),
        if (state.error != null) ...[
          const SizedBox(height: 12),
          Text(state.error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
              textAlign: TextAlign.center),
        ],
        const SizedBox(height: 20),
        FilledButton(
          key: const Key('pipeline_finish'),
          onPressed: state.saving ? null : _finish,
          child: state.saving
              ? const SizedBox(
                  height: 18, width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Terminer'),
        ),
      ],
    );
  }
}

/// Live status of the local Ollama, with a copyable pull command when the default
/// model isn't there. WHY not auto-pull: a pull is a multi-GB, minutes-long
/// download that wants its own progress UI — pushing it into a wizard step would
/// block the whole setup on a bar we don't have.
class _OllamaPanel extends ConsumerWidget {
  const _OllamaPanel();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status = ref.watch(ollamaStatusProvider);
    final selectedModel = ref.watch(pipelineSetupProvider).ollamaModel;

    return status.when(
      loading: () => const _StatusLine(ok: true, text: 'Détection d\'Ollama…'),
      error: (_, __) =>
          const _StatusLine(ok: false, text: 'Impossible de détecter Ollama.'),
      data: (s) {
        if (!s.reachable) {
          final svc = ref.read(ollamaServiceProvider);
          final inst = ref.watch(ollamaInstallProvider);
          // A preparation (start or download+install) is in flight → show its progress.
          if (inst != null && inst.phase != InstallPhase.error) {
            return _OllamaInstallProgress(inst);
          }
          // Installed but not running (e.g. after a reboot) → START it automatically.
          // No click, and NEVER prompt to reinstall something already on disk.
          if (svc.isInstalled && inst == null) {
            WidgetsBinding.instance.addPostFrameCallback(
                (_) => ref.read(ollamaInstallProvider.notifier).install());
            return _OllamaInstallProgress(
                const InstallProgress(InstallPhase.starting));
          }
          // Genuinely absent → offer the automatic download+install (a big download,
          // so behind a button for consent). The manual path stays as a fallback.
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const _StatusLine(ok: false, text: 'Ollama n\'est pas installé.'),
              const SizedBox(height: 12),
              FilledButton.icon(
                key: const Key('ollama_auto_install'),
                icon: const Icon(Icons.download, size: 18),
                label: const Text('Installer Ollama + le modèle (automatique)'),
                onPressed: () => ref.read(ollamaInstallProvider.notifier).install(),
              ),
              const SizedBox(height: 4),
              Text(
                'Télécharge et installe Ollama depuis internet, puis récupère le '
                'modèle conseillé — aucune étape manuelle. Gros téléchargement '
                '(plusieurs Go) ; tu peux aussi cliquer « Terminer » et le lancer plus tard.',
                style: Theme.of(context).textTheme.bodySmall,
                textAlign: TextAlign.center,
              ),
              if (inst?.phase == InstallPhase.error) ...[
                const SizedBox(height: 8),
                Text(inst!.error ?? 'Échec de l\'installation.',
                    style: TextStyle(color: Theme.of(context).colorScheme.error),
                    textAlign: TextAlign.center),
              ],
              const SizedBox(height: 12),
              // Manual fallback, for a locked-down machine or an offline install.
              Text('Ou installe-le manuellement :',
                  style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 4),
              const _CopyCommand('ollama pull $kDefaultOllamaModel'),
              TextButton(
                onPressed: () => ref.invalidate(ollamaStatusProvider),
                child: const Text('Revérifier'),
              ),
            ],
          );
        }
        final pull = ref.watch(ollamaPullProvider);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _StatusLine(ok: true, text: 'Ollama détecté — ${s.models.length} modèle(s)'),
            const SizedBox(height: 8),
            const Text('Choisis un modèle à télécharger :'),
            const SizedBox(height: 8),
            // The curated registry, recommended first — the single source of truth
            // lives in models/ollama_models.dart, read here and (later) in Settings.
            for (final m in kRecommendedModels)
              _ModelChoice(
                model: m,
                selected: selectedModel == m.id,
                installed: s.hasModel(m.id),
                onTap: () => ref.read(pipelineSetupProvider.notifier).selectModel(m.id),
              ),
            const SizedBox(height: 12),
            _DownloadArea(
              selectedModel: selectedModel,
              installed: s.hasModel(selectedModel),
              pull: pull,
              onDownload: () =>
                  ref.read(ollamaPullProvider.notifier).download(selectedModel),
            ),
          ],
        );
      },
    );
  }
}

/// Live progress of the automatic Ollama runtime install (download → install →
/// start). The model pull that follows is shown by the reachable branch once the
/// status probe flips.
class _OllamaInstallProgress extends StatelessWidget {
  final InstallProgress inst;
  const _OllamaInstallProgress(this.inst);

  @override
  Widget build(BuildContext context) {
    final (String label, double? frac) = switch (inst.phase) {
      InstallPhase.downloading => (
          inst.fraction != null
              ? 'Téléchargement d\'Ollama — ${(inst.fraction! * 100).toStringAsFixed(0)} %'
              : 'Téléchargement d\'Ollama…',
          inst.fraction),
      InstallPhase.installing => ('Installation d\'Ollama…', null),
      InstallPhase.starting => ('Démarrage d\'Ollama…', null),
      InstallPhase.done => ('Ollama prêt — récupération du modèle…', 1.0),
      InstallPhase.error => (inst.error ?? 'Échec de l\'installation.', null),
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        LinearProgressIndicator(value: frac),
        const SizedBox(height: 6),
        Text(label,
            style: Theme.of(context).textTheme.bodySmall,
            textAlign: TextAlign.center),
      ],
    );
  }
}

/// One selectable model row: label, size, recommended badge, and install state.
class _ModelChoice extends StatelessWidget {
  final RecommendedModel model;
  final bool selected;
  final bool installed;
  final VoidCallback onTap;

  const _ModelChoice({
    required this.model,
    required this.selected,
    required this.installed,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            border: Border.all(
              color: selected ? scheme.primary : scheme.outlineVariant,
              width: selected ? 2 : 1,
            ),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Icon(selected ? Icons.radio_button_checked : Icons.radio_button_off,
                  size: 18, color: selected ? scheme.primary : scheme.outline),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(model.label,
                            style: Theme.of(context).textTheme.titleSmall),
                        const SizedBox(width: 6),
                        Text(model.size,
                            style: Theme.of(context).textTheme.bodySmall),
                        if (model.recommended) ...[
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                            decoration: BoxDecoration(
                              color: scheme.primaryContainer,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text('Recommandé',
                                style: TextStyle(
                                    fontSize: 10, color: scheme.onPrimaryContainer)),
                          ),
                        ],
                      ],
                    ),
                    Text(model.note, style: Theme.of(context).textTheme.bodySmall),
                  ],
                ),
              ),
              if (installed)
                const Padding(
                  padding: EdgeInsets.only(left: 6),
                  child: Icon(Icons.check_circle, size: 18, color: Colors.green),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// The action zone under the model list: "already installed", a download button,
/// a live progress bar, or an error with retry — depending on state.
class _DownloadArea extends StatelessWidget {
  final String selectedModel;
  final bool installed;
  final PullState pull;
  final VoidCallback onDownload;

  const _DownloadArea({
    required this.selectedModel,
    required this.installed,
    required this.pull,
    required this.onDownload,
  });

  @override
  Widget build(BuildContext context) {
    // Already on disk → nothing to do.
    if (installed) {
      return const _StatusLine(ok: true, text: 'Modèle déjà présent — prêt à l\'emploi.');
    }

    // A pull is running (or finished/failed) for THIS model.
    if (pull.model == selectedModel) {
      switch (pull.status) {
        case PullStatus.downloading:
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              LinearProgressIndicator(value: pull.fraction),
              const SizedBox(height: 6),
              Text(
                pull.fraction != null
                    ? '${pull.message ?? "Téléchargement"} — ${(pull.fraction! * 100).toStringAsFixed(0)} %'
                    : (pull.message ?? 'Téléchargement…'),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          );
        case PullStatus.done:
          return const _StatusLine(ok: true, text: 'Téléchargement terminé.');
        case PullStatus.error:
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _StatusLine(ok: false, text: pull.message ?? 'Échec du téléchargement.'),
              const SizedBox(height: 4),
              OutlinedButton(onPressed: onDownload, child: const Text('Réessayer')),
            ],
          );
        case PullStatus.idle:
          break;
      }
    }

    // Not installed, no pull in flight → offer the download.
    final size = kRecommendedModels
        .firstWhere((m) => m.id == selectedModel,
            orElse: () => const RecommendedModel(
                id: '', label: '', size: '', note: ''))
        .size;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        FilledButton.icon(
          key: const Key('ollama_download'),
          icon: const Icon(Icons.download, size: 18),
          label: Text('Télécharger${size.isNotEmpty ? " ($size)" : ""}'),
          onPressed: onDownload,
        ),
        const SizedBox(height: 4),
        Text(
          'Le téléchargement peut prendre plusieurs minutes. Tu peux aussi cliquer '
          '"Terminer" et le lancer plus tard.',
          style: Theme.of(context).textTheme.bodySmall,
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

class _OpenRouterPanel extends StatelessWidget {
  final TextEditingController controller;
  const _OpenRouterPanel({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          key: const Key('openrouter_key_field'),
          controller: controller,
          obscureText: true,
          decoration: const InputDecoration(
            labelText: 'Clé API OpenRouter',
            hintText: 'sk-or-…',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 6),
        Text('La clé est stockée de façon sécurisée (jamais en clair sur le disque).',
            style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}

/// A one-line command in a mono box with a copy button — for the Ollama pull.
class _CopyCommand extends StatelessWidget {
  final String command;
  const _CopyCommand(this.command);

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(command,
                style: const TextStyle(fontFamily: 'monospace', fontSize: 13)),
          ),
          IconButton(
            icon: const Icon(Icons.copy, size: 16),
            tooltip: 'Copier',
            onPressed: () => Clipboard.setData(ClipboardData(text: command)),
          ),
        ],
      ),
    );
  }
}

/// A selectable engine card for the pipeline step.
class _EngineChoice extends StatelessWidget {
  final bool selected;
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _EngineChoice({
    required this.selected,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          border: Border.all(
            color: selected ? scheme.primary : scheme.outlineVariant,
            width: selected ? 2 : 1,
          ),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          children: [
            Icon(icon, color: selected ? scheme.primary : scheme.onSurfaceVariant),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: Theme.of(context).textTheme.titleSmall),
                  Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
            if (selected) Icon(Icons.check_circle, color: scheme.primary, size: 20),
          ],
        ),
      ),
    );
  }
}

/// Back / forward controls at the bottom of the wizard. The forward button is only
/// rendered for steps that don't drive their own advance (the placeholders).
class _NavBar extends StatelessWidget {
  final bool showBack;
  final VoidCallback onBack;
  final bool showForward;
  final bool isLast;
  final VoidCallback onForward;

  const _NavBar({
    required this.showBack,
    required this.onBack,
    required this.showForward,
    required this.isLast,
    required this.onForward,
  });

  @override
  Widget build(BuildContext context) {
    if (!showBack && !showForward) return const SizedBox.shrink();
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        showBack
            ? TextButton(onPressed: onBack, child: const Text('Retour'))
            : const SizedBox.shrink(),
        showForward
            ? FilledButton(
                key: const Key('wizard_next'),
                onPressed: onForward,
                child: Text(isLast ? 'Terminer' : 'Suivant'),
              )
            : const SizedBox.shrink(),
      ],
    );
  }
}

class _StepIndicator extends StatelessWidget {
  final List<String> labels;
  final int current;
  const _StepIndicator({required this.labels, required this.current});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        for (var i = 0; i < labels.length; i++) ...[
          if (i > 0)
            Container(
                width: 28, height: 1.5,
                color: i <= current ? scheme.primary : scheme.outlineVariant),
          Column(
            children: [
              CircleAvatar(
                radius: 13,
                backgroundColor:
                    i <= current ? scheme.primary : scheme.surfaceContainerHighest,
                child: Text('${i + 1}',
                    style: TextStyle(
                        fontSize: 12,
                        color: i <= current ? scheme.onPrimary : scheme.outline)),
              ),
              const SizedBox(height: 4),
              Text(labels[i], style: Theme.of(context).textTheme.labelSmall),
            ],
          ),
        ],
      ],
    );
  }
}
