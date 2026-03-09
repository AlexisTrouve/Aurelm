import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/entity_provider.dart';
import '../../providers/database_provider.dart';
import '../../providers/civilization_provider.dart';
import '../../widgets/common/empty_state.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/entity_type_badge.dart';

/// Shows all disabled entities so the MJ can review and reactivate them.
class DisabledEntitiesScreen extends ConsumerWidget {
  const DisabledEntitiesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final civs = ref.watch(civListProvider);
    // null = all civs
    final disabledAsync = ref.watch(disabledEntitiesProvider(null));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Entités désactivées'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/entities'),
        ),
      ),
      body: disabledAsync.when(
        loading: () => const LoadingIndicator(),
        error: (e, _) => Center(child: Text('Erreur: $e')),
        data: (entities) {
          if (entities.isEmpty) {
            return const EmptyState(
              icon: Icons.check_circle_outline,
              message: 'Aucune entité désactivée',
            );
          }
          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: entities.length,
            itemBuilder: (context, i) {
              final e = entities[i];
              return Card(
                child: ListTile(
                  leading: Icon(Icons.block, color: Colors.red.shade300),
                  title: Text(e.entity.canonicalName),
                  subtitle: Row(
                    children: [
                      EntityTypeBadge(entityType: e.entity.entityType, compact: true),
                      if (e.entity.disabledAt != null) ...[
                        const SizedBox(width: 8),
                        Text(
                          'Désactivée le ${e.entity.disabledAt!.substring(0, 10)}',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: Theme.of(context).colorScheme.onSurfaceVariant,
                              ),
                        ),
                      ],
                    ],
                  ),
                  trailing: FilledButton.tonal(
                    onPressed: () async {
                      final db = ref.read(databaseProvider);
                      if (db == null) return;
                      await db.entityDao.setEntityDisabled(e.entity.id, disabled: false);
                    },
                    child: const Text('Réactiver'),
                  ),
                  onTap: () => context.push('/entities/${e.entity.id}'),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
