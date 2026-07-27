part of '../chat_screen.dart';

// ---------------------------------------------------------------------------
// Quote preview — strip shown above input when a message is being quoted
// ---------------------------------------------------------------------------

class _QuotePreview extends StatelessWidget {
  final ChatMessage message;
  final VoidCallback onClear;

  const _QuotePreview({required this.message, required this.onClear});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final isUser = message.role == ChatRole.user;
    final role = isUser ? 'Vous' : 'Aurelm';
    final preview = message.content.replaceAll('\n', ' ');

    return Container(
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
        border: Border(
          // Left accent bar — matches bubble color
          left: BorderSide(
            color: isUser ? colorScheme.primary : colorScheme.secondary,
            width: 3,
          ),
        ),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  role,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: isUser ? colorScheme.primary : colorScheme.secondary,
                        fontWeight: FontWeight.w600,
                      ),
                ),
                const SizedBox(height: 2),
                Text(
                  preview,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                ),
              ],
            ),
          ),
          // Clear quote button
          InkWell(
            onTap: onClear,
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(4),
              child: Icon(Icons.close, size: 16, color: colorScheme.onSurfaceVariant),
            ),
          ),
        ],
      ),
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
  /// Message currently quoted — shown as a preview strip above the input.
  final ChatMessage? quotedMessage;
  final VoidCallback onClearQuote;

  const _InputBar({
    required this.controller,
    required this.focusNode,
    required this.enabled,
    required this.onSend,
    required this.onPickFile,
    required this.attachments,
    required this.onRemoveAttachment,
    this.quotedMessage,
    required this.onClearQuote,
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
          // Quote preview — shown when a message is being quoted
          if (quotedMessage != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: _QuotePreview(
                message: quotedMessage!,
                onClear: onClearQuote,
              ),
            ),

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
