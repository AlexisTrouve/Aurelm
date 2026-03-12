import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/entity_provider.dart';
import '../../providers/database_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/entity_type_badge.dart';
import '../../widgets/common/section_header.dart';
import 'widgets/naming_history.dart';
import 'widgets/notes_menu_button.dart';
import 'widgets/relation_list.dart';
import 'widgets/mention_timeline.dart';

class EntityDetailScreen extends ConsumerWidget {
  final int entityId;

  const EntityDetailScreen({super.key, required this.entityId});

  Future<void> _confirmDisable(
      BuildContext context, WidgetRef ref, bool currentlyDisabled) async {
    if (currentlyDisabled) {
      // Reactivate without confirmation
      final db = ref.read(databaseProvider);
      if (db == null) return;
      await db.entityDao.setEntityDisabled(entityId, disabled: false);
      return;
    }
    // Disable requires confirmation
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Désactiver cette entité ?'),
        content: const Text(
          'L\'entité sera retirée de toutes les vues et les liens vers elle '
          'ne seront plus cliquables.\n\n'
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
      await db.entityDao.setEntityDisabled(entityId, disabled: true);
      if (context.mounted) {
        if (context.canPop()) context.pop();
        else context.go('/entities');
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final entityAsync = ref.watch(entityDetailProvider(entityId));

    return entityAsync.when(
      loading: () => const Scaffold(body: LoadingIndicator()),
      error: (e, _) => Scaffold(body: ErrorView(message: e.toString())),
      data: (entity) {
        if (entity == null) {
          return SelectionArea(
            child: Scaffold(
              appBar: AppBar(),
              body: const Center(child: Text('Entity not found')),
            ),
          );
        }

        return SelectionArea(
          child: Scaffold(
          appBar: AppBar(
            toolbarHeight: 44,
            title: Text(entity.entity.canonicalName),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.canPop() ? context.pop() : context.go('/entities'),
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.hub),
                tooltip: 'View in graph',
                onPressed: () => context.go('/graph', extra: {'entityId': entityId}),
              ),
              // Hide toggle
              IconButton(
                icon: Icon(
                  entity.entity.hidden ? Icons.visibility : Icons.visibility_off,
                  color: entity.entity.hidden ? Colors.orange : null,
                ),
                tooltip: entity.entity.hidden ? 'Afficher (retirer du masquage)' : 'Cacher (masquer de la vue principale)',
                onPressed: () async {
                  final db = ref.read(databaseProvider);
                  if (db == null) return;
                  await db.entityDao.setEntityHidden(
                    entityId,
                    hidden: !entity.entity.hidden,
                  );
                },
              ),
              // Disable button
              IconButton(
                icon: Icon(
                  Icons.block,
                  color: entity.entity.disabled ? Colors.red : null,
                ),
                tooltip: entity.entity.disabled
                    ? 'Réactiver cette entité'
                    : 'Désactiver cette entité (retrait complet)',
                onPressed: () => _confirmDisable(context, ref, entity.entity.disabled),
              ),
            ],
          ),
          body: NotesSideRail(
            attachment: NoteAttachment.entity,
            attachmentId: entityId,
            child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Type + mention count
                Row(
                  children: [
                    EntityTypeBadge(entityType: entity.entity.entityType),
                    const SizedBox(width: 12),
                    Text(
                      '${entity.mentionCount} mentions',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color:
                                Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                    ),
                    if (entity.entity.isActive == 0) ...[
                      const SizedBox(width: 12),
                      Chip(
                        label: const Text('Inactive'),
                        backgroundColor:
                            Theme.of(context).colorScheme.errorContainer,
                        labelStyle: TextStyle(
                          color:
                              Theme.of(context).colorScheme.onErrorContainer,
                        ),
                      ),
                    ],
                  ],
                ),

                // Description
                if (entity.entity.description != null) ...[
                  const SizedBox(height: 16),
                  Text(entity.entity.description!),
                ],

                // Naming history — chronological alias chain with turn links
                const SizedBox(height: 24),
                const SectionHeader(title: 'Historique des noms'),
                NamingHistory(entityId: entityId),

                // Relations
                const SizedBox(height: 24),
                const SectionHeader(title: 'Relations'),
                RelationList(entityId: entityId),

                // Mention timeline
                const SizedBox(height: 24),
                const SectionHeader(title: 'Mentions'),
                MentionTimeline(entityId: entityId, entityName: entity.entity.canonicalName),

              ],
            ),
          ),
          ), // NotesSideRail
          ),
        );
      },
    );
  }
}
