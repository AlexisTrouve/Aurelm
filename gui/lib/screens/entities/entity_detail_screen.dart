import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/entity_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/entity_type_badge.dart';
import '../../widgets/common/section_header.dart';
import 'widgets/alias_chips.dart';
import 'widgets/relation_list.dart';
import 'widgets/mention_timeline.dart';

class EntityDetailScreen extends ConsumerWidget {
  final int entityId;

  const EntityDetailScreen({super.key, required this.entityId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final entityAsync = ref.watch(entityDetailProvider(entityId));

    return entityAsync.when(
      loading: () => const Scaffold(body: LoadingIndicator()),
      error: (e, _) => Scaffold(body: ErrorView(message: e.toString())),
      data: (entity) {
        if (entity == null) {
          return Scaffold(
            appBar: AppBar(),
            body: const Center(child: Text('Entity not found')),
          );
        }

        return Scaffold(
          appBar: AppBar(
            title: Text(entity.entity.canonicalName),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.go('/entities'),
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.hub),
                tooltip: 'View in graph',
                onPressed: () => context.go('/graph'),
              ),
            ],
          ),
          body: SingleChildScrollView(
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

                // Aliases
                if (entity.aliases.isNotEmpty) ...[
                  const SizedBox(height: 24),
                  const SectionHeader(title: 'Aliases'),
                  AliasChips(aliases: entity.aliases),
                ],

                // Relations
                const SizedBox(height: 24),
                const SectionHeader(title: 'Relations'),
                RelationList(entityId: entityId),

                // Mention timeline
                const SizedBox(height: 24),
                const SectionHeader(title: 'Mentions'),
                MentionTimeline(entityId: entityId),
              ],
            ),
          ),
        );
      },
    );
  }
}
