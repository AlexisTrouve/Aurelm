import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/database.dart';
import '../../../providers/notes_provider.dart';
import '../../../widgets/common/section_header.dart';
import 'notes_menu_button.dart' show NoteAttachment;

/// Reusable notes panel — shows a list of GM notes for an entity/subject/turn,
/// with add, edit (inline), and remove (confirmation popup) support.
///
/// Usage:
///   NotesPanel(attachment: NoteAttachment.entity, attachmentId: entityId)
class NotesPanel extends ConsumerWidget {
  final NoteAttachment attachment;
  final int attachmentId;

  const NotesPanel({
    super.key,
    required this.attachment,
    required this.attachmentId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notesAsync = switch (attachment) {
      NoteAttachment.entity =>
        ref.watch(entityNotesProvider(attachmentId)),
      NoteAttachment.subject =>
        ref.watch(subjectNotesProvider(attachmentId)),
      NoteAttachment.turn =>
        ref.watch(turnNotesProvider(attachmentId)),
    };

    return notesAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (e, _) => Text('Erreur notes: $e'),
      data: (noteList) => _NotesPanelContent(
        notes: noteList,
        attachment: attachment,
        attachmentId: attachmentId,
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Content widget (stateful — handles expand/edit state)
// ---------------------------------------------------------------------------

class _NotesPanelContent extends ConsumerStatefulWidget {
  final List<NoteRow> notes;
  final NoteAttachment attachment;
  final int attachmentId;

  const _NotesPanelContent({
    required this.notes,
    required this.attachment,
    required this.attachmentId,
  });

  @override
  ConsumerState<_NotesPanelContent> createState() => _NotesPanelContentState();
}

class _NotesPanelContentState extends ConsumerState<_NotesPanelContent> {
  // Which note is currently expanded to show Edit/Remove buttons
  int? _expandedNoteId;
  // Which note is currently in edit mode
  int? _editingNoteId;
  // Controllers for the inline edit form
  final _editTitleCtrl = TextEditingController();
  final _editContentCtrl = TextEditingController();
  // Controller for the add form (shown in a dialog)
  bool _showAddForm = false;
  final _addTitleCtrl = TextEditingController();
  final _addContentCtrl = TextEditingController();

  @override
  void dispose() {
    _editTitleCtrl.dispose();
    _editContentCtrl.dispose();
    _addTitleCtrl.dispose();
    _addContentCtrl.dispose();
    super.dispose();
  }

  void _startEdit(NoteRow note) {
    setState(() {
      _editingNoteId = note.id;
      _editTitleCtrl.text = note.title;
      _editContentCtrl.text = note.content;
    });
  }

  void _cancelEdit() {
    setState(() {
      _editingNoteId = null;
    });
  }

  Future<void> _confirmEdit(int noteId) async {
    await updateNote(
      ref,
      noteId,
      _editTitleCtrl.text.trim(),
      _editContentCtrl.text.trim(),
    );
    if (mounted) {
      setState(() {
        _editingNoteId = null;
        _expandedNoteId = null;
      });
    }
  }

  Future<void> _confirmDelete(BuildContext context, NoteRow note) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Supprimer cette note ?'),
        content: Text(
          note.title.isNotEmpty ? '"${note.title}"' : 'Cette note sera supprimée définitivement.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Conserver'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await deleteNote(ref, note.id);
      if (mounted) {
        setState(() {
          if (_expandedNoteId == note.id) _expandedNoteId = null;
          if (_editingNoteId == note.id) _editingNoteId = null;
        });
      }
    }
  }

  Future<void> _addNote() async {
    final title = _addTitleCtrl.text.trim();
    final content = _addContentCtrl.text.trim();
    if (content.isEmpty) return;

    switch (widget.attachment) {
      case NoteAttachment.entity:
        await addNoteForEntity(ref, widget.attachmentId, title, content);
      case NoteAttachment.subject:
        await addNoteForSubject(ref, widget.attachmentId, title, content);
      case NoteAttachment.turn:
        await addNoteForTurn(ref, widget.attachmentId, title, content);
    }

    if (mounted) {
      setState(() {
        _showAddForm = false;
        _addTitleCtrl.clear();
        _addContentCtrl.clear();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section header with "+" button
        Row(
          children: [
            Expanded(
              child: SectionHeader(
                title: 'Notes (${widget.notes.length})',
              ),
            ),
            IconButton(
              icon: Icon(
                _showAddForm ? Icons.close : Icons.add,
                size: 18,
              ),
              tooltip: _showAddForm ? 'Annuler' : 'Ajouter une note',
              onPressed: () {
                setState(() {
                  _showAddForm = !_showAddForm;
                  if (!_showAddForm) {
                    _addTitleCtrl.clear();
                    _addContentCtrl.clear();
                  }
                });
              },
            ),
          ],
        ),

        // Add form
        if (_showAddForm) _AddNoteForm(
          titleCtrl: _addTitleCtrl,
          contentCtrl: _addContentCtrl,
          onConfirm: _addNote,
          onCancel: () => setState(() {
            _showAddForm = false;
            _addTitleCtrl.clear();
            _addContentCtrl.clear();
          }),
        ),

        // Notes list
        if (widget.notes.isEmpty && !_showAddForm)
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 8),
            child: Text(
              'Aucune note',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                    fontStyle: FontStyle.italic,
                  ),
            ),
          )
        else
          ...widget.notes.map((note) => _NoteCard(
                note: note,
                isExpanded: _expandedNoteId == note.id,
                isEditing: _editingNoteId == note.id,
                editTitleCtrl: _editTitleCtrl,
                editContentCtrl: _editContentCtrl,
                onTap: () => setState(() {
                  _expandedNoteId =
                      _expandedNoteId == note.id ? null : note.id;
                  // Close edit mode if collapsing
                  if (_expandedNoteId == null) _editingNoteId = null;
                }),
                onEdit: () => _startEdit(note),
                onEditConfirm: () => _confirmEdit(note.id),
                onEditCancel: _cancelEdit,
                onDelete: () => _confirmDelete(context, note),
              )),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Note card widget — show/expand/edit/delete
// ---------------------------------------------------------------------------

class _NoteCard extends StatelessWidget {
  final NoteRow note;
  final bool isExpanded;
  final bool isEditing;
  final TextEditingController editTitleCtrl;
  final TextEditingController editContentCtrl;
  final VoidCallback onTap;
  final VoidCallback onEdit;
  final VoidCallback onEditConfirm;
  final VoidCallback onEditCancel;
  final VoidCallback onDelete;

  const _NoteCard({
    required this.note,
    required this.isExpanded,
    required this.isEditing,
    required this.editTitleCtrl,
    required this.editContentCtrl,
    required this.onTap,
    required this.onEdit,
    required this.onEditConfirm,
    required this.onEditCancel,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      decoration: BoxDecoration(
        color: cs.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isExpanded
              ? cs.primary.withValues(alpha: 0.4)
              : cs.outline.withValues(alpha: 0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header — always visible, tap to expand
          InkWell(
            onTap: onTap,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Row(
                children: [
                  Icon(
                    isExpanded
                        ? Icons.keyboard_arrow_up
                        : Icons.keyboard_arrow_down,
                    size: 16,
                    color: cs.onSurfaceVariant,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      note.title.isNotEmpty ? note.title : '(sans titre)',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: note.title.isNotEmpty
                                ? null
                                : cs.onSurfaceVariant,
                            fontStyle: note.title.isNotEmpty
                                ? FontStyle.normal
                                : FontStyle.italic,
                          ),
                    ),
                  ),
                  if (!isExpanded && note.content.isNotEmpty)
                    Flexible(
                      child: Text(
                        // First ~60 chars as preview
                        note.content.length > 60
                            ? '${note.content.substring(0, 60)}…'
                            : note.content,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: cs.onSurfaceVariant,
                            ),
                        overflow: TextOverflow.ellipsis,
                        maxLines: 1,
                      ),
                    ),
                ],
              ),
            ),
          ),

          // Expanded content
          if (isExpanded) ...[
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(12),
              child: isEditing
                  ? _EditForm(
                      titleCtrl: editTitleCtrl,
                      contentCtrl: editContentCtrl,
                      onConfirm: onEditConfirm,
                      onCancel: onEditCancel,
                    )
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Content text
                        SelectionArea(
                          child: Text(
                            note.content.isNotEmpty
                                ? note.content
                                : '(contenu vide)',
                            style: Theme.of(context)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(
                                  color: note.content.isNotEmpty
                                      ? null
                                      : cs.onSurfaceVariant,
                                  fontStyle: note.content.isNotEmpty
                                      ? FontStyle.normal
                                      : FontStyle.italic,
                                ),
                          ),
                        ),
                        // Edit/Delete buttons
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            TextButton.icon(
                              icon: const Icon(Icons.edit_outlined, size: 16),
                              label: const Text('Éditer'),
                              onPressed: onEdit,
                            ),
                            const SizedBox(width: 8),
                            TextButton.icon(
                              icon: const Icon(Icons.delete_outline,
                                  size: 16, color: Colors.red),
                              label: const Text('Supprimer',
                                  style: TextStyle(color: Colors.red)),
                              onPressed: onDelete,
                            ),
                          ],
                        ),
                      ],
                    ),
            ),
          ],
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Inline edit form — confirm button bottom-right
// ---------------------------------------------------------------------------

class _EditForm extends StatelessWidget {
  final TextEditingController titleCtrl;
  final TextEditingController contentCtrl;
  final VoidCallback onConfirm;
  final VoidCallback onCancel;

  const _EditForm({
    required this.titleCtrl,
    required this.contentCtrl,
    required this.onConfirm,
    required this.onCancel,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: titleCtrl,
          decoration: const InputDecoration(
            labelText: 'Titre',
            isDense: true,
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: contentCtrl,
          decoration: const InputDecoration(
            labelText: 'Contenu',
            isDense: true,
            border: OutlineInputBorder(),
            alignLabelWithHint: true,
          ),
          minLines: 3,
          maxLines: 8,
        ),
        const SizedBox(height: 8),
        // Confirm / Cancel — confirm bottom-right
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            TextButton(
              onPressed: onCancel,
              child: const Text('Annuler'),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: onConfirm,
              child: const Text('Confirmer'),
            ),
          ],
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Add note form (shown inline below header)
// ---------------------------------------------------------------------------

class _AddNoteForm extends StatelessWidget {
  final TextEditingController titleCtrl;
  final TextEditingController contentCtrl;
  final VoidCallback onConfirm;
  final VoidCallback onCancel;

  const _AddNoteForm({
    required this.titleCtrl,
    required this.contentCtrl,
    required this.onConfirm,
    required this.onCancel,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primaryContainer.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: titleCtrl,
            decoration: const InputDecoration(
              labelText: 'Titre (optionnel)',
              isDense: true,
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: contentCtrl,
            decoration: const InputDecoration(
              labelText: 'Contenu *',
              isDense: true,
              border: OutlineInputBorder(),
              alignLabelWithHint: true,
            ),
            minLines: 3,
            maxLines: 8,
            autofocus: true,
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                onPressed: onCancel,
                child: const Text('Annuler'),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                icon: const Icon(Icons.save_outlined, size: 16),
                label: const Text('Ajouter'),
                onPressed: onConfirm,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
