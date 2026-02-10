import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../providers/pipeline_provider.dart';

class PipelineStatusCard extends ConsumerWidget {
  const PipelineStatusCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lastRun = ref.watch(lastPipelineRunProvider);

    return lastRun.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (run) {
        if (run == null) {
          return Card(
            child: ListTile(
              leading: Icon(Icons.info_outline,
                  color: Theme.of(context).colorScheme.onSurfaceVariant),
              title: const Text('Pipeline has not been run yet'),
              subtitle: const Text('Run the ML pipeline to import game data'),
            ),
          );
        }

        final statusColor = switch (run.status) {
          'completed' => AppColors.success,
          'running' => Colors.blue,
          'failed' => AppColors.error,
          _ => Colors.grey,
        };

        return Card(
          child: ListTile(
            leading: Icon(
              run.status == 'completed'
                  ? Icons.check_circle
                  : run.status == 'running'
                      ? Icons.sync
                      : Icons.error,
              color: statusColor,
            ),
            title: Text('Last pipeline run: ${run.status}'),
            subtitle: Text(
              '${run.messagesProcessed ?? 0} messages, '
              '${run.turnsCreated ?? 0} turns, '
              '${run.entitiesExtracted ?? 0} entities',
            ),
            trailing: Text(
              run.completedAt ?? run.startedAt,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        );
      },
    );
  }
}
