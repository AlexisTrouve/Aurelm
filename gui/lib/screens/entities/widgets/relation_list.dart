import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../providers/database_provider.dart';
import '../../../data/database.dart';

class RelationList extends ConsumerWidget {
  final int entityId;

  const RelationList({super.key, required this.entityId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final db = ref.watch(databaseProvider);
    if (db == null) return const SizedBox.shrink();

    return StreamBuilder<List<RelationRow>>(
      stream: db.relationDao.watchRelationsForEntity(entityId),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        final relations = snapshot.data ?? [];
        if (relations.isEmpty) {
          return Text(
            'No relations found',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          );
        }

        // Group by direction
        final outgoing =
            relations.where((r) => r.sourceEntityId == entityId).toList();
        final incoming =
            relations.where((r) => r.targetEntityId == entityId).toList();

        return Card(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (outgoing.isNotEmpty) ...[
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                  child: Text(
                    'Outgoing',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                ),
                ...outgoing.map((r) => _RelationTile(
                      relationType: r.relationType,
                      description: r.description,
                      targetEntityId: r.targetEntityId,
                      direction: 'to',
                    )),
              ],
              if (incoming.isNotEmpty) ...[
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                  child: Text(
                    'Incoming',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                ),
                ...incoming.map((r) => _RelationTile(
                      relationType: r.relationType,
                      description: r.description,
                      targetEntityId: r.sourceEntityId,
                      direction: 'from',
                    )),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _RelationTile extends StatelessWidget {
  final String relationType;
  final String? description;
  final int targetEntityId;
  final String direction;

  const _RelationTile({
    required this.relationType,
    required this.description,
    required this.targetEntityId,
    required this.direction,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      dense: true,
      leading: Icon(
        direction == 'to' ? Icons.arrow_forward : Icons.arrow_back,
        size: 18,
      ),
      title: Text(relationType.replaceAll('_', ' ')),
      subtitle: description != null ? Text(description!) : null,
      trailing: const Icon(Icons.chevron_right, size: 18),
      onTap: () => context.go('/entities/$targetEntityId'),
    );
  }
}
