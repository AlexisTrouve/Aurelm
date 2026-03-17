import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../models/entity_with_details.dart';
import '../../../providers/database_provider.dart';
import '../../../providers/favorites_provider.dart';
import '../../../widgets/common/entity_type_icon.dart';
import '../../../widgets/common/entity_type_badge.dart';

/// Semantic tag color — matches entity_filter_bar.dart and entity_profiler.py vocab.
Color _entityTagColor(String tag) => switch (tag) {
      'militaire' => Colors.red,
      'religieux' => Colors.indigo,
      'politique' => Colors.purple,
      'economique' => Colors.green,
      'culturel' => Colors.amber,
      'diplomatique' => Colors.pink,
      'technologique' => Colors.blueGrey,
      'mythologique' => Colors.deepPurple,
      'actif' => Colors.teal,
      'disparu' => Colors.grey,
      'emergent' => Colors.cyan,
      'legendaire' => Colors.orange,
      _ => Colors.blueGrey,
    };

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
    // Parse semantic tags from JSON column (nullable — not yet tagged = empty)
    final tags = entity.entity.tags != null
        ? (jsonDecode(entity.entity.tags!) as List).cast<String>()
        : <String>[];
    final isFav = ref
        .watch(favoritesProvider)
        .contains('entity_${entity.entity.id}');

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
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
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
                if (entity.entity.hidden) ...[
                  const SizedBox(width: 8),
                  const Tooltip(
                    message: 'Entité cachée',
                    child:
                        Icon(Icons.visibility_off, size: 14, color: Colors.grey),
                  ),
                ],
              ],
            ),
            // Semantic tag chips (only shown when tags are assigned by pipeline)
            if (tags.isNotEmpty) ...[
              const SizedBox(height: 3),
              Wrap(
                spacing: 3,
                runSpacing: 2,
                children: tags.map((tag) {
                  final color = _entityTagColor(tag);
                  return Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(3),
                      border:
                          Border.all(color: color.withValues(alpha: 0.3)),
                    ),
                    child: Text(
                      tag,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: color.withValues(alpha: 0.85),
                            fontSize: 9,
                          ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ],
        ),
        // Quick-action buttons: favorite + hide + disable
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Favorite toggle
            IconButton(
              icon: Icon(
                isFav ? Icons.star : Icons.star_border,
                size: 18,
                color: isFav ? Colors.amber : Colors.grey,
              ),
              tooltip: isFav ? 'Retirer des favoris' : 'Ajouter aux favoris',
              onPressed: () => ref
                  .read(favoritesProvider.notifier)
                  .toggle('entity', entity.entity.id, entity.entity.civId),
            ),
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
