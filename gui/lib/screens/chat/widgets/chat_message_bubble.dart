part of '../chat_screen.dart';

// ---------------------------------------------------------------------------
// Message bubble
// ---------------------------------------------------------------------------

class _MessageBubble extends ConsumerStatefulWidget {
  final ChatMessage message;
  final int index;
  /// Called when the user clicks "Citer" on this bubble.
  final void Function(ChatMessage) onQuote;

  const _MessageBubble({
    required this.message,
    required this.index,
    required this.onQuote,
  });

  @override
  ConsumerState<_MessageBubble> createState() => _MessageBubbleState();
}

class _MessageBubbleState extends ConsumerState<_MessageBubble> {
  bool _hovered = false;

  ChatMessage get message => widget.message;
  int get index => widget.index;

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
  Widget build(BuildContext context) {
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

    // Reasoning was asked for this turn but the model answered without surfacing
    // any — correct adaptive behaviour on a simple question, not a broken toggle.
    // Gated on content being present: thinking streams before the answer, so once
    // content arrives with no thinking, none is coming.
    final answeredDirectly = !isUser &&
        message.thinkingRequested &&
        message.thinkingBlocks.isEmpty &&
        message.content.isNotEmpty;

    // For assistant messages, show thinking blocks + tool cards above the bubble
    Widget content = bubble;
    if (!isUser &&
        (message.toolCalls.isNotEmpty ||
            message.thinkingBlocks.isNotEmpty ||
            answeredDirectly)) {
      content = Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ...message.thinkingBlocks.map((t) => _ThinkingBlock(content: t)),
            if (answeredDirectly) const _DirectAnswerNote(),
            ...message.toolCalls.map((tc) => _ToolCallCard(toolCall: tc)),
            if (message.content.isNotEmpty) bubble,
          ],
        ),
      );
    }

    return _withHoverActions(context, content);
  }

  /// Barre d'icônes hover + clic droit pour "Copier depuis ici".
  Widget _withHoverActions(BuildContext context, Widget content) {
    final isUser = message.role == ChatRole.user;
    final notifier = ref.read(chatProvider.notifier);

    return GestureDetector(
      // Clic droit : menu contextuel léger (copier depuis ici uniquement)
      onSecondaryTapDown: (details) async {
        final overlay =
            Overlay.of(context).context.findRenderObject() as RenderBox;
        final result = await showMenu<String>(
          context: context,
          position: RelativeRect.fromRect(
            details.globalPosition & const Size(1, 1),
            Offset.zero & overlay.size,
          ),
          items: [
            const PopupMenuItem(
              value: 'copy_from',
              child: ListTile(
                leading: Icon(Icons.content_copy, size: 18),
                title: Text('Copier depuis ici'),
                dense: true,
              ),
            ),
          ],
        );
        if (result == 'copy_from') notifier.copyConversationFrom(index);
      },
      child: MouseRegion(
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: Column(
          crossAxisAlignment:
              isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            content,
            AnimatedOpacity(
              opacity: _hovered ? 1.0 : 0.0,
              duration: const Duration(milliseconds: 120),
              child: Padding(
                padding: const EdgeInsets.only(top: 2, bottom: 2),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: _buildActionIcons(context, isUser, notifier),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Construit la liste des icônes d'action selon le rôle du message.
  List<Widget> _buildActionIcons(
    BuildContext context,
    bool isUser,
    ChatNotifier notifier,
  ) {
    Widget btn(IconData icon, String tooltip, VoidCallback onTap,
        {Color? color}) {
      return Tooltip(
        message: tooltip,
        waitDuration: const Duration(milliseconds: 500),
        child: InkWell(
          borderRadius: BorderRadius.circular(6),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(4),
            child: Icon(icon, size: 15,
                color: color ?? Theme.of(context).colorScheme.onSurfaceVariant),
          ),
        ),
      );
    }

    if (isUser) {
      return [
        btn(Icons.copy_outlined, 'Copier', () => notifier.copyMessage(index)),
        btn(Icons.format_quote, 'Citer', () => widget.onQuote(message)),
        btn(Icons.edit_outlined, 'Modifier',
            () => _showEditConfirm(context, notifier)),
        btn(Icons.delete_outline, 'Supprimer',
            () => _showDeleteConfirm(context, notifier),
            color: Theme.of(context).colorScheme.error),
      ];
    } else {
      return [
        btn(Icons.copy_outlined, 'Copier', () => notifier.copyMessage(index)),
        btn(Icons.format_quote, 'Citer', () => widget.onQuote(message)),
        btn(Icons.fork_right, 'Dupliquer depuis ici', () async {
          await notifier.duplicateCurrentSessionFrom(index);
          if (context.mounted) ref.invalidate(filteredSessionsProvider);
        }),
        btn(Icons.refresh, 'Réessayer', () => notifier.retryMessage(index)),
      ];
    }
  }

  /// Confirmation avant suppression — avertit que les messages suivants disparaissent.
  Future<void> _showDeleteConfirm(
      BuildContext context, ChatNotifier notifier) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Supprimer ce message ?'),
        content: const Text(
            'Ce message et tous ceux qui suivent seront supprimés définitivement.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
                backgroundColor: Theme.of(ctx).colorScheme.error),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );
    if (ok == true) await notifier.deleteMessageFrom(index);
  }

  /// Confirmation + saisie du nouveau texte pour éditer un message user.
  ///
  /// L'édition supprime ce message et tout ce qui suit — on avertit avant.
  Future<void> _showEditConfirm(
      BuildContext context, ChatNotifier notifier) async {
    // Étape 1 : avertissement
    final proceed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Modifier ce message ?'),
        content: const Text(
            'Les messages suivants seront supprimés et l\'agent sera relancé avec le nouveau texte.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Continuer'),
          ),
        ],
      ),
    );
    if (proceed != true || !context.mounted) return;

    // Étape 2 : saisie du nouveau texte
    final controller = TextEditingController(text: message.content);
    final newText = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Nouveau message'),
        content: TextField(
          controller: controller,
          maxLines: null,
          autofocus: true,
          decoration: const InputDecoration(border: OutlineInputBorder()),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Annuler'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Envoyer'),
          ),
        ],
      ),
    );
    if (newText != null && newText.isNotEmpty) {
      await notifier.editMessage(index, newText);
    }
  }

}
