import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/database.dart';
import '../../../providers/notes_provider.dart';

/// Which object a note is attached to.
enum NoteAttachment { entity, subject, turn }

// Rail dimensions
const _kRailWidth = 96.0;
const _kTagHeight = 28.0;
const _kTagGap = 5.0;
const _kTopPad = 8.0;

// ---------------------------------------------------------------------------
// NotesSideRail — vertical rail on left side of body, tags expand on hover
// ---------------------------------------------------------------------------

/// Wraps [child] with a thin vertical rail on the left showing note tags.
/// Each tag displays 6-char uppercase; hover expands to show the full title.
/// Click opens a floating draggable note window.
class NotesSideRail extends ConsumerStatefulWidget {
  final NoteAttachment attachment;
  final int attachmentId;
  final Widget child;

  const NotesSideRail({
    super.key,
    required this.attachment,
    required this.attachmentId,
    required this.child,
  });

  @override
  ConsumerState<NotesSideRail> createState() => _NotesSideRailState();
}

class _NotesSideRailState extends ConsumerState<NotesSideRail> {
  bool _collapsed = false;

  // Collapsed rail: just a thin strip with a toggle arrow
  static const _kCollapsedWidth = 20.0;

  @override
  Widget build(BuildContext context) {
    final notesAsync = switch (widget.attachment) {
      NoteAttachment.entity  => ref.watch(entityNotesProvider(widget.attachmentId)),
      NoteAttachment.subject => ref.watch(subjectNotesProvider(widget.attachmentId)),
      NoteAttachment.turn    => ref.watch(turnNotesProvider(widget.attachmentId)),
    };
    final notes = notesAsync.valueOrNull ?? [];
    final cs = Theme.of(context).colorScheme;
    final railW = _collapsed ? _kCollapsedWidth : _kRailWidth;

    return Stack(
      clipBehavior: Clip.none,
      children: [
        // Main content — pushed right by current rail width
        AnimatedPadding(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
          padding: EdgeInsets.only(left: railW),
          child: widget.child,
        ),

        // Rail background strip
        AnimatedPositioned(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
          left: 0,
          top: 0,
          bottom: 0,
          width: railW,
          child: Container(
            decoration: BoxDecoration(
              color: cs.surfaceContainerLow,
              border: Border(
                right: BorderSide(color: cs.outlineVariant, width: 0.5),
              ),
            ),
            // Toggle button at the top of the rail
            alignment: Alignment.topCenter,
            child: Padding(
              padding: const EdgeInsets.only(top: 2),
              child: SizedBox(
                width: _collapsed ? 18 : 24,
                height: 18,
                child: IconButton(
                  padding: EdgeInsets.zero,
                  iconSize: 14,
                  icon: Icon(
                    _collapsed ? Icons.chevron_right : Icons.chevron_left,
                    color: cs.onSurfaceVariant,
                  ),
                  tooltip: _collapsed ? 'Ouvrir les notes' : 'Réduire',
                  onPressed: () => setState(() => _collapsed = !_collapsed),
                ),
              ),
            ),
          ),
        ),

        // Note tags — only when expanded
        if (!_collapsed) ...[
          for (var i = 0; i < notes.length; i++)
            Positioned(
              left: 4,
              top: _kTopPad + 20 + i * (_kTagHeight + _kTagGap),
              child: _NoteRailTag(
                note: notes[i],
                collapsedWidth: _kRailWidth - 8,
                onTap: () => showNoteViewWindow(context, notes[i]),
              ),
            ),

          // "+" add button at the bottom of tags
          Positioned(
            left: 4,
            top: _kTopPad + 20 + notes.length * (_kTagHeight + _kTagGap),
            child: _AddRailButton(
              width: _kRailWidth - 8,
              onTap: () => showNoteAddWindow(
                  context, widget.attachment, widget.attachmentId),
            ),
          ),
        ],
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Individual rail tag — collapsed 6-char, hover expands right
// ---------------------------------------------------------------------------

class _NoteRailTag extends StatefulWidget {
  final NoteRow note;
  final double collapsedWidth;
  final VoidCallback onTap;

  const _NoteRailTag({
    required this.note,
    required this.collapsedWidth,
    required this.onTap,
  });

  @override
  State<_NoteRailTag> createState() => _NoteRailTagState();
}

class _NoteRailTagState extends State<_NoteRailTag> {
  bool _hovered = false;

  String get _fullLabel {
    final src = widget.note.title.isNotEmpty
        ? widget.note.title
        : widget.note.content;
    return src.isNotEmpty ? src : '?';
  }

  String get _shortLabel {
    final f = _fullLabel;
    final cropped = f.length > 6 ? f.substring(0, 6) : f;
    return cropped.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedSize(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
          alignment: Alignment.centerLeft,
          child: Container(
            height: _kTagHeight,
            constraints: BoxConstraints(
              minWidth: widget.collapsedWidth,
              maxWidth: _hovered ? 260 : widget.collapsedWidth,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: _hovered
                  ? cs.primaryContainer
                  : cs.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(4),
              border: Border.all(
                color: _hovered ? cs.primary : cs.outlineVariant,
                width: 0.5,
              ),
              boxShadow: _hovered
                  ? [BoxShadow(
                      color: Colors.black.withValues(alpha: 0.15),
                      blurRadius: 6,
                      offset: const Offset(2, 1),
                    )]
                  : null,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.sticky_note_2,
                  size: 14,
                  color: _hovered ? cs.primary : cs.onSurfaceVariant,
                ),
                const SizedBox(width: 6),
                Flexible(
                  child: Text(
                    _hovered ? _fullLabel : _shortLabel,
                    style: TextStyle(
                      fontSize: _hovered ? 13 : 12,
                      fontWeight: FontWeight.w600,
                      color: _hovered ? cs.onPrimaryContainer : cs.onSurface,
                      letterSpacing: _hovered ? 0 : 0.3,
                    ),
                    overflow: TextOverflow.ellipsis,
                    maxLines: 1,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// "+" button in the rail
// ---------------------------------------------------------------------------

class _AddRailButton extends StatefulWidget {
  final double width;
  final VoidCallback onTap;

  const _AddRailButton({required this.width, required this.onTap});

  @override
  State<_AddRailButton> createState() => _AddRailButtonState();
}

class _AddRailButtonState extends State<_AddRailButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedSize(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
          alignment: Alignment.centerLeft,
          child: Container(
            height: _kTagHeight,
            constraints: BoxConstraints(
              minWidth: widget.width,
              maxWidth: _hovered ? 200 : widget.width,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: _hovered
                  ? cs.primaryContainer.withValues(alpha: 0.5)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(4),
              border: Border.all(
                color: _hovered ? cs.primary : cs.outlineVariant,
                width: 0.5,
                strokeAlign: BorderSide.strokeAlignInside,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.add, size: 16,
                    color: _hovered ? cs.primary : cs.onSurfaceVariant),
                if (_hovered) ...[
                  const SizedBox(width: 6),
                  Text(
                    'Nouvelle note',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: cs.primary,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Draggable floating window infrastructure
// ---------------------------------------------------------------------------

typedef _WindowBody = Widget Function(VoidCallback close);

OverlayEntry _insertWindow(
  BuildContext context,
  String title,
  IconData icon,
  _WindowBody body, {
  Offset initialOffset = const Offset(200, 140),
}) {
  late OverlayEntry entry;
  entry = OverlayEntry(
    builder: (ctx) => _FloatingWindowFrame(
      title: title,
      icon: icon,
      initialOffset: initialOffset,
      onClose: () => entry.remove(),
      body: body(() => entry.remove()),
    ),
  );
  Overlay.of(context).insert(entry);
  return entry;
}

class _FloatingWindowFrame extends StatefulWidget {
  final String title;
  final IconData icon;
  final Offset initialOffset;
  final VoidCallback onClose;
  final Widget body;

  const _FloatingWindowFrame({
    required this.title,
    required this.icon,
    required this.initialOffset,
    required this.onClose,
    required this.body,
  });

  @override
  State<_FloatingWindowFrame> createState() => _FloatingWindowFrameState();
}

class _FloatingWindowFrameState extends State<_FloatingWindowFrame> {
  late Offset _pos;

  @override
  void initState() {
    super.initState();
    _pos = widget.initialOffset;
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Stack(
      children: [
        Positioned(
          left: _pos.dx,
          top: _pos.dy,
          child: Material(
            elevation: 16,
            borderRadius: BorderRadius.circular(10),
            color: cs.surface,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minWidth: 380, maxWidth: 520),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Draggable title bar
                  GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onPanUpdate: (d) =>
                        setState(() => _pos = _pos + d.delta),
                    child: Container(
                      height: 36,
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      decoration: BoxDecoration(
                        color: cs.surfaceContainerHighest,
                        borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(10)),
                      ),
                      child: Row(
                        children: [
                          Icon(widget.icon, size: 14,
                              color: cs.onSurfaceVariant),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(widget.title,
                                style: Theme.of(context)
                                    .textTheme
                                    .titleSmall
                                    ?.copyWith(fontSize: 12)),
                          ),
                          // Red X — always closes without saving
                          SizedBox(
                            width: 24,
                            height: 24,
                            child: IconButton(
                              padding: EdgeInsets.zero,
                              iconSize: 15,
                              icon: const Icon(Icons.close,
                                  color: Colors.red),
                              tooltip: 'Fermer',
                              onPressed: widget.onClose,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  // Window body
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: widget.body,
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Note view window
// ---------------------------------------------------------------------------

void showNoteViewWindow(BuildContext context, NoteRow note) {
  _insertWindow(
    context,
    note.title.isNotEmpty ? note.title : 'Note',
    Icons.sticky_note_2_outlined,
    (close) => _NoteViewBody(note: note, onWindowClose: close),
  );
}

class _NoteViewBody extends ConsumerWidget {
  final NoteRow note;
  final VoidCallback onWindowClose;

  const _NoteViewBody({required this.note, required this.onWindowClose});

  Future<void> _delete(BuildContext ctx, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: ctx,
      builder: (dCtx) => AlertDialog(
        title: const Text('Supprimer cette note ?'),
        content: Text(note.title.isNotEmpty
            ? '"${note.title}"'
            : 'Cette note sera supprimée définitivement.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dCtx).pop(false),
            child: const Text('Conserver'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.of(dCtx).pop(true),
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await deleteNote(ref, note.id);
      onWindowClose();
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (note.title.isNotEmpty) ...[
          Text(note.title,
              style: Theme.of(context)
                  .textTheme
                  .titleSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
        ],
        ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 300),
          child: SingleChildScrollView(
            child: SelectionArea(
              child: Text(
                note.content.isNotEmpty ? note.content : '(contenu vide)',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: note.content.isEmpty ? cs.onSurfaceVariant : null,
                      fontStyle:
                          note.content.isEmpty ? FontStyle.italic : null,
                      height: 1.6,
                    ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 14),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            TextButton.icon(
              icon: const Icon(Icons.edit_outlined, size: 15),
              label: const Text('Éditer'),
              onPressed: () => showNoteEditWindow(context, note),
            ),
            const SizedBox(width: 6),
            TextButton.icon(
              icon: const Icon(Icons.delete_outline,
                  size: 15, color: Colors.red),
              label: const Text('Supprimer',
                  style: TextStyle(color: Colors.red)),
              onPressed: () => _delete(context, ref),
            ),
          ],
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Note edit window  (X = cancel, Confirmer = save + close)
// ---------------------------------------------------------------------------

void showNoteEditWindow(BuildContext context, NoteRow note) {
  _insertWindow(
    context,
    'Éditer${note.title.isNotEmpty ? " — ${note.title}" : ""}',
    Icons.edit_outlined,
    (close) => _NoteEditBody(note: note, onSaved: close),
    initialOffset: const Offset(240, 160),
  );
}

class _NoteEditBody extends ConsumerStatefulWidget {
  final NoteRow note;
  final VoidCallback onSaved;

  const _NoteEditBody({required this.note, required this.onSaved});

  @override
  ConsumerState<_NoteEditBody> createState() => _NoteEditBodyState();
}

class _NoteEditBodyState extends ConsumerState<_NoteEditBody> {
  late final TextEditingController _titleCtrl;
  late final TextEditingController _contentCtrl;

  @override
  void initState() {
    super.initState();
    _titleCtrl = TextEditingController(text: widget.note.title);
    _contentCtrl = TextEditingController(text: widget.note.content);
  }

  @override
  void dispose() {
    _titleCtrl.dispose();
    _contentCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    await updateNote(ref, widget.note.id,
        _titleCtrl.text.trim(), _contentCtrl.text.trim());
    widget.onSaved();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: _titleCtrl,
          decoration: const InputDecoration(
            labelText: 'Titre',
            isDense: true,
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _contentCtrl,
          decoration: const InputDecoration(
            labelText: 'Contenu',
            isDense: true,
            border: OutlineInputBorder(),
            alignLabelWithHint: true,
          ),
          minLines: 4,
          maxLines: 12,
          autofocus: true,
        ),
        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerRight,
          child: FilledButton(
              onPressed: _save, child: const Text('Confirmer')),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Note add window  (X = cancel without saving, Ajouter = save + close)
// ---------------------------------------------------------------------------

void showNoteAddWindow(
    BuildContext context, NoteAttachment attachment, int attachmentId) {
  _insertWindow(
    context,
    'Nouvelle note',
    Icons.add_circle_outline,
    (close) => _NoteAddBody(
        attachment: attachment, attachmentId: attachmentId, onAdded: close),
    initialOffset: const Offset(220, 150),
  );
}

class _NoteAddBody extends ConsumerStatefulWidget {
  final NoteAttachment attachment;
  final int attachmentId;
  final VoidCallback onAdded;

  const _NoteAddBody({
    required this.attachment,
    required this.attachmentId,
    required this.onAdded,
  });

  @override
  ConsumerState<_NoteAddBody> createState() => _NoteAddBodyState();
}

class _NoteAddBodyState extends ConsumerState<_NoteAddBody> {
  final _titleCtrl = TextEditingController();
  final _contentCtrl = TextEditingController();

  @override
  void dispose() {
    _titleCtrl.dispose();
    _contentCtrl.dispose();
    super.dispose();
  }

  Future<void> _add() async {
    final content = _contentCtrl.text.trim();
    if (content.isEmpty) return;
    switch (widget.attachment) {
      case NoteAttachment.entity:
        await addNoteForEntity(
            ref, widget.attachmentId, _titleCtrl.text.trim(), content);
      case NoteAttachment.subject:
        await addNoteForSubject(
            ref, widget.attachmentId, _titleCtrl.text.trim(), content);
      case NoteAttachment.turn:
        await addNoteForTurn(
            ref, widget.attachmentId, _titleCtrl.text.trim(), content);
    }
    widget.onAdded();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: _titleCtrl,
          decoration: const InputDecoration(
            labelText: 'Titre (optionnel)',
            isDense: true,
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _contentCtrl,
          decoration: const InputDecoration(
            labelText: 'Contenu *',
            isDense: true,
            border: OutlineInputBorder(),
            alignLabelWithHint: true,
          ),
          minLines: 4,
          maxLines: 12,
          autofocus: true,
        ),
        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerRight,
          child: FilledButton.icon(
            icon: const Icon(Icons.add, size: 15),
            label: const Text('Ajouter'),
            onPressed: _add,
          ),
        ),
      ],
    );
  }
}
