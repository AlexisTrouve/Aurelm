import 'dart:io';

import 'package:drift/drift.dart' show Variable;
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../../providers/chat_provider.dart';
import '../../providers/bot_provider.dart';
import '../../providers/database_provider.dart';
import '../../providers/chat_sessions_provider.dart';
import '../../providers/lore_links_provider.dart';
import '../../providers/side_panel_provider.dart';
import '../../services/chat_sessions_service.dart';
import '../../utils/lore_linker.dart';
import '../../widgets/common/side_panel.dart';

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
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Refresh sessions list when a chat turn completes (loading: true→false),
    // so auto-tags applied by the bot are visible immediately in the drawer.
    ref.listenManual(chatProvider, (prev, next) {
      if (prev?.loading == true && next.loading == false) {
        ref.invalidate(filteredSessionsProvider);
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
    if (!_scrollController.hasClients) return;
    // Wait for layout to settle before scrolling — avoids overshooting
    // when messages are still being laid out (e.g. session load).
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
              ref.refresh(filteredSessionsProvider);
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
                ref.refresh(filteredSessionsProvider);
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
        drawer: _buildSessionsDrawer(context, chatState),
        appBar: AppBar(
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
              if (mounted) ref.refresh(filteredSessionsProvider);
            },
          ),
          // Session actions menu (duplicate, copy conversation)
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert),
            tooltip: 'Actions session',
            onSelected: (value) async {
              final sessionId = chatState.sessionId;
              switch (value) {
                case 'duplicate':
                  if (sessionId == null) break;
                  await ref.read(sessionsProvider).duplicateSession(sessionId);
                  if (mounted) ref.refresh(filteredSessionsProvider);
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
                              return _MessageBubble(message: msg, index: index);
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
          // Side panel — lore detail views (max 40% width, 3 slots) on RIGHT
          const SidePanel(),
        ],
      ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Message segment parser — splits user messages into text and file parts
// ---------------------------------------------------------------------------

/// Represents a segment of a user message: either plain text or an attached file.
sealed class _MessageSegment {}

class _TextSegment extends _MessageSegment {
  final String text;
  _TextSegment(this.text);
}

class _FileSegment extends _MessageSegment {
  final String filename;
  final String content;
  _FileSegment(this.filename, this.content);
}

/// Parse a message string into alternating text/file segments.
/// Files are delimited by `[Fichier: name]\ncontent` blocks.
List<_MessageSegment> _parseMessageSegments(String message) {
  final segments = <_MessageSegment>[];
  final pattern = RegExp(r'\[Fichier: ([^\]]+)\]\n');
  int cursor = 0;

  for (final match in pattern.allMatches(message)) {
    // Text before this file marker
    if (match.start > cursor) {
      final text = message.substring(cursor, match.start).trim();
      if (text.isNotEmpty) segments.add(_TextSegment(text));
    }

    final filename = match.group(1)!;
    // File content runs from end of marker to next marker or end of string
    final contentStart = match.end;
    // Look for next file marker to delimit content
    final nextMatch = pattern.firstMatch(message.substring(contentStart));
    final contentEnd = nextMatch != null
        ? contentStart + nextMatch.start
        : message.length;
    // Trim trailing whitespace between file blocks
    final content = message.substring(contentStart, contentEnd).trimRight();
    segments.add(_FileSegment(filename, content));
    cursor = contentEnd;
  }

  // Trailing text after last file
  if (cursor < message.length) {
    final text = message.substring(cursor).trim();
    if (text.isNotEmpty) segments.add(_TextSegment(text));
  }

  return segments;
}

/// Pick an icon based on file extension.
IconData _fileIcon(String filename) {
  final ext = filename.contains('.') ? filename.split('.').last.toLowerCase() : '';
  return switch (ext) {
    'py' || 'dart' => Icons.code,
    'ts' || 'js' => Icons.javascript,
    'json' => Icons.data_object,
    'sql' => Icons.storage,
    'md' => Icons.description,
    'csv' => Icons.table_chart,
    'txt' => Icons.text_snippet,
    _ => Icons.insert_drive_file,
  };
}

/// Build user message content with file cards when attachments are present.
Widget _buildUserContent(String content, ColorScheme colorScheme) {
  final segments = _parseMessageSegments(content);

  // Fast path: single text segment = plain message, no overhead
  if (segments.length == 1 && segments.first is _TextSegment) {
    return Text(
      (segments.first as _TextSegment).text,
      style: TextStyle(color: colorScheme.onPrimary),
    );
  }

  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: segments.map((seg) {
      if (seg is _TextSegment) {
        return Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Text(
            seg.text,
            style: TextStyle(color: colorScheme.onPrimary),
          ),
        );
      }
      final file = seg as _FileSegment;
      return Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: _FileCard(filename: file.filename, content: file.content),
      );
    }).toList(),
  );
}

// ---------------------------------------------------------------------------
// File card — collapsible, shown inside user bubbles for attached files
// ---------------------------------------------------------------------------

class _FileCard extends StatefulWidget {
  final String filename;
  final String content;

  const _FileCard({required this.filename, required this.content});

  @override
  State<_FileCard> createState() => _FileCardState();
}

class _FileCardState extends State<_FileCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    // Human-readable size label
    final chars = widget.content.length;
    final sizeLabel = chars >= 1024
        ? '${(chars / 1024).toStringAsFixed(1)} KB'
        : '$chars chars';

    return Container(
      decoration: BoxDecoration(
        color: colorScheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: colorScheme.secondary.withValues(alpha: 0.5),
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
                  Icon(_fileIcon(widget.filename),
                      size: 14, color: colorScheme.secondary),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      widget.filename,
                      style: textTheme.labelSmall?.copyWith(
                        color: colorScheme.onSurface,
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    sizeLabel,
                    style: textTheme.labelSmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                      fontSize: 10,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    _expanded ? Icons.expand_less : Icons.expand_more,
                    size: 14,
                    color: colorScheme.onSurfaceVariant,
                  ),
                ],
              ),
              if (_expanded) ...[
                const Divider(height: 10, thickness: 0.5),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 300),
                  child: SingleChildScrollView(
                    child: SelectableText(
                      widget.content,
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
// Message bubble
// ---------------------------------------------------------------------------

class _MessageBubble extends ConsumerWidget {
  final ChatMessage message;
  final int index;

  const _MessageBubble({required this.message, required this.index});

  /// Handle taps on lore:// links — open in the side panel.
  /// For turns with multiple civs (lore://turn/-turnNumber), show a civ picker.
  void _onTapLoreLink(BuildContext context, WidgetRef ref, String href) {
    final uri = Uri.tryParse(href);
    if (uri == null || uri.scheme != 'lore') return;

    final rawId = int.tryParse(uri.pathSegments.lastOrNull ?? '');
    if (rawId == null) return;

    final type = switch (uri.host) {
      'entity' => LoreLinkType.entity,
      'civ' => LoreLinkType.civ,
      'subject' => LoreLinkType.subject,
      'turn' => LoreLinkType.turn,
      _ => null,
    };
    if (type == null) return;

    // Turn with negative ID = ambiguous turn number, needs civ picker
    if (type == LoreLinkType.turn && rawId < 0) {
      _showTurnCivPicker(context, ref, -rawId);
      return;
    }

    ref.read(sidePanelProvider.notifier).open(
          SidePanelItem(type: type, id: rawId),
        );
  }

  /// Show a dialog to pick which civ's turn to open when multiple civs have
  /// the same turn number.
  void _showTurnCivPicker(
      BuildContext context, WidgetRef ref, int turnNumber) async {
    final db = ref.read(databaseProvider);
    if (db == null) return;

    // Find all turns with this turn_number across civs
    final rows = await db.customSelect(
      '''
      SELECT t.id, t.turn_number, c.id AS civ_id, c.name AS civ_name
      FROM turn_turns t
      JOIN civ_civilizations c ON c.id = t.civ_id
      WHERE t.turn_number = ?
      ORDER BY c.name
      ''',
      variables: [Variable<int>(turnNumber)],
      readsFrom: {db.turnTurns, db.civCivilizations},
    ).get();

    if (rows.isEmpty) return;

    // Only one civ — open directly
    if (rows.length == 1) {
      ref.read(sidePanelProvider.notifier).open(
            SidePanelItem(
              type: LoreLinkType.turn,
              id: rows.first.read<int>('id'),
            ),
          );
      return;
    }

    // Multiple civs — show picker dialog
    if (!context.mounted) return;
    final chosen = await showDialog<int>(
      context: context,
      builder: (dCtx) => SimpleDialog(
        title: Text('Tour $turnNumber - quelle civilisation ?'),
        children: rows.map((r) {
          final turnId = r.read<int>('id');
          final civName = r.read<String>('civ_name');
          return SimpleDialogOption(
            onPressed: () => Navigator.of(dCtx).pop(turnId),
            child: Text(civName),
          );
        }).toList(),
      ),
    );

    if (chosen != null) {
      ref.read(sidePanelProvider.notifier).open(
            SidePanelItem(type: LoreLinkType.turn, id: chosen),
          );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isUser = message.role == ChatRole.user;
    final colorScheme = Theme.of(context).colorScheme;

    // For assistant messages, inject lore hyperlinks in background isolate.
    // Shows raw text immediately, swaps in linked text when ready (non-blocking).
    String displayContent = message.content;
    if (!isUser && displayContent.isNotEmpty) {
      final linkedAsync = ref.watch(loreLinkTextProvider(displayContent));
      displayContent = linkedAsync.valueOrNull ?? displayContent;
    }

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
            ? _buildUserContent(message.content, colorScheme)
            : MarkdownBody(
                data: displayContent,
                styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context))
                    .copyWith(
                  p: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: colorScheme.onSurface,
                      ),
                ),
                onTapLink: (_, href, __) {
                  if (href != null && href.startsWith('lore://')) {
                    _onTapLoreLink(context, ref, href);
                  }
                },
              ),
      ),
    );

    // For assistant messages, show thinking blocks + tool cards above the bubble
    if (!isUser &&
        (message.toolCalls.isNotEmpty || message.thinkingBlocks.isNotEmpty)) {
      return _withContextMenu(
        context,
        ref,
        Padding(
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
        ),
      );
    }

    return _withContextMenu(context, ref, bubble);
  }

  /// Enveloppe [child] dans un GestureDetector qui affiche un menu contextuel
  /// au clic droit (secondary tap). Les options varient selon le rôle du message :
  /// - user : Copier, Modifier, Supprimer
  /// - assistant : Copier, Réessayer
  Widget _withContextMenu(BuildContext context, WidgetRef ref, Widget child) {
    final isUser = message.role == ChatRole.user;
    final notifier = ref.read(chatProvider.notifier);

    return GestureDetector(
      onSecondaryTapDown: (details) async {
        // RenderBox de l'overlay pour calculer la position du menu
        final overlay =
            Overlay.of(context).context.findRenderObject() as RenderBox;
        final menuItems = <PopupMenuEntry<String>>[
          const PopupMenuItem(
            value: 'copy',
            child: ListTile(
              leading: Icon(Icons.copy, size: 18),
              title: Text('Copier'),
              dense: true,
            ),
          ),
          const PopupMenuItem(
            value: 'copy_from',
            child: ListTile(
              leading: Icon(Icons.content_copy, size: 18),
              title: Text('Copier depuis ici'),
              dense: true,
            ),
          ),
          if (isUser) ...[
            const PopupMenuItem(
              value: 'edit',
              child: ListTile(
                leading: Icon(Icons.edit, size: 18),
                title: Text('Modifier'),
                dense: true,
              ),
            ),
            const PopupMenuDivider(),
            const PopupMenuItem(
              value: 'delete',
              child: ListTile(
                leading: Icon(Icons.delete, size: 18, color: Colors.red),
                title: Text('Supprimer',
                    style: TextStyle(color: Colors.red)),
                dense: true,
              ),
            ),
          ] else ...[
            const PopupMenuItem(
              value: 'retry',
              child: ListTile(
                leading: Icon(Icons.refresh, size: 18),
                title: Text('Réessayer'),
                dense: true,
              ),
            ),
          ],
        ];

        final result = await showMenu<String>(
          context: context,
          position: RelativeRect.fromRect(
            details.globalPosition & const Size(1, 1),
            Offset.zero & overlay.size,
          ),
          items: menuItems,
        );

        if (result == null) return;

        switch (result) {
          case 'copy':
            notifier.copyMessage(index);
          case 'copy_from':
            notifier.copyConversationFrom(index);
          case 'edit':
            if (!context.mounted) return;
            final controller =
                TextEditingController(text: message.content);
            final newText = await showDialog<String>(
              context: context,
              builder: (ctx) => AlertDialog(
                title: const Text('Modifier le message'),
                content: TextField(
                  controller: controller,
                  maxLines: null,
                  autofocus: true,
                  decoration: const InputDecoration(
                      border: OutlineInputBorder()),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('Annuler'),
                  ),
                  ElevatedButton(
                    onPressed: () =>
                        Navigator.pop(ctx, controller.text.trim()),
                    child: const Text('Envoyer'),
                  ),
                ],
              ),
            );
            if (newText != null && newText.isNotEmpty) {
              await notifier.editMessage(index, newText);
            }
          case 'delete':
            await notifier.deleteMessageFrom(index);
          case 'retry':
            await notifier.retryMessage(index);
        }
      },
      child: child,
    );
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
                child: _buildUserContent(text, colorScheme),
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
// Summary bubble — compress/resume blocks, centered, collapsible
// ---------------------------------------------------------------------------

class _SummaryBubble extends StatefulWidget {
  final ChatMessage message;
  const _SummaryBubble({required this.message});

  @override
  State<_SummaryBubble> createState() => _SummaryBubbleState();
}

class _SummaryBubbleState extends State<_SummaryBubble> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final isResume = widget.message.messageType == MessageType.resume;
    final icon = isResume ? Icons.auto_stories : Icons.compress;
    final label = isResume ? 'Resume de session' : 'Historique compresse';
    final accentColor = isResume
        ? colorScheme.tertiary
        : colorScheme.secondary;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.7,
          ),
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () => setState(() => _expanded = !_expanded),
              borderRadius: BorderRadius.circular(12),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: accentColor.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: accentColor.withValues(alpha: 0.3),
                    style: BorderStyle.solid,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header row: icon + label + expand arrow
                    Row(
                      children: [
                        Icon(icon, size: 16, color: accentColor),
                        const SizedBox(width: 8),
                        Text(
                          label,
                          style: Theme.of(context).textTheme.labelMedium?.copyWith(
                            color: accentColor,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const Spacer(),
                        Icon(
                          _expanded ? Icons.expand_less : Icons.expand_more,
                          size: 18,
                          color: accentColor,
                        ),
                      ],
                    ),
                    // Collapsible content
                    if (_expanded) ...[
                      const SizedBox(height: 8),
                      Divider(height: 1, color: accentColor.withValues(alpha: 0.2)),
                      const SizedBox(height: 8),
                      SelectableText(
                        widget.message.content,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurface.withValues(alpha: 0.8),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
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

// ---------------------------------------------------------------------------
// Token usage badge — context tokens / max budget, shown in AppBar
// ---------------------------------------------------------------------------

class _TokenUsageBadge extends StatelessWidget {
  final int contextTokens;
  final int maxTokens;

  const _TokenUsageBadge({
    required this.contextTokens,
    required this.maxTokens,
  });

  /// Format token count: 1234 -> "1.2k", 56789 -> "56.8k"
  static String _fmt(int tokens) {
    if (tokens < 1000) return '$tokens';
    return '${(tokens / 1000).toStringAsFixed(1)}k';
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final ratio = contextTokens / maxTokens;

    // Color shifts as context fills up: green -> amber -> red
    final Color barColor;
    if (ratio < 0.5) {
      barColor = Colors.green;
    } else if (ratio < 0.8) {
      barColor = Colors.amber;
    } else {
      barColor = colorScheme.error;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Tooltip(
        message: 'Contexte: $contextTokens / $maxTokens tokens',
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.token, size: 14, color: barColor),
            const SizedBox(width: 4),
            Text(
              '${_fmt(contextTokens)} / ${_fmt(maxTokens)}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: barColor,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
