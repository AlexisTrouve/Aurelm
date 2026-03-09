import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../models/entity_with_details.dart';
import '../../../providers/database_provider.dart';
import '../../../widgets/common/entity_type_icon.dart';
import '../../../widgets/common/entity_type_badge.dart';

class EntityListTile extends ConsumerWidget {
  final EntityWithDetails entity;

  const EntityListTile({super.key, required this.entity});

  Future<void> _confirmDisable(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Désactiver cette entité ?'),
        content: const Text(
          'L\'entité sera retirée de toutes les vues.\n\n'
          'Vous pourrez la réactiver depuis la vue "Désactivées".',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Désactiver'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      final db = ref.read(databaseProvider);
      if (db == null) return;
      await db.entityDao.setEntityDisabled(entity.entity.id, disabled: true);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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
            // Badge visible only when showHidden is active
            if (entity.entity.hidden) ...[
              const SizedBox(width: 8),
              const Tooltip(
                message: 'Entité cachée',
                child: Icon(Icons.visibility_off, size: 14, color: Colors.grey),
              ),
            ],
          ],
        ),
        // Quick-action buttons: hide and disable
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Hide toggle — icône œil
            Tooltip(
              message: entity.entity.hidden
                  ? 'Afficher (retirer du masquage)'
                  : 'Cacher de la vue principale',
              child: IconButton(
                icon: Icon(
                  entity.entity.hidden ? Icons.visibility : Icons.visibility_off,
                  size: 18,
                  color: entity.entity.hidden ? Colors.orange : Colors.grey,
                ),
                onPressed: () async {
                  final db = ref.read(databaseProvider);
                  if (db == null) return;
                  await db.entityDao.setEntityHidden(
                    entity.entity.id,
                    hidden: !entity.entity.hidden,
                  );
                },
              ),
            ),
            // Disable — icône block, avec confirmation
            Tooltip(
              message: 'Désactiver (retrait complet)',
              child: IconButton(
                icon: const Icon(Icons.block, size: 18, color: Colors.grey),
                onPressed: () => _confirmDisable(context, ref),
              ),
            ),
          ],
        ),
        onTap: () => context.push('/entities/${entity.entity.id}'),
      ),
    );
  }
}
