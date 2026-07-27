part of '../chat_screen.dart';

// ---------------------------------------------------------------------------
// Token usage badge — context tokens / max budget, shown in AppBar
// ---------------------------------------------------------------------------

class _TokenUsageBadge extends StatelessWidget {
  final int contextTokens;
  final int maxTokens;

  const _TokenUsageBadge({
    required this.contextTokens,
    required this.maxTokens,
  });

  /// Format token count: 1234 -> "1.2k", 56789 -> "56.8k"
  static String _fmt(int tokens) {
    if (tokens < 1000) return '$tokens';
    return '${(tokens / 1000).toStringAsFixed(1)}k';
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final ratio = contextTokens / maxTokens;

    // Color shifts as context fills up: green -> amber -> red
    final Color barColor;
    if (ratio < 0.5) {
      barColor = Colors.green;
    } else if (ratio < 0.8) {
      barColor = Colors.amber;
    } else {
      barColor = colorScheme.error;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Tooltip(
        message: 'Contexte: $contextTokens / $maxTokens tokens',
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.token, size: 14, color: barColor),
            const SizedBox(width: 4),
            Text(
              '${_fmt(contextTokens)} / ${_fmt(maxTokens)}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: barColor,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// App-bar dropdown to pick the model for the next turn — populated from the
/// bot's /chat/models (which proxies the etheryale /v1/models). Hidden until the
/// list loads; selecting a model routes subsequent sends through it. Null
/// selection = the bot's configured default.
class _ModelPicker extends ConsumerWidget {
  const _ModelPicker();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(chatModelsProvider).valueOrNull;
    final models = data?.models ?? const <String>[];
    if (models.isEmpty) return const SizedBox.shrink();

    final selected = ref.watch(selectedModelProvider);
    final fallback = (data?.defaultModel.isNotEmpty ?? false)
        ? data!.defaultModel
        : models.first;
    final current = models.contains(selected) ? selected! : fallback;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: models.contains(current) ? current : models.first,
          isDense: true,
          icon: const Icon(Icons.expand_more, size: 18),
          borderRadius: BorderRadius.circular(8),
          style: Theme.of(context).textTheme.bodySmall,
          items: [
            for (final m in models) DropdownMenuItem(value: m, child: Text(m)),
          ],
          onChanged: (m) {
            if (m == null) return;
            ref.read(selectedModelProvider.notifier).state = m;
            ref.read(chatProvider.notifier).setModel(m);
          },
        ),
      ),
    );
  }
}

/// App-bar dropdown to pick how hard the agent reasons on the next turn.
///
/// The levels come from the bot (/chat/models), weakest → strongest. One knob for
/// every provider: the bot forwards it as `reasoning_effort`, which the proxy maps
/// to Anthropic's adaptive effort or to a thinking budget, and passes through to
/// GPT. Measured on opus-4-8: low→max costs ~2.3x the latency for ~2.8x the tokens,
/// hence the warning on the heavy levels.
class _EffortPicker extends ConsumerWidget {
  const _EffortPicker();

  /// Levels worth warning about — they visibly slow a turn down.
  static const _slowLevels = {'xhigh', 'max'};

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(chatModelsProvider).valueOrNull;
    final efforts = data?.efforts ?? const <String>[];
    if (efforts.isEmpty) return const SizedBox.shrink();

    final selected = ref.watch(selectedEffortProvider);
    final fallback = (data?.defaultEffort.isNotEmpty ?? false)
        ? data!.defaultEffort
        : efforts.first;
    final current = efforts.contains(selected) ? selected! : fallback;
    final value = efforts.contains(current) ? current : efforts.first;

    return Tooltip(
      message: 'Effort de raisonnement\nxhigh/max : nettement plus lent',
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.bolt,
              size: 16,
              color: _slowLevels.contains(value)
                  ? Theme.of(context).colorScheme.tertiary
                  : Theme.of(context).iconTheme.color?.withValues(alpha: 0.7),
            ),
            const SizedBox(width: 2),
            DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: value,
                isDense: true,
                icon: const Icon(Icons.expand_more, size: 18),
                borderRadius: BorderRadius.circular(8),
                style: Theme.of(context).textTheme.bodySmall,
                items: [
                  for (final e in efforts)
                    DropdownMenuItem(value: e, child: Text(e)),
                ],
                onChanged: (e) {
                  if (e == null) return;
                  ref.read(selectedEffortProvider.notifier).state = e;
                  ref.read(chatProvider.notifier).setEffort(e);
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// App-bar toggle asking the agent to surface a readable reasoning summary.
///
/// Honest UX note (measured, not assumed): the classic models (sonnet-4-6, haiku)
/// stream their thinking regardless of this toggle, while opus-4-7/4-8 fill the
/// summary only sporadically — so this can legitimately light up and still show
/// nothing. That's the model being terse, not a bug.
class _ThinkingToggle extends ConsumerWidget {
  const _ThinkingToggle();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final on = ref.watch(showThinkingProvider);
    return IconButton(
      icon: Icon(on ? Icons.psychology : Icons.psychology_outlined, size: 20),
      color: on ? Theme.of(context).colorScheme.primary : null,
      tooltip: on
          ? 'Raisonnement visible — actif\n(les modèles forts le montrent sur les questions complexes ; haiku, toujours)'
          : 'Afficher le raisonnement de l\'agent',
      onPressed: () {
        final next = !on;
        ref.read(showThinkingProvider.notifier).state = next;
        ref.read(chatProvider.notifier).setShowThinking(next);
      },
    );
  }
}
