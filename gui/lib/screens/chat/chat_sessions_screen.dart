import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/chat_sessions_provider.dart';

/// Screen listing all chat sessions with filtering and management options.
class ChatSessionsScreen extends ConsumerWidget {
  const ChatSessionsScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter = ref.watch(sessionsFilterProvider);
    final sessionsAsync = ref.watch(filteredSessionsProvider);
    final tagsAsync = ref.watch(allSessionTagsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Chat Sessions'),
        elevation: 0,
      ),
      body: Column(
        children: [
          // Filter bar
          Container(
            color: Theme.of(context).appBarTheme.backgroundColor,
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Archive toggle
                Row(
                  children: [
                    Checkbox(
                      value: filter.archived,
                      onChanged: (val) {
                        ref.read(sessionsFilterProvider.notifier).state =
                            filter.copyWith(archived: val ?? false);
                      },
                    ),
                    const Text('Show Archived'),
                  ],
                ),
                // Tag filter dropdown
                tagsAsync.when(
                  data: (tags) => DropdownButton<String?>(
                    value: filter.selectedTag,
                    onChanged: (tag) {
                      ref.read(sessionsFilterProvider.notifier).state =
                          filter.copyWith(selectedTag: tag, clearTag: tag == null);
                    },
                    items: [
                      const DropdownMenuItem(
                        value: null,
                        child: Text('All Tags'),
                      ),
                      ...tags.map((tag) => DropdownMenuItem(
                        value: tag,
                        child: Text(tag),
                      )),
                    ],
                  ),
                  loading: () => const CircularProgressIndicator(),
                  error: (err, st) => Text('Error: $err'),
                ),
              ],
            ),
          ),
          // Sessions list
          Expanded(
            child: sessionsAsync.when(
              data: (sessions) {
                if (sessions.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.chat_bubble_outline, size: 64, color: Colors.grey),
                        const SizedBox(height: 16),
                        const Text('No sessions found'),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: () => _showCreateDialog(context, ref),
                          child: const Text('Create New Session'),
                        ),
                      ],
                    ),
                  );
                }

                return ListView.builder(
                  itemCount: sessions.length,
                  itemBuilder: (context, idx) {
                    final session = sessions[idx];
                    return _SessionCard(session: session);
                  },
                );
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, st) => Center(child: Text('Error: $err')),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateDialog(context, ref),
        child: const Icon(Icons.add),
      ),
    );
  }

  void _showCreateDialog(BuildContext context, WidgetRef ref) {
    final nameController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Create New Session'),
        content: TextField(
          controller: nameController,
          decoration: const InputDecoration(
            hintText: 'Session name...',
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final name = nameController.text.trim();
              if (name.isEmpty) return;

              try {
                final sessionId = await ref
                    .read(sessionsProvider)
                    .createSession(name);

                if (context.mounted) {
                  Navigator.pop(context);
                  // Refresh sessions list
                  // ignore: unused_result
                  ref.refresh(filteredSessionsProvider);
                  // Navigate to chat with this session
                  context.go('/chat', extra: sessionId);
                }
              } catch (e) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Error: $e')),
                );
              }
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }
}

/// A single session card with preview and action buttons.
class _SessionCard extends ConsumerWidget {
  final ChatSessionPreview session;

  const _SessionCard({
    super.key,
    required this.session,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: ListTile(
        onTap: () {
          // Load session into chat and navigate
          context.go('/chat', extra: session.sessionId);
        },
        title: Text(session.name),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (session.lastMessage != null)
              Text(
                session.lastMessage!,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12, color: Colors.grey),
              ),
            const SizedBox(height: 4),
            Wrap(
              spacing: 4,
              children: [
                Chip(
                  label: Text('${session.messageCount} msgs'),
                  visualDensity: VisualDensity.compact,
                ),
                ...session.tags.map((tag) => Chip(
                  label: Text(tag),
                  visualDensity: VisualDensity.compact,
                  backgroundColor: Colors.amber.withAlpha(100),
                )),
              ],
            ),
          ],
        ),
        trailing: PopupMenuButton<String>(
          onSelected: (action) async {
            switch (action) {
              case 'rename':
                _showRenameDialog(context, ref);
              case 'archive':
                await ref.read(sessionsProvider)
                    .toggleArchive(session.sessionId, !session.archived);
                // ignore: unused_result
                ref.refresh(filteredSessionsProvider);
              case 'delete':
                final confirm = await showDialog<bool>(
                  context: context,
                  builder: (ctx) => AlertDialog(
                    title: const Text('Delete Session?'),
                    content: const Text('This cannot be undone.'),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(ctx, false),
                        child: const Text('Cancel'),
                      ),
                      ElevatedButton(
                        onPressed: () => Navigator.pop(ctx, true),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.red,
                        ),
                        child: const Text('Delete'),
                      ),
                    ],
                  ),
                );
                if (confirm == true) {
                  await ref.read(sessionsProvider)
                      .deleteSession(session.sessionId);
                  // ignore: unused_result
                  ref.refresh(filteredSessionsProvider);
                }
            }
          },
          itemBuilder: (context) => [
            PopupMenuItem(
              value: 'rename',
              child: const Text('Rename'),
            ),
            PopupMenuItem(
              value: 'archive',
              child: Text(session.archived ? 'Unarchive' : 'Archive'),
            ),
            PopupMenuItem(
              value: 'delete',
              child: const Text('Delete'),
            ),
          ],
        ),
      ),
    );
  }

  void _showRenameDialog(BuildContext context, WidgetRef ref) {
    final nameController = TextEditingController(text: session.name);

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rename Session'),
        content: TextField(
          controller: nameController,
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final newName = nameController.text.trim();
              if (newName.isEmpty || newName == session.name) {
                Navigator.pop(context);
                return;
              }

              await ref.read(sessionsProvider)
                  .renameSession(session.sessionId, newName);
              // ignore: unused_result
              ref.refresh(filteredSessionsProvider);
              if (context.mounted) Navigator.pop(context);
            },
            child: const Text('Rename'),
          ),
        ],
      ),
    );
  }
}
