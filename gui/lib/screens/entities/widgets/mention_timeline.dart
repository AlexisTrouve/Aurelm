import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../providers/entity_provider.dart';
import '../../../widgets/common/civ_badge.dart';

class MentionTimeline extends ConsumerWidget {
  final int entityId;
  // Used as highlight text when navigating to the turn detail
  final String entityName;

  const MentionTimeline({super.key, required this.entityId, required this.entityName});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mentions = ref.watch(entityMentionsProvider(entityId));

    return mentions.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => const Text('Error loading mentions'),
      data: (mentionList) {
        if (mentionList.isEmpty) {
          return Text(
            'No mentions recorded',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          );
        }

        return Card(
          child: Column(
            children: mentionList.map((m) {
              return ListTile(
                dense: true,
                leading: CircleAvatar(
                  radius: 14,
                  child: Text(
                    '${m.turnNumber}',
                    style: const TextStyle(fontSize: 11),
                  ),
                ),
                title: Text(
                  m.turnTitle ?? 'Turn ${m.turnNumber}',
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
                subtitle: m.mention.context != null
                    ? Text(
                        m.mention.context!,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      )
                    : Text(
                        '"${m.mention.mentionText}"',
                        style: const TextStyle(fontStyle: FontStyle.italic),
                      ),
                trailing: CivBadge(civName: m.civName),
                // Fast travel → turn detail, auto-highlight the entity name
                onTap: () => context.push(
                  '/turns/${m.mention.turnId}',
                  extra: {'highlight': m.mention.mentionText ?? entityName},
                ),
              );
            }).toList(),
          ),
        );
      },
    );
  }
}
