import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/enrollment_provider.dart';

/// First-run wizard — the only moment Aurelm needs the network to set itself up.
///
/// WHAT: collects everything a fresh instance needs, in order:
///   1. Activation  — trade a one-time code for the etheryale API key (implemented)
///   2. Discord     — bot token + channel↔civ mapping        (placeholder, Step 10 #4)
///   3. Pipeline    — Ollama or OpenRouter for ingestion      (placeholder, Step 10 #3)
///
/// WHY it sits above the router: until a key exists there is no bot, so the shell,
/// the database and the navigation rail have nothing to show. Gating here also
/// guarantees the bot is not auto-started key-less (which would leave /chat on 503).
///
/// COMMENT: steps 2 and 3 are deliberately visible-but-inert rather than hidden —
/// their real content depends on chantiers that aren't designed yet, and showing the
/// shape now keeps the wizard honest about what's coming. Finishing marks
/// `setup_complete`, which is what every later launch checks (locally, offline).
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
      (title: 'Discord', body: const _PlaceholderStep(
        what: 'Connexion Discord',
        why: 'Token du bot + association channel ↔ civilisation.',
      )),
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
                if (_step > 0)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      TextButton(
                        onPressed: () => setState(() => _step -= 1),
                        child: const Text('Retour'),
                      ),
                      FilledButton(
                        key: const Key('wizard_next'),
                        onPressed: () {
                          if (_step < steps.length - 1) {
                            setState(() => _step += 1);
                          } else {
                            _finish();
                          }
                        },
                        child: Text(_step < steps.length - 1
                            ? 'Suivant'
                            : 'Terminer'),
                      ),
                    ],
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
