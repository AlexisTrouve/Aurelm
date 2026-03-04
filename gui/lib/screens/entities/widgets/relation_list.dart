import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../providers/database_provider.dart';
import '../../../data/daos/relation_dao.dart';

/// Shows all relations for an entity, with the related entity's canonical name
/// resolved via a JOIN (no N+1 queries).
class RelationList extends ConsumerWidget {
  final int entityId;

  const RelationList({super.key, required this.entityId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final db = ref.watch(databaseProvider);
    if (db == null) return const SizedBox.shrink();

    return StreamBuilder<List<RelationWithNames>>(
      stream: db.relationDao.watchRelationsWithNamesForEntity(entityId),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        final relations = snapshot.data ?? [];
        if (relations.isEmpty) {
          return Text(
            'Aucune relation',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          );
        }

        final outgoing =
            relations.where((r) => r.isOutgoing).toList();
        final incoming =
            relations.where((r) => !r.isOutgoing).toList();

        return Card(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (outgoing.isNotEmpty) ...[
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                  child: Text(
                    'Vers',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                ),
                ...outgoing.map((r) => _RelationTile(relation: r)),
              ],
              if (incoming.isNotEmpty) ...[
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                  child: Text(
                    'Depuis',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                ),
                ...incoming.map((r) => _RelationTile(relation: r)),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _RelationTile extends StatelessWidget {
  final RelationWithNames relation;

  const _RelationTile({required this.relation});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      dense: true,
      leading: Icon(
        relation.isOutgoing ? Icons.arrow_forward : Icons.arrow_back,
        size: 18,
      ),
      // Show the related entity name prominently
      title: Text(
        relation.relatedName,
        style: const TextStyle(fontWeight: FontWeight.w500),
      ),
      // Show relation type + optional description as subtitle
      subtitle: Text(
        relation.relation.description != null
            ? '${relation.relation.relationType.replaceAll('_', ' ')} · ${relation.relation.description}'
            : relation.relation.relationType.replaceAll('_', ' '),
      ),
      trailing: const Icon(Icons.chevron_right, size: 18),
      onTap: () => context.go('/entities/${relation.relatedEntityId}'),
    );
  }
}
