part of '../chat_screen.dart';

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

/// Shown when visible reasoning was requested but the (adaptive) model answered
/// directly — so an empty reasoning panel reads as intentional, not broken.
class _DirectAnswerNote extends StatelessWidget {
  const _DirectAnswerNote();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 6, left: 4),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.bolt, size: 13, color: scheme.outline),
          const SizedBox(width: 4),
          Text(
            'Réponse directe — le raisonnement n\'apparaît que sur les questions complexes.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: scheme.outline,
                  fontStyle: FontStyle.italic,
                ),
          ),
        ],
      ),
    );
  }
}

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
