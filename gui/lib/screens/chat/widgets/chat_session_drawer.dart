part of '../chat_screen.dart';

/// Sessions sidebar — the chat-session list with quick switch, plus create /
/// rename / tag / archive / delete. Extracted from _ChatScreenState into a pure
/// ConsumerWidget: it reads chatProvider / filteredSessionsProvider /
/// sessionsProvider itself and depends on NO ChatScreen instance state. Behaviour
/// is locked by the drawer parcours in integration_test/chat_flow_test.dart.
class _SessionsDrawer extends ConsumerWidget {
  const _SessionsDrawer();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final chatState = ref.watch(chatProvider);
    return Drawer(
      child: Column(
        children: [
          DrawerHeader(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primary,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Sessions',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: Theme.of(context).colorScheme.onPrimary,
                  ),
                ),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () async {
                      Navigator.pop(context);
                      await ref.read(chatProvider.notifier).newSession();
                      // Refresh the sessions list
                      ref.invalidate(filteredSessionsProvider);
                    },
                    icon: const Icon(Icons.add),
                    label: const Text('Nouvelle'),
                  ),
                ),
              ],
            ),
          ),
          // Sessions list
          Expanded(
            child: ref.watch(filteredSessionsProvider).when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, st) => Center(
                child: Text('Erreur: $err'),
              ),
              data: (sessions) {
                if (sessions.isEmpty) {
                  return Center(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(
                        'Aucune session créée.\nCliquez sur "Nouvelle" pour commencer.',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  );
                }
                return ListView.builder(
                  itemCount: sessions.length,
                  itemBuilder: (context, index) {
                    final session = sessions[index];
                    final isActive = chatState.sessionId == session.sessionId;
                    return Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        ListTile(
                          title: Text(session.name),
                          subtitle: Text(
                            '${session.messageCount} messages',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          selected: isActive,
                          selectedTileColor:
                              Theme.of(context).colorScheme.primaryContainer,
                          onTap: () {
                            // Switch to this session (pass name + tags for AppBar)
                            ref.read(chatProvider.notifier).setSessionId(
                              session.sessionId,
                              name: session.name,
                              tags: session.tags,
                            );
                            Navigator.pop(context);
                          },
                          trailing: PopupMenuButton(
                            itemBuilder: (context) => [
                              PopupMenuItem(
                                child: const Text('Renommer'),
                                onTap: () {
                                  _showRenameDialog(context, ref, session);
                                },
                              ),
                              PopupMenuItem(
                                child: const Text('Ajouter un tag'),
                                onTap: () {
                                  _showAddTagDialog(context, ref, session);
                                },
                              ),
                              PopupMenuItem(
                                child: Text(
                                  session.archived ? 'Restaurer' : 'Archiver',
                                ),
                                onTap: () {
                                  ref
                                      .read(sessionsProvider)
                                      .toggleArchive(session.sessionId, !session.archived);
                                },
                              ),
                              PopupMenuItem(
                                child: const Text('Supprimer'),
                                onTap: () {
                                  ref.read(sessionsProvider).deleteSession(session.sessionId);
                                },
                              ),
                            ],
                          ),
                        ),
                        // Tags displayed below the tile, outside ListTile constraints
                        if (session.tags.isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
                            child: Wrap(
                              spacing: 4,
                              runSpacing: 2,
                              children: session.tags.map((tag) => GestureDetector(
                                onLongPress: () {
                                  ref.read(sessionsProvider).removeTag(session.sessionId, tag);
                                  ref.invalidate(filteredSessionsProvider);
                                },
                                child: Chip(
                                  label: Text(tag),
                                  labelStyle: Theme.of(context).textTheme.labelSmall,
                                  padding: EdgeInsets.zero,
                                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                  visualDensity: VisualDensity.compact,
                                ),
                              )).toList(),
                            ),
                          ),
                      ],
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  void _showRenameDialog(BuildContext context, WidgetRef ref, ChatSessionPreview session) {
    final controller = TextEditingController(text: session.name);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Renommer la session'),
        content: TextField(
          controller: controller,
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Annuler'),
          ),
          ElevatedButton(
            onPressed: () {
              if (controller.text.trim().isNotEmpty) {
                ref
                    .read(sessionsProvider)
                    .renameSession(session.sessionId, controller.text.trim());
                Navigator.pop(context);
              }
            },
            child: const Text('Renommer'),
          ),
        ],
      ),
    );
  }

  void _showAddTagDialog(BuildContext context, WidgetRef ref, ChatSessionPreview session) {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Ajouter un tag'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(hintText: 'ex: Confluence, important...'),
          onSubmitted: (v) {
            if (v.trim().isNotEmpty) {
              ref.read(sessionsProvider).addTag(session.sessionId, v.trim());
              ref.invalidate(filteredSessionsProvider);
              Navigator.pop(context);
            }
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Annuler'),
          ),
          ElevatedButton(
            onPressed: () {
              if (controller.text.trim().isNotEmpty) {
                ref.read(sessionsProvider).addTag(session.sessionId, controller.text.trim());
                ref.invalidate(filteredSessionsProvider);
                Navigator.pop(context);
              }
            },
            child: const Text('Ajouter'),
          ),
        ],
      ),
    );
  }
}
