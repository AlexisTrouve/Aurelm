import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../models/turn_with_entities.dart';
import '../../../widgets/common/civ_badge.dart';

class TimelineTurnCard extends StatelessWidget {
  final TurnWithEntities turn;

  const TimelineTurnCard({super.key, required this.turn});

  @override
  Widget build(BuildContext context) {
    final t = turn.turn;
    final typeColor = AppColors.turnTypeColors[t.turnType] ?? Colors.grey;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Turn number badge
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: typeColor.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              alignment: Alignment.center,
              child: Text(
                '${t.turnNumber}',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: typeColor,
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ),

            const SizedBox(width: 16),

            // Content
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          t.title ?? 'Turn ${t.turnNumber}',
                          style: Theme.of(context)
                              .textTheme
                              .titleSmall
                              ?.copyWith(fontWeight: FontWeight.w600),
                        ),
                      ),
                      CivBadge(civName: turn.civName),
                    ],
                  ),
                  const SizedBox(height: 4),
                  if (t.summary != null)
                    Text(
                      t.summary!,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color:
                                Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                    ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      // Turn type badge
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: typeColor.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          t.turnType.replaceAll('_', ' '),
                          style:
                              Theme.of(context).textTheme.labelSmall?.copyWith(
                                    color: typeColor,
                                    fontWeight: FontWeight.w600,
                                  ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      // Segment type badges
                      ...turn.segmentTypes.map((st) {
                        final stColor =
                            AppColors.segmentTypeColors[st] ?? Colors.grey;
                        return Padding(
                          padding: const EdgeInsets.only(right: 4),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 4, vertical: 1),
                            decoration: BoxDecoration(
                              border: Border.all(
                                  color: stColor.withOpacity(0.4)),
                              borderRadius: BorderRadius.circular(3),
                            ),
                            child: Text(
                              st,
                              style: Theme.of(context)
                                  .textTheme
                                  .labelSmall
                                  ?.copyWith(
                                    color: stColor,
                                    fontSize: 9,
                                  ),
                            ),
                          ),
                        );
                      }),
                      const Spacer(),
                      Text(
                        '${turn.entityCount} entities',
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              color: Theme.of(context)
                                  .colorScheme
                                  .onSurfaceVariant,
                            ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
