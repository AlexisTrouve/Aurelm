import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../data/daos/entity_dao.dart';
import '../../../providers/entity_provider.dart';

/// Displays the chronological naming history of an entity.
/// Shows a horizontal chain: "Nés sans ciel (T3) → Sans-Ciel (T7) → ..."
/// Each alias is a tappable chip linking to the turn where it first appeared.
class NamingHistory extends ConsumerWidget {
  final int entityId;

  const NamingHistory({super.key, required this.entityId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final historyAsync = ref.watch(namingHistoryProvider(entityId));

    return historyAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (history) {
        // Only show if there are actual aliases (more than just the canonical name)
        if (history.length <= 1) return const SizedBox.shrink();

        return Wrap(
          spacing: 4,
          runSpacing: 4,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: _buildChain(context, history),
        );
      },
    );
  }

  List<Widget> _buildChain(
      BuildContext context, List<AliasHistoryEntry> history) {
    final theme = Theme.of(context);
    final widgets = <Widget>[];

    for (int i = 0; i < history.length; i++) {
      final entry = history[i];

      // Arrow between entries
      if (i > 0) {
        widgets.add(Icon(
          Icons.arrow_forward,
          size: 14,
          color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
        ));
      }

      widgets.add(_NameChip(entry: entry));
    }

    return widgets;
  }
}

class _NameChip extends StatelessWidget {
  final AliasHistoryEntry entry;

  const _NameChip({required this.entry});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasLink = entry.turnId != null;

    // Current canonical name gets a highlighted style
    final bgColor = entry.isCurrent
        ? theme.colorScheme.primaryContainer
        : theme.colorScheme.surfaceContainerHighest;
    final textColor = entry.isCurrent
        ? theme.colorScheme.onPrimaryContainer
        : theme.colorScheme.onSurfaceVariant;

    final label = entry.turnNumber != null
        ? '${entry.name} (T${entry.turnNumber})'
        : entry.name;

    final chip = Chip(
      label: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          color: textColor,
          fontWeight:
              entry.isCurrent ? FontWeight.bold : FontWeight.normal,
        ),
      ),
      backgroundColor: bgColor,
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
      visualDensity: VisualDensity.compact,
    );

    if (!hasLink) return chip;

    // Tappable: navigate to the turn and highlight the entity name
    return GestureDetector(
      onTap: () => context.push(
        '/turns/${entry.turnId}',
        extra: {'highlight': entry.name},
      ),
      child: chip,
    );
  }
}
