import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../models/civ_with_stats.dart';

class CivSummaryCard extends StatelessWidget {
  final CivWithStats civWithStats;

  const CivSummaryCard({super.key, required this.civWithStats});

  @override
  Widget build(BuildContext context) {
    final civ = civWithStats.civ;
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => context.go('/civs/${civ.id}'),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.public, color: colorScheme.primary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      civ.name,
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.bold),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              if (civ.playerName != null) ...[
                const SizedBox(height: 4),
                Text(
                  'Player: ${civ.playerName}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                ),
              ],
              const Spacer(),
              Row(
                children: [
                  _StatChip(
                    icon: Icons.history,
                    label: '${civWithStats.turnCount} turns',
                  ),
                  const SizedBox(width: 12),
                  _StatChip(
                    icon: Icons.category,
                    label: '${civWithStats.entityCount} entities',
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _StatChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: Theme.of(context).colorScheme.onSurfaceVariant),
        const SizedBox(width: 4),
        Text(
          label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
        ),
      ],
    );
  }
}
