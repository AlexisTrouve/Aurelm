import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/database.dart';
import '../../../providers/notes_provider.dart';
import '../../../widgets/common/floating_window.dart';

/// Which object a note is attached to.
enum NoteAttachment { entity, subject, turn, civ }

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
      NoteAttachment.civ     => ref.watch(civNotesProvider(widget.attachmentId)),
    };
    final notes = notesAsync.valueOrNull ?? [];
    final cs = Theme.of(context).colorScheme;
    final railW = _collapsed ? _kCollapsedWidth : _kRailWidth;

    // Row-based layout — gives the main content bounded height constraints
    // (Stack + AnimatedPadding caused unbounded height → SingleChildScrollView
    // rendered at intrinsic size 0 → invisible body content).
    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Rail background strip
        AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
          width: railW,
          child: Container(
            decoration: BoxDecoration(
              color: cs.surfaceContainerLow,
              border: Border(
                right: BorderSide(color: cs.outlineVariant, width: 0.5),
              ),
            ),
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                // Toggle button at the top
                Positioned(
                  top: 2, left: 0, right: 0,
                  child: Center(child: SizedBox(
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
                  )),
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
            ),
          ),
        ),

        // Main content fills remaining space with bounded constraints
        Expanded(child: widget.child),
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
                // Star icon for pinned notes, regular icon otherwise
                Icon(
                  widget.note.pinned == 1 ? Icons.star : Icons.sticky_note_2,
                  size: 14,
                  color: widget.note.pinned == 1
                      ? Colors.amber
                      : (_hovered ? cs.primary : cs.onSurfaceVariant),
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
// Draggable floating window infrastructure — delegated to floating_window.dart
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Note view window
// ---------------------------------------------------------------------------

void showNoteViewWindow(BuildContext context, NoteRow note) {
  insertFloatingWindow(
    context,
    note.title.isNotEmpty ? note.title : 'Note',
    Icons.sticky_note_2_outlined,
    (close) => _NoteViewBody(note: note, onWindowClose: close),
  );
}

class _NoteViewBody extends ConsumerStatefulWidget {
  final NoteRow note;
  final VoidCallback onWindowClose;

  const _NoteViewBody({required this.note, required this.onWindowClose});

  @override
  ConsumerState<_NoteViewBody> createState() => _NoteViewBodyState();
}

class _NoteViewBodyState extends ConsumerState<_NoteViewBody> {
  /// Local pin state — updated immediately on click, persisted to DB
  late bool _pinned;

  @override
  void initState() {
    super.initState();
    _pinned = widget.note.pinned == 1;
  }

  Future<void> _togglePin() async {
    final next = !_pinned;
    setState(() => _pinned = next);
    await toggleNotePinned(ref, widget.note.id, next);
  }

  Future<void> _delete(BuildContext ctx) async {
    final confirmed = await showDialog<bool>(
      context: ctx,
      builder: (dCtx) => AlertDialog(
        title: const Text('Supprimer cette note ?'),
        content: Text(widget.note.title.isNotEmpty
            ? '"${widget.note.title}"'
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
      await deleteNote(ref, widget.note.id);
      widget.onWindowClose();
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final note = widget.note;
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
          children: [
            // Pin/important toggle — local state, immediate visual update
            Tooltip(
              message: _pinned ? 'Retirer des importants' : 'Marquer comme important',
              child: TextButton.icon(
                icon: Icon(
                  _pinned ? Icons.star : Icons.star_border,
                  size: 16,
                  color: _pinned ? Colors.amber : cs.onSurfaceVariant,
                ),
                label: Text(
                  'Important',
                  style: TextStyle(
                    color: _pinned ? Colors.amber.shade700 : cs.onSurfaceVariant,
                    fontWeight: _pinned ? FontWeight.w600 : FontWeight.normal,
                  ),
                ),
                onPressed: _togglePin,
              ),
            ),
            const Spacer(),
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
              onPressed: () => _delete(context),
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
  insertFloatingWindow(
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
  late bool _pinned;

  @override
  void initState() {
    super.initState();
    _titleCtrl = TextEditingController(text: widget.note.title);
    _contentCtrl = TextEditingController(text: widget.note.content);
    _pinned = widget.note.pinned == 1;
  }

  @override
  void dispose() {
    _titleCtrl.dispose();
    _contentCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    // Save title + content, then toggle pin if changed
    await updateNote(ref, widget.note.id,
        _titleCtrl.text.trim(), _contentCtrl.text.trim());
    if (_pinned != (widget.note.pinned == 1)) {
      await toggleNotePinned(ref, widget.note.id, _pinned);
    }
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
        Row(
          children: [
            // Pin toggle inline in edit mode
            _InlinePinToggle(
              pinned: _pinned,
              onToggle: (v) => setState(() => _pinned = v),
            ),
            const Spacer(),
            FilledButton(
                onPressed: _save, child: const Text('Confirmer')),
          ],
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
  insertFloatingWindow(
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
    try {
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
        case NoteAttachment.civ:
          await addNoteForCiv(
              ref, widget.attachmentId, _titleCtrl.text.trim(), content);
      }
      widget.onAdded();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erreur: $e'), backgroundColor: Colors.red),
        );
      }
    }
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

// ---------------------------------------------------------------------------
// Pin toggle button — used in note view window (reads DB, toggles directly)
// ---------------------------------------------------------------------------

// _PinToggleButton supprime -- le toggle pin est maintenant inline
// dans _NoteViewBodyState et _NoteEditBodyState

// ---------------------------------------------------------------------------
// Inline pin toggle — used in edit window (local state, saved on confirm)
// ---------------------------------------------------------------------------

class _InlinePinToggle extends StatelessWidget {
  final bool pinned;
  final ValueChanged<bool> onToggle;

  const _InlinePinToggle({required this.pinned, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return InkWell(
      borderRadius: BorderRadius.circular(6),
      onTap: () => onToggle(!pinned),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              pinned ? Icons.star : Icons.star_border,
              size: 16,
              color: pinned ? Colors.amber : cs.onSurfaceVariant,
            ),
            const SizedBox(width: 4),
            Text(
              'Important',
              style: TextStyle(
                fontSize: 12,
                color: pinned ? Colors.amber.shade700 : cs.onSurfaceVariant,
                fontWeight: pinned ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
