import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../providers/entity_provider.dart';
import '../../../widgets/common/entity_type_icon.dart';
import '../../../widgets/common/entity_type_badge.dart';

class TopEntitiesList extends ConsumerWidget {
  final int civId;

  const TopEntitiesList({super.key, required this.civId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final topEntities = ref.watch(topEntitiesProvider(civId));

    return topEntities.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => const Text('Error loading entities'),
      data: (entities) {
        if (entities.isEmpty) {
          return const Text('No entities found');
        }

        return Card(
          child: Column(
            children: entities.map((e) {
              return ListTile(
                leading: EntityTypeIcon(entityType: e.entity.entityType),
                title: Text(e.entity.canonicalName),
                subtitle: EntityTypeBadge(
                  entityType: e.entity.entityType,
                  compact: true,
                ),
                trailing: Text(
                  '${e.mentionCount} mentions',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                onTap: () => context.go('/entities/${e.entity.id}'),
              );
            }).toList(),
          ),
        );
      },
    );
  }
}
