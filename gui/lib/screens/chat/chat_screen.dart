import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../../providers/chat_provider.dart';
import '../../providers/bot_provider.dart';
import '../../providers/database_provider.dart';
import '../../providers/chat_sessions_provider.dart';
import '../../services/chat_sessions_service.dart';

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

  /// Files attached to the next message — cleared after send.
  final List<({String name, String content})> _attachments = [];

  @override
  void initState() {
    super.initState();
    // Pre-load session if provided
    if (widget.initialSessionId != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        // Set the session ID in the state so subsequent messages use it
        ref.read(chatProvider.notifier).setSessionId(widget.initialSessionId!);
      });
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  /// Combine typed text + file attachments into the final message string.
  String _buildMessage() {
    final text = _controller.text.trim();
    final parts = <String>[];
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
    setState(() => _attachments.clear());
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

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
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
                      ref.refresh(filteredSessionsProvider);
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
                    return ListTile(
                      title: Text(session.name),
                      subtitle: Text(
                        '${session.messageCount} messages',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      selected: isActive,
                      selectedTileColor:
                          Theme.of(context).colorScheme.primaryContainer,
                      onTap: () {
                        // Switch to this session
                        ref.read(chatProvider.notifier).setSessionId(session.sessionId);
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

  Widget _buildScaffold(
      BuildContext context, ChatState chatState, bool isOnline) {
    return SelectionArea(
      child: Scaffold(
        drawer: _buildSessionsDrawer(context, chatState),
        appBar: AppBar(
        title: const Text('Aurelm Agent'),
        actions: [
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
          // New conversation button
          IconButton(
            icon: const Icon(Icons.add_comment_outlined),
            tooltip: 'Nouvelle conversation',
            onPressed: () async {
              await ref.read(chatProvider.notifier).newSession();
              // Refresh the sessions list after creating a new one
              if (mounted) {
                ref.refresh(filteredSessionsProvider);
              }
            },
          ),
        ],
      ),
      body: Column(
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
                        return _MessageBubble(
                            message: chatState.messages[index]);
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

          // Input bar
          _InputBar(
            controller: _controller,
            focusNode: _focusNode,
            enabled: isOnline,
            onSend: _send,
            onPickFile: _pickFile,
            attachments: _attachments,
            onRemoveAttachment: (i) => setState(() => _attachments.removeAt(i)),
          ),
        ],
      ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

class _MessageBubble extends StatelessWidget {
  final ChatMessage message;

  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == ChatRole.user;
    final colorScheme = Theme.of(context).colorScheme;

    final bubble = Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isUser
              ? colorScheme.primary
              : colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
        ),
        child: isUser
            ? Text(
                message.content,
                style: TextStyle(color: colorScheme.onPrimary),
              )
            : MarkdownBody(
                data: message.content,
                styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context))
                    .copyWith(
                  p: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: colorScheme.onSurface,
                      ),
                ),
              ),
      ),
    );

    // For assistant messages, show thinking blocks + tool cards above the bubble
    if (!isUser &&
        (message.toolCalls.isNotEmpty || message.thinkingBlocks.isNotEmpty)) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Thinking blocks (brain icon, collapsible)
            ...message.thinkingBlocks.map(
              (t) => _ThinkingBlock(content: t),
            ),
            // Resolved tool call cards
            ...message.toolCalls.map((tc) => _ToolCallCard(toolCall: tc)),
            // Only show the text bubble if there's actual content
            if (message.content.isNotEmpty) bubble,
          ],
        ),
      );
    }

    return bubble;
  }
}

// ---------------------------------------------------------------------------
// Input bar
// ---------------------------------------------------------------------------

class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final FocusNode focusNode;
  final bool enabled;
  final VoidCallback onSend;
  final VoidCallback onPickFile;
  final List<({String name, String content})> attachments;
  final void Function(int index) onRemoveAttachment;

  const _InputBar({
    required this.controller,
    required this.focusNode,
    required this.enabled,
    required this.onSend,
    required this.onPickFile,
    required this.attachments,
    required this.onRemoveAttachment,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 8, 12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          top: BorderSide(
            color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.2),
          ),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Attachment chips — shown when files are attached
          if (attachments.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Wrap(
                spacing: 6,
                children: [
                  for (int i = 0; i < attachments.length; i++)
                    Chip(
                      label: Text(
                        attachments[i].name,
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                      deleteIcon: const Icon(Icons.close, size: 14),
                      onDeleted: () => onRemoveAttachment(i),
                      visualDensity: VisualDensity.compact,
                    ),
                ],
              ),
            ),
          Row(
            children: [
              // Paperclip button — attach a text file
              IconButton(
                onPressed: enabled ? onPickFile : null,
                icon: const Icon(Icons.attach_file),
                tooltip: 'Joindre un fichier',
                iconSize: 20,
              ),
              Expanded(
                // Intercept Enter (send) vs Shift+Enter (newline) on desktop
                child: Focus(
                  onKeyEvent: (_, event) {
                    if (event is KeyDownEvent &&
                        event.logicalKey == LogicalKeyboardKey.enter &&
                        !HardwareKeyboard.instance.isShiftPressed) {
                      if (enabled) onSend();
                      return KeyEventResult.handled; // swallow Enter
                    }
                    return KeyEventResult.ignored;
                  },
                  child: TextField(
                    controller: controller,
                    focusNode: focusNode,
                    enabled: enabled,
                    maxLines: null,
                    keyboardType: TextInputType.multiline,
                    textInputAction: TextInputAction.newline,
                    decoration: InputDecoration(
                      hintText: enabled
                          ? 'Posez une question... (Shift+Enter pour newline)'
                          : 'Agent hors ligne — démarrez le bot',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide.none,
                      ),
                      filled: true,
                      fillColor: Theme.of(context).colorScheme.surfaceContainerHighest,
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 10),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filled(
                onPressed: enabled ? onSend : null,
                icon: const Icon(Icons.send),
                tooltip: 'Envoyer',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Tool call card — collapsible, shown between bubble and tool result
// ---------------------------------------------------------------------------

class _ToolCallCard extends StatefulWidget {
  final ToolCallInfo toolCall;
  const _ToolCallCard({required this.toolCall});

  @override
  State<_ToolCallCard> createState() => _ToolCallCardState();
}

class _ToolCallCardState extends State<_ToolCallCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final tc = widget.toolCall;
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    final label = tc.inputSummary.isNotEmpty
        ? '${tc.name} — ${tc.inputSummary}'
        : tc.name;

    return Container(
      margin: const EdgeInsets.only(bottom: 3),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: colorScheme.outline.withValues(alpha: 0.2),
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: () => setState(() => _expanded = !_expanded),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.manage_search,
                      size: 14, color: colorScheme.onSurfaceVariant),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      label,
                      style: textTheme.labelSmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Icon(
                    _expanded ? Icons.expand_less : Icons.expand_more,
                    size: 14,
                    color: colorScheme.onSurfaceVariant,
                  ),
                ],
              ),
              if (_expanded) ...[
                const Divider(height: 10, thickness: 0.5),
                // Show full result if available, otherwise summary
                ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 300),
                  child: SingleChildScrollView(
                    child: SelectableText(
                      tc.fullResult.isNotEmpty
                          ? tc.fullResult
                          : tc.resultSummary,
                      style: textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                        fontFamily: 'monospace',
                        fontSize: 11,
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Queued message bubble — faded, shown while LLM is processing
// ---------------------------------------------------------------------------

class _QueuedMessageBubble extends StatelessWidget {
  final String text; // all queued messages pre-joined with \n
  final VoidCallback onCancel;

  const _QueuedMessageBubble({
    required this.text,
    required this.onCancel,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Align(
      alignment: Alignment.centerRight,
      child: Opacity(
        opacity: 0.45,
        child: Container(
          constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.75,
          ),
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: colorScheme.primary,
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(16),
              topRight: Radius.circular(16),
              bottomLeft: Radius.circular(16),
              bottomRight: Radius.circular(4),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Flexible(
                child: Text(
                  text,
                  style: TextStyle(color: colorScheme.onPrimary),
                ),
              ),
              // ✕ removes the last line from the queue (Escape equivalent)
              const SizedBox(width: 8),
              GestureDetector(
                onTap: onCancel,
                child: Icon(Icons.close, size: 14, color: colorScheme.onPrimary),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Thinking block — collapsible, brain icon
// ---------------------------------------------------------------------------

class _ThinkingBlock extends StatefulWidget {
  final String content;
  const _ThinkingBlock({required this.content});

  @override
  State<_ThinkingBlock> createState() => _ThinkingBlockState();
}

class _ThinkingBlockState extends State<_ThinkingBlock> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return Container(
      margin: const EdgeInsets.only(bottom: 3),
      decoration: BoxDecoration(
        color: colorScheme.tertiaryContainer.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: colorScheme.tertiary.withValues(alpha: 0.3),
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: () => setState(() => _expanded = !_expanded),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.psychology,
                      size: 14, color: colorScheme.tertiary),
                  const SizedBox(width: 6),
                  Text(
                    'Thinking...',
                    style: textTheme.labelSmall?.copyWith(
                      color: colorScheme.tertiary,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                  const Spacer(),
                  Icon(
                    _expanded ? Icons.expand_less : Icons.expand_more,
                    size: 14,
                    color: colorScheme.tertiary,
                  ),
                ],
              ),
              if (_expanded) ...[
                const Divider(height: 10, thickness: 0.5),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 200),
                  child: SingleChildScrollView(
                    child: SelectableText(
                      widget.content,
                      style: textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurface.withValues(alpha: 0.7),
                        fontStyle: FontStyle.italic,
                        fontSize: 11,
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Pending tool chip — spinner while tool is executing
// ---------------------------------------------------------------------------

class _PendingToolChip extends StatelessWidget {
  final PendingToolCall pending;
  const _PendingToolChip({required this.pending});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final label = pending.inputSummary.isNotEmpty
        ? '${pending.name} — ${pending.inputSummary}'
        : pending.name;

    return Container(
      margin: const EdgeInsets.only(bottom: 3),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: colorScheme.outline.withValues(alpha: 0.2),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 12,
            height: 12,
            child: CircularProgressIndicator(
              strokeWidth: 1.5,
              color: colorScheme.primary,
            ),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

class _EmptyState extends ConsumerStatefulWidget {
  final bool isOnline;

  const _EmptyState({required this.isOnline});

  @override
  ConsumerState<_EmptyState> createState() => _EmptyStateState();
}

class _EmptyStateState extends ConsumerState<_EmptyState> {
  bool _starting = false;
  String? _startError;

  Future<void> _startBot() async {
    final dbPath = ref.read(dbPathProvider);
    if (dbPath == null) {
      setState(() => _startError = 'Aucune base de données configurée.');
      return;
    }
    setState(() {
      _starting = true;
      _startError = null;
    });
    // Use 'py' launcher (Windows) — BotService handles the working directory
    final ok = await ref.read(botServiceProvider).start(
          dbPath: dbPath,
          pythonPath: 'py',
          pythonArgs: ['-3.12'], // Windows py launcher: select Python 3.12
        );
    if (mounted) {
      setState(() {
        _starting = false;
        if (!ok) _startError = 'Échec du démarrage — vérifiez la console.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.auto_awesome,
            size: 64,
            color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.4),
          ),
          const SizedBox(height: 16),
          Text(
            'Aurelm Agent',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            widget.isOnline
                ? 'Posez une question sur le lore, les civilisations ou les entités.'
                : 'Le bot Python n\'est pas démarré.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
            textAlign: TextAlign.center,
          ),
          // Start button — shown when offline
          if (!widget.isOnline) ...[
            const SizedBox(height: 20),
            if (_starting)
              const CircularProgressIndicator()
            else
              FilledButton.icon(
                onPressed: _startBot,
                icon: const Icon(Icons.play_arrow),
                label: const Text('Démarrer l\'agent'),
              ),
            if (_startError != null) ...[
              const SizedBox(height: 8),
              Text(
                _startError!,
                style: TextStyle(
                    color: Theme.of(context).colorScheme.error, fontSize: 12),
              ),
            ],
          ],
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Error banner
// ---------------------------------------------------------------------------

class _ErrorBanner extends StatelessWidget {
  final String error;
  final VoidCallback onDismiss;

  const _ErrorBanner({required this.error, required this.onDismiss});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Theme.of(context).colorScheme.errorContainer,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          Icon(Icons.error_outline,
              color: Theme.of(context).colorScheme.onErrorContainer, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              error,
              style: TextStyle(
                  color: Theme.of(context).colorScheme.onErrorContainer,
                  fontSize: 12),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close, size: 16),
            color: Theme.of(context).colorScheme.onErrorContainer,
            onPressed: onDismiss,
          ),
        ],
      ),
    );
  }
}
