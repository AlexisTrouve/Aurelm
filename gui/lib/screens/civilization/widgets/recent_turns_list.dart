import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/app_constants.dart';
import '../../../core/theme/app_colors.dart';
import '../../../models/turn_with_entities.dart';
import '../../../providers/turn_provider.dart';
import '../../../providers/database_provider.dart';

class RecentTurnsList extends ConsumerWidget {
  final int civId;

  const RecentTurnsList({super.key, required this.civId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final db = ref.watch(databaseProvider);
    if (db == null) return const SizedBox.shrink();

    // Watch timeline filtered by this civ, limited to recent
    return StreamBuilder<List<TurnWithEntities>>(
      stream: db.turnDao.watchTimeline(
        civId: civId,
        limit: AppConstants.recentTurnsLimit,
      ),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        final turns = snapshot.data ?? [];
        if (turns.isEmpty) {
          return const Text('No turns recorded yet');
        }

        return Card(
          child: Column(
            children: turns.map((t) {
              final typeColor =
                  AppColors.turnTypeColors[t.turn.turnType] ?? Colors.grey;
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: typeColor.withOpacity(0.2),
                  child: Text(
                    '${t.turn.turnNumber}',
                    style: TextStyle(
                      color: typeColor,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                title: Text(t.turn.title ?? 'Turn ${t.turn.turnNumber}'),
                subtitle: t.turn.summary != null
                    ? Text(
                        t.turn.summary!,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      )
                    : null,
                trailing: Text(
                  '${t.entityCount} entities',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              );
            }).toList(),
          ),
        );
      },
    );
  }
}
