import 'dart:io';

// Chat screen. The 2267-line monolith was decomposed into `part` files (same
// library, so the private widgets keep seeing each other with zero import/visibility
// churn); each `part` is a cohesive, standalone component:
//   - widgets/chat_message_parts.dart   : user-message segment parser + file/quote cards
//   - widgets/chat_message_bubble.dart  : _MessageBubble (hover actions, lore links)
//   - widgets/chat_input_bar.dart       : _InputBar + _QuotePreview (the quote strip)
//   - widgets/chat_stream_widgets.dart  : tool card, queued/summary bubbles, thinking,
//                                         pending chip, empty state, error banner
//   - widgets/chat_app_bar_pickers.dart : model / effort / thinking pickers + token badge
// This file keeps ONLY the screen State (lifecycle, send/scroll wiring) and its two
// build methods (_buildScaffold, _buildSessionsDrawer + its dialogs). The E2E net
// integration_test/chat_flow_test.dart proves the decomposition is behaviour-neutral.
//   Still a State method, not yet a widget: _buildSessionsDrawer. Extracting it is
//   mechanical (per the seam map it touches no State fields) but must wait for a
//   drawer E2E first — untested UI does not get refactored blind.

import 'package:drift/drift.dart' show Variable;
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../../providers/chat_provider.dart';
import '../../providers/bot_provider.dart';
import '../../providers/database_provider.dart';
import '../../providers/chat_sessions_provider.dart';
import '../../providers/lore_links_provider.dart';
import '../../providers/side_panel_provider.dart';
import '../../utils/lore_linker.dart';
import '../../widgets/common/side_panel.dart';

part 'widgets/chat_message_parts.dart';
part 'widgets/chat_message_bubble.dart';
part 'widgets/chat_input_bar.dart';
part 'widgets/chat_stream_widgets.dart';
part 'widgets/chat_app_bar_pickers.dart';

/// Full-page chat interface for the Aurelm AI agent.
class ChatScreen extends ConsumerStatefulWidget {
  final String? initialSessionId;

  const ChatScreen({super.key, this.initialSessionId});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  final _focusNode = FocusNode();
  // Key targeting our own Scaffold so openDrawer() doesn't hit the nav shell above.
  final _scaffoldKey = GlobalKey<ScaffoldState>();

  /// Files attached to the next message — cleared after send.
  final List<({String name, String content})> _attachments = [];

  /// Message being quoted — prepended to the next send as a blockquote.
  ChatMessage? _quotedMessage;

  @override
  void initState() {
    super.initState();

    // Restore persisted input text (survives navigation away and back)
    final savedText = ref.read(chatInputTextProvider);
    if (savedText.isNotEmpty) {
      _controller.text = savedText;
      _controller.selection =
          TextSelection.fromPosition(TextPosition(offset: savedText.length));
    }

    // Sync controller changes → persistent provider so text survives navigation
    _controller.addListener(() {
      ref.read(chatInputTextProvider.notifier).state = _controller.text;
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      // Pre-load session if provided via route extra
      if (widget.initialSessionId != null) {
        ref.read(chatProvider.notifier).setSessionId(widget.initialSessionId!);
      }
      // Jump to bottom instantly after layout settles (2 frames needed for ListView extent)
      _jumpToBottom();
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    ref.listenManual(chatProvider, (prev, next) {
      // Refresh sessions list when a chat turn completes
      if (prev?.loading == true && next.loading == false) {
        ref.invalidate(filteredSessionsProvider);
      }
      // Clear persisted input text when session changes (new or different session)
      if (prev != null && prev.sessionId != next.sessionId) {
        ref.read(chatInputTextProvider.notifier).state = '';
        _controller.clear();
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  /// Combine quoted message + typed text + file attachments into the final message string.
  String _buildMessage() {
    final text = _controller.text.trim();
    final parts = <String>[];
    // Prepend quoted message as a blockquote so the agent sees the context
    if (_quotedMessage != null) {
      final role = _quotedMessage!.role == ChatRole.user ? 'Vous' : 'Aurelm';
      final quoted = _quotedMessage!.content
          .split('\n')
          .map((l) => '> $l')
          .join('\n');
      parts.add('[$role a écrit :]\n$quoted');
    }
    if (text.isNotEmpty) parts.add(text);
    for (final att in _attachments) {
      parts.add('[Fichier: ${att.name}]\n${att.content}');
    }
    return parts.join('\n\n');
  }

  void _send() {
    final message = _buildMessage();
    if (message.isEmpty) return;
    _controller.clear();
    ref.read(chatInputTextProvider.notifier).state = '';
    setState(() {
      _attachments.clear();
      _quotedMessage = null; // clear quote after send
    });
    ref.read(chatProvider.notifier).send(message);
    // Refocus input so the user can type the next message immediately
    _focusNode.requestFocus();
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['txt', 'md', 'json', 'csv', 'py', 'dart', 'ts', 'js', 'sql'],
    );
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;
    if (file.path == null) return;
    try {
      final content = await File(file.path!).readAsString();
      setState(() => _attachments.add((name: file.name, content: content)));
    } catch (_) {
      // Unreadable file — silently ignore
    }
  }

  /// Animated scroll to bottom — used when new messages arrive during a session.
  void _scrollToBottom() {
    if (!_scrollController.hasClients) return;
    // Wait for layout to settle before scrolling
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      final maxExtent = _scrollController.position.maxScrollExtent;
      if (maxExtent <= 0) return;
      _scrollController.animateTo(
        maxExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    });
  }

  /// Instant jump to bottom — used on initial load / navigation restore.
  /// Uses a double post-frame to ensure the ListView extent is fully computed.
  void _jumpToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || !_scrollController.hasClients) return;
        _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatProvider);
    final botHealthAsync = ref.watch(botHealthProvider);
    final isOnline = botHealthAsync.valueOrNull == true;

    // Auto-scroll when new messages arrive
    ref.listen(chatProvider, (_, next) {
      if (!next.loading) {
        WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());
      }
    });


    return Focus(
      // Escape: cancel last queued message or ongoing LLM call
      autofocus: false,
      onKeyEvent: (_, event) {
        if (event is KeyDownEvent &&
            event.logicalKey == LogicalKeyboardKey.escape) {
          ref.read(chatProvider.notifier).cancelLast();
          return KeyEventResult.handled;
        }
        return KeyEventResult.ignored;
      },
      child: _buildScaffold(context, chatState, isOnline),
    );
  }

  // Build sessions drawer — list of all sessions with quick access
  Widget _buildSessionsDrawer(BuildContext context, ChatState chatState) {
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
                                  _showRenameDialog(context, session);
                                },
                              ),
                              PopupMenuItem(
                                child: const Text('Ajouter un tag'),
                                onTap: () {
                                  _showAddTagDialog(context, session);
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

  void _showRenameDialog(BuildContext context, ChatSessionPreview session) {
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

  void _showAddTagDialog(BuildContext context, ChatSessionPreview session) {
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

  Widget _buildScaffold(
      BuildContext context, ChatState chatState, bool isOnline) {
    return SelectionArea(
      child: Scaffold(
        key: _scaffoldKey,
        drawer: _buildSessionsDrawer(context, chatState),
        appBar: AppBar(
        // When a session is open: back button + hamburger to open sessions drawer.
        // leadingWidth widened to fit both icons side by side.
        leadingWidth: chatState.sessionId != null ? 96 : 56,
        leading: chatState.sessionId != null
            ? Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back),
                    tooltip: 'Liste des sessions',
                    onPressed: () => context.go('/chat/sessions'),
                  ),
                  IconButton(
                    icon: const Icon(Icons.menu),
                    tooltip: 'Sessions',
                    onPressed: () => _scaffoldKey.currentState?.openDrawer(),
                  ),
                ],
              )
            : null,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Flexible(
              child: Text(
                chatState.sessionName.isNotEmpty
                    ? chatState.sessionName
                    : 'Aurelm Agent',
                overflow: TextOverflow.ellipsis,
              ),
            ),
            // Session tags as small chips next to the title
            if (chatState.sessionTags.isNotEmpty) ...[
              const SizedBox(width: 8),
              ...chatState.sessionTags.map((tag) => Padding(
                padding: const EdgeInsets.only(right: 4),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    tag,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: Theme.of(context).colorScheme.onPrimaryContainer,
                    ),
                  ),
                ),
              )),
            ],
          ],
        ),
        actions: [
          // Model picker — any model the etheryale proxy serves.
          const _ModelPicker(),
          // How hard the agent reasons on the next turn.
          const _EffortPicker(),
          // Ask for a readable reasoning summary.
          const _ThinkingToggle(),
          // Online/offline indicator
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.circle,
                  size: 10,
                  color: isOnline ? Colors.green : Colors.red,
                ),
                const SizedBox(width: 6),
                Text(
                  isOnline ? 'En ligne' : 'Hors ligne',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          // Token usage — context size / max budget
          if (chatState.inputTokens > 0)
            _TokenUsageBadge(
              contextTokens: chatState.inputTokens,
              maxTokens: 60000,
            ),
          // New conversation button
          IconButton(
            icon: const Icon(Icons.add_comment_outlined),
            tooltip: 'Nouvelle conversation',
            onPressed: () async {
              await ref.read(chatProvider.notifier).newSession();
              if (mounted) ref.invalidate(filteredSessionsProvider);
            },
          ),
          // Session actions menu (duplicate, copy conversation)
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert),
            tooltip: 'Actions session',
            onSelected: (value) async {
              switch (value) {
                case 'duplicate':
                  await ref.read(chatProvider.notifier).duplicateCurrentSession();
                  if (mounted) ref.invalidate(filteredSessionsProvider);
                case 'copy_conv':
                  ref.read(chatProvider.notifier).copyConversation();
              }
            },
            itemBuilder: (_) => [
              const PopupMenuItem(
                value: 'duplicate',
                child: ListTile(
                  leading: Icon(Icons.copy_all, size: 18),
                  title: Text('Dupliquer la session'),
                  dense: true,
                ),
              ),
              const PopupMenuItem(
                value: 'copy_conv',
                child: ListTile(
                  leading: Icon(Icons.content_copy, size: 18),
                  title: Text('Copier la conversation'),
                  dense: true,
                ),
              ),
            ],
          ),
        ],
      ),
      body: Row(
        children: [
          // Chat column — takes remaining space
          Expanded(
            child: Column(
              children: [
                // Message list + queued messages
                Expanded(
                  child: (chatState.messages.isEmpty &&
                          chatState.messageQueue.isEmpty)
                      ? _EmptyState(isOnline: isOnline)
                      : ListView.builder(
                          controller: _scrollController,
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 12),
                          // Regular messages + optional fused queue bubble
                          itemCount: chatState.messages.length +
                              (chatState.messageQueue.isNotEmpty ? 1 : 0),
                          itemBuilder: (context, index) {
                            if (index < chatState.messages.length) {
                              final msg = chatState.messages[index];
                              // Compress/resume blocks get a distinct system-style bubble
                              if (msg.messageType == MessageType.compress ||
                                  msg.messageType == MessageType.resume) {
                                return _SummaryBubble(message: msg);
                              }
                              return _MessageBubble(
                                message: msg,
                                index: index,
                                onQuote: (m) => setState(() => _quotedMessage = m),
                              );
                            }
                            // All queued messages fused into a single faded bubble
                            return _QueuedMessageBubble(
                              text: chatState.messageQueue.join('\n'),
                              onCancel: () =>
                                  ref.read(chatProvider.notifier).cancelLast(),
                            );
                          },
                        ),
                ),

                // Pending tool calls (shown with spinner as tools execute)
                if (chatState.pendingTools.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: chatState.pendingTools
                          .map((p) => _PendingToolChip(pending: p))
                          .toList(),
                    ),
                  ),

                // Loading indicator
                if (chatState.loading)
                  const LinearProgressIndicator(minHeight: 2),

                // Error banner
                if (chatState.error != null)
                  _ErrorBanner(
                    error: chatState.error!,
                    onDismiss: () =>
                        ref.read(chatProvider.notifier).newSession(),
                  ),

                // Input bar (with optional quote preview)
                _InputBar(
                  controller: _controller,
                  focusNode: _focusNode,
                  enabled: isOnline,
                  onSend: _send,
                  onPickFile: _pickFile,
                  attachments: _attachments,
                  onRemoveAttachment: (i) => setState(() => _attachments.removeAt(i)),
                  quotedMessage: _quotedMessage,
                  onClearQuote: () => setState(() => _quotedMessage = null),
                ),
              ],
            ),
          ),
          // Side panel — lore detail views (max 40% width, 3 slots) on RIGHT
          const SidePanel(),
        ],
      ),
      ),
    );
  }
}
