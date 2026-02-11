import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../providers/bot_provider.dart';
import '../../../providers/pipeline_provider.dart';

class PipelineStatusCard extends ConsumerWidget {
  const PipelineStatusCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lastRun = ref.watch(lastPipelineRunProvider);
    final botHealth = ref.watch(botHealthProvider);
    final syncState = ref.watch(syncStateProvider);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Bot status row
            Row(
              children: [
                botHealth.when(
                  loading: () => const Icon(Icons.circle, size: 12, color: Colors.grey),
                  error: (_, __) => const Icon(Icons.circle, size: 12, color: Colors.red),
                  data: (healthy) => Icon(
                    Icons.circle,
                    size: 12,
                    color: healthy ? Colors.green : Colors.red,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  botHealth.when(
                    loading: () => 'Bot: checking...',
                    error: (_, __) => 'Bot: offline',
                    data: (healthy) => healthy ? 'Bot: online' : 'Bot: offline',
                  ),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const Spacer(),
                // Sync button
                _SyncButton(syncState: syncState, ref: ref),
              ],
            ),
            const Divider(height: 24),
            // Pipeline run info
            lastRun.when(
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
              data: (run) {
                if (run == null) {
                  return Row(
                    children: [
                      Icon(Icons.info_outline,
                          color: Theme.of(context).colorScheme.onSurfaceVariant),
                      const SizedBox(width: 12),
                      const Expanded(
                        child: Text('Pipeline has not been run yet'),
                      ),
                    ],
                  );
                }

                final statusColor = switch (run.status) {
                  'completed' => AppColors.success,
                  'running' => Colors.blue,
                  'failed' => AppColors.error,
                  _ => Colors.grey,
                };

                return Row(
                  children: [
                    Icon(
                      run.status == 'completed'
                          ? Icons.check_circle
                          : run.status == 'running'
                              ? Icons.sync
                              : Icons.error,
                      color: statusColor,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Last pipeline run: ${run.status}'),
                          Text(
                            '${run.messagesProcessed ?? 0} messages, '
                            '${run.turnsCreated ?? 0} turns, '
                            '${run.entitiesExtracted ?? 0} entities',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    Text(
                      run.completedAt ?? run.startedAt,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                );
              },
            ),
            // Sync result
            if (syncState.status == SyncStatus.success && syncState.result != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Sync: ${syncState.result!['messages_fetched'] ?? 0} fetched, '
                  '${syncState.result!['pipeline']?['total_turns_created'] ?? 0} turns created',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.success,
                      ),
                ),
              ),
            if (syncState.status == SyncStatus.error)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Sync error: ${syncState.error}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.error,
                      ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _SyncButton extends StatelessWidget {
  final SyncState syncState;
  final WidgetRef ref;

  const _SyncButton({required this.syncState, required this.ref});

  @override
  Widget build(BuildContext context) {
    final isSyncing = syncState.status == SyncStatus.syncing;

    return FilledButton.tonalIcon(
      onPressed: isSyncing
          ? null
          : () => ref.read(syncStateProvider.notifier).triggerSync(),
      icon: isSyncing
          ? const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.sync),
      label: Text(isSyncing ? 'Syncing...' : 'Sync'),
    );
  }
}
