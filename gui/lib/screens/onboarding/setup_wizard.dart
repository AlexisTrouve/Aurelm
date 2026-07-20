import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/discord_provider.dart';
import '../../providers/enrollment_provider.dart';
import '../../services/discord_service.dart';

/// First-run wizard — the only moment Aurelm needs the network to set itself up.
///
/// WHAT: collects everything a fresh instance needs, in order:
///   1. Activation  — trade a one-time code for the etheryale API key (implemented)
///   2. Database    — create + migrate the local DB                   (implemented)
///   3. Discord     — bot token, verify, channel↔civ mapping       (implemented)
///   4. Pipeline    — Ollama or OpenRouter for ingestion      (placeholder, Step 10 #3)
///
/// WHY it sits above the router: until a key exists there is no bot, so the shell,
/// the database and the navigation rail have nothing to show. Gating here also
/// guarantees the bot is not auto-started key-less (which would leave /chat on 503).
///
/// COMMENT: the last step is a visible placeholder rather than hidden — its content
/// depends on a chantier not designed yet, and showing the shape keeps the wizard
/// honest about what's coming. Finishing marks `setup_complete`, which is what every
/// later launch checks (locally, offline).
class SetupWizard extends ConsumerStatefulWidget {
  const SetupWizard({super.key});

  @override
  ConsumerState<SetupWizard> createState() => _SetupWizardState();
}

class _SetupWizardState extends ConsumerState<SetupWizard> {
  int _step = 0;

  Future<void> _finish() async {
    await ref.read(keyStoreProvider).markSetupComplete();
    // Re-read the flag; the app swaps the wizard for the real UI when it flips.
    ref.invalidate(setupCompleteProvider);
  }

  @override
  Widget build(BuildContext context) {
    final steps = <({String title, Widget body})>[
      (title: 'Activation', body: _ActivationStep(onDone: () => setState(() => _step = 1))),
      (title: 'Base', body: _DatabaseStep(onDone: () => setState(() => _step = 2))),
      (title: 'Discord', body: DiscordStep(onDone: () => setState(() => _step = 3))),
      (title: 'Analyse', body: const _PlaceholderStep(
        what: 'Moteur d\'analyse',
        why: 'Ollama (local) ou OpenRouter (cloud) pour traiter les tours.',
      )),
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
                // Steps that have a side effect (activation redeem, DB migrate,
                // Discord save) own their forward action — the bar only drives the
                // placeholder steps, which have none.
                _NavBar(
                  showBack: _step > 0,
                  onBack: () => setState(() => _step -= 1),
                  showForward: _step >= 3,
                  isLast: _step == steps.length - 1,
                  onForward: () {
                    if (_step < steps.length - 1) {
                      setState(() => _step += 1);
                    } else {
                      _finish();
                    }
                  },
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
        const SizedBox(height: 20),
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
    setState(() => _saving = true);
    final mappings = <String, ({String civName, String player})>{};
    _civCtrls.forEach((channelId, ctrl) {
      mappings[channelId] = (
        civName: ctrl.text,
        player: _playerCtrls[channelId]?.text ?? '',
      );
    });
    final ok = await ref.read(discordConnectProvider.notifier).save(
          token: _tokenCtrl.text,
          mappings: mappings,
        );
    if (!mounted) return;
    setState(() => _saving = false);
    if (ok) widget.onDone();
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

/// A wizard step whose real content belongs to a chantier that isn't designed yet.
/// Shown rather than hidden so the wizard doesn't silently pretend setup is finished.
class _PlaceholderStep extends StatelessWidget {
  final String what;
  final String why;
  const _PlaceholderStep({required this.what, required this.why});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(Icons.construction_outlined,
            size: 40, color: Theme.of(context).colorScheme.outline),
        const SizedBox(height: 12),
        Text(what, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 6),
        Text(why,
            style: Theme.of(context).textTheme.bodySmall,
            textAlign: TextAlign.center),
        const SizedBox(height: 10),
        Text('À configurer dans Réglages pour l\'instant.',
            style: Theme.of(context).textTheme.bodySmall,
            textAlign: TextAlign.center),
      ],
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
