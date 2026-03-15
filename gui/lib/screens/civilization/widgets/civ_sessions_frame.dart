import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../providers/chat_sessions_provider.dart';
import '../../../widgets/common/section_header.dart';

/// Frame affiché sur CivDetailScreen : 5 sessions récentes taggées avec la civ.
/// Dégradé silencieux si le bot est offline (liste vide).
class CivSessionsFrame extends ConsumerWidget {
  final String civName;

  const CivSessionsFrame({super.key, required this.civName});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sessionsAsync = ref.watch(civSessionsProvider(civName));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(
          title: 'Sessions',
          trailing: TextButton(
            // Navigue vers /chat/sessions avec filtre civ pré-sélectionné
            onPressed: () {
              ref.read(sessionsFilterProvider.notifier).state =
                  SessionsFilterState(selectedTag: civName);
              context.go('/chat/sessions');
            },
            child: const Text('View all'),
          ),
        ),
        sessionsAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          // Erreur réseau : masqué discrètement (bot offline)
          error: (_, __) => const SizedBox.shrink(),
          data: (sessions) {
            if (sessions.isEmpty) {
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Text(
                  'Aucune session pour cette civilisation',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                ),
              );
            }
            return Card(
              child: Column(
                children: sessions
                    .map(
                      (session) => ListTile(
                        leading: const Icon(Icons.chat_bubble_outline, size: 20),
                        title: Text(session.name),
                        subtitle: session.lastMessage != null
                            ? Text(
                                session.lastMessage!,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context).textTheme.bodySmall,
                              )
                            : Text(
                                '${session.messageCount} messages',
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                        trailing: const Icon(Icons.chevron_right, size: 18),
                        onTap: () =>
                            context.go('/chat', extra: session.sessionId),
                      ),
                    )
                    .toList(),
              ),
            );
          },
        ),
      ],
    );
  }
}
