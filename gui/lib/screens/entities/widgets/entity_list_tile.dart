import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../models/entity_with_details.dart';
import '../../../widgets/common/entity_type_icon.dart';
import '../../../widgets/common/entity_type_badge.dart';

class EntityListTile extends StatelessWidget {
  final EntityWithDetails entity;

  const EntityListTile({super.key, required this.entity});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: EntityTypeIcon(
          entityType: entity.entity.entityType,
          size: 28,
        ),
        title: Text(
          entity.entity.canonicalName,
          style: const TextStyle(fontWeight: FontWeight.w500),
        ),
        subtitle: Row(
          children: [
            EntityTypeBadge(
              entityType: entity.entity.entityType,
              compact: true,
            ),
            const SizedBox(width: 8),
            Text(
              '${entity.mentionCount} mentions',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
          ],
        ),
        onTap: () => context.go('/entities/${entity.entity.id}'),
      ),
    );
  }
}
