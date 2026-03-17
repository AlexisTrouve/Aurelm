import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../data/database.dart';
import '../../providers/subject_provider.dart';
import '../../providers/civilization_provider.dart';
import '../../providers/favorites_provider.dart';
import '../../providers/database_provider.dart';
import '../../models/subject_with_details.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/section_header.dart';
import '../entities/widgets/notes_menu_button.dart';

// Available tags for subjects (domain tags assigned by LLM pipeline).
const _kTagVocab = [
  'militaire',
  'politique',
  'économie',
  'religion',
  'technologie',
  'diplomatique',
  'culturel',
  'géographique',
  'social',
  'exploration',
];

/// Detail page for a single subject — shows description, options, and all
/// resolution attempts with confidence percentages.
/// Supports inline edit mode (no popup).
class SubjectDetailScreen extends ConsumerWidget {
  final int subjectId;

  const SubjectDetailScreen({super.key, required this.subjectId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(subjectDetailProvider(subjectId));

    return detailAsync.when(
      loading: () => const Scaffold(body: LoadingIndicator()),
      error: (e, _) => Scaffold(body: ErrorView(message: e.toString())),
      data: (detail) {
        if (detail == null) {
          return Scaffold(
            appBar: AppBar(),
            body: const Center(child: Text('Sujet introuvable')),
          );
        }
        return _SubjectDetailStateful(detail: detail);
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Stateful shell — handles edit mode state
// ---------------------------------------------------------------------------

class _SubjectDetailStateful extends ConsumerStatefulWidget {
  final SubjectDetail detail;

  const _SubjectDetailStateful({required this.detail});

  @override
  ConsumerState<_SubjectDetailStateful> createState() =>
      _SubjectDetailStatefulState();
}

class _SubjectDetailStatefulState
    extends ConsumerState<_SubjectDetailStateful> {
  // Edit mode state
  bool _editMode = false;
  bool _saving = false;

  // GM-locked fields snapshot at edit mode entry — extended on save, never replaced
  Set<String> _gmFields = {};

  // Controllers (populated when entering edit mode)
  late TextEditingController _titleCtrl;
  late TextEditingController _descCtrl;
  late TextEditingController _quoteCtrl;
  String _direction = 'mj_to_pj';
  String _category = 'question';
  String _status = 'open';
  List<String> _editTags = [];

  @override
  void initState() {
    super.initState();
    _titleCtrl = TextEditingController();
    _descCtrl = TextEditingController();
    _quoteCtrl = TextEditingController();
  }

  @override
  void dispose() {
    _titleCtrl.dispose();
    _descCtrl.dispose();
    _quoteCtrl.dispose();
    super.dispose();
  }

  void _enterEditMode() {
    final s = widget.detail.subject;
    _titleCtrl.text = s.title;
    _descCtrl.text = s.description ?? '';
    _quoteCtrl.text = s.sourceQuote ?? '';
    _direction = s.direction;
    _category = s.category;
    _status = s.status;
    // Parse JSON tags array
    final rawTags = s.tags;
    _editTags = _parseTags(rawTags);
    // Snapshot current GM locks to extend (not replace) on save
    _gmFields = Set<String>.from(
      ref.read(subjectGmFieldsProvider(widget.detail.subject.id)).valueOrNull ?? {},
    );
    setState(() => _editMode = true);
  }

  void _cancelEditMode() => setState(() => _editMode = false);

  Future<void> _saveEditMode() async {
    final title = _titleCtrl.text.trim();
    if (title.isEmpty) return;
    setState(() => _saving = true);
    try {
      await updateSubject(
        ref,
        subjectId: widget.detail.subject.id,
        title: title,
        description: _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim(),
        direction: _direction,
        category: _category,
        status: _status,
        tags: _editTags,
        sourceQuote: _quoteCtrl.text.trim(),
      );

      // Auto-lock edited fields — title is always locked (always has content).
      // Empty fields are not locked: pipeline can re-fill them if GM cleared them.
      final locked = Set<String>.from(_gmFields);
      locked.add('title'); // title always non-empty (validated above)
      if (_descCtrl.text.trim().isNotEmpty) locked.add('description');
      if (_editTags.isNotEmpty) locked.add('tags');
      final db = ref.read(databaseProvider);
      if (db != null) {
        await db.subjectDao.updateGmFields(widget.detail.subject.id, locked);
      }

      if (mounted) setState(() => _editMode = false);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  /// Remove a single field from GM locks after user confirmation.
  Future<void> _unlockField(BuildContext context, WidgetRef ref, int subjectId, String field) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Déverrouiller ce champ ?'),
        content: const Text(
          'Le pipeline pourra modifier ce champ lors du prochain run.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Déverrouiller'),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      final db = ref.read(databaseProvider);
      if (db == null) return;
      final current =
          ref.read(subjectGmFieldsProvider(subjectId)).valueOrNull ?? {};
      await db.subjectDao.updateGmFields(
        subjectId,
        Set<String>.from(current)..remove(field),
      );
    }
  }

  /// Parse JSON tag array string → list of strings.
  List<String> _parseTags(String raw) {
    final clean = raw.replaceAll(RegExp(r'[\[\]\s]'), '');
    if (clean.isEmpty) return [];
    return clean
        .split(',')
        .map((t) => t.replaceAll('"', '').trim())
        .where((t) => t.isNotEmpty)
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    // Re-watch detail to get live updates even in edit mode
    final detailAsync = ref.watch(subjectDetailProvider(widget.detail.subject.id));
    final detail = detailAsync.maybeWhen(data: (d) => d, orElse: () => widget.detail);
    if (detail == null) return const SizedBox.shrink();

    return Scaffold(
      appBar: _editMode ? _buildEditAppBar() : _buildViewAppBar(context, ref, detail),
      body: NotesSideRail(
        attachment: NoteAttachment.subject,
        attachmentId: detail.subject.id,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: _editMode
              ? _buildEditBody(context, ref)
              : _buildViewBody(context, ref, detail),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // App bars
  // ---------------------------------------------------------------------------

  AppBar _buildViewAppBar(BuildContext context, WidgetRef ref, SubjectDetail detail) {
    final s = detail.subject;
    final isOpen = s.status == 'open';
    final isFav = ref.watch(favoritesProvider).contains('subject_${s.id}');

    return AppBar(
      toolbarHeight: 44,
      leadingWidth: 88,
      title: Text(s.title, overflow: TextOverflow.ellipsis),
      leading: IconButton(
        icon: const Icon(Icons.arrow_back),
        onPressed: () =>
            context.canPop() ? context.pop() : context.go('/subjects'),
      ),
      actions: [
        // Favorite toggle
        IconButton(
          icon: Icon(
            isFav ? Icons.star : Icons.star_border,
            color: isFav ? Colors.amber : null,
          ),
          tooltip: isFav ? 'Retirer des favoris' : 'Ajouter aux favoris',
          onPressed: () => ref
              .read(favoritesProvider.notifier)
              .toggle('subject', s.id, s.civId),
        ),
        // Edit button
        IconButton(
          icon: const Icon(Icons.edit_outlined),
          tooltip: 'Modifier',
          onPressed: _enterEditMode,
        ),
        // Close subject menu
        if (isOpen)
          PopupMenuButton<String>(
            icon: const Icon(Icons.check_circle_outline),
            tooltip: 'Clore le sujet',
            onSelected: (status) =>
                _confirmClose(context, ref, s.id, status),
            itemBuilder: (_) => const [
              PopupMenuItem(
                value: 'resolved',
                child: Row(
                  children: [
                    Icon(Icons.check_circle, color: Colors.green, size: 18),
                    SizedBox(width: 8),
                    Text('Marquer comme résolu'),
                  ],
                ),
              ),
              PopupMenuItem(
                value: 'abandoned',
                child: Row(
                  children: [
                    Icon(Icons.cancel, color: Colors.red, size: 18),
                    SizedBox(width: 8),
                    Text('Abandonner'),
                  ],
                ),
              ),
            ],
          ),
      ],
    );
  }

  AppBar _buildEditAppBar() {
    return AppBar(
      toolbarHeight: 44,
      leading: IconButton(
        icon: const Icon(Icons.close),
        onPressed: _cancelEditMode,
      ),
      title: const Text('Modifier le sujet'),
      actions: [
        Padding(
          padding: const EdgeInsets.only(right: 12),
          child: FilledButton(
            onPressed: _saving ? null : _saveEditMode,
            child: _saving
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Enregistrer'),
          ),
        ),
      ],
    );
  }

  // ---------------------------------------------------------------------------
  // View body (read-only)
  // ---------------------------------------------------------------------------

  Widget _buildViewBody(BuildContext context, WidgetRef ref, SubjectDetail detail) {
    final s = detail.subject;
    final isMjToPj = s.direction == 'mj_to_pj';
    final isResolved = s.status == 'resolved';

    final tags = _parseTags(s.tags);
    // GM-locked fields — shown as small amber lock badges next to protected content
    final gmFields =
        ref.watch(subjectGmFieldsProvider(s.id)).valueOrNull ?? {};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header badges
        Wrap(
          spacing: 8,
          runSpacing: 4,
          children: [
            _DirectionBadge(isMjToPj: isMjToPj),
            _CategoryBadge(category: s.category),
            _StatusBadge(status: s.status),
            if (detail.sourceTurnId != 0)
              _TurnChip(
                turnId: detail.sourceTurnId,
                label: 'T${detail.sourceTurnNumber} · ${detail.civName}',
                highlight: (s.sourceQuote?.isNotEmpty == true)
                    ? s.sourceQuote
                    : s.title,
              ),
          ],
        ),

        // Tags
        if (tags.isNotEmpty) ...[
          const SizedBox(height: 10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(
                child: Wrap(
                  spacing: 6,
                  children: tags
                      .map((t) => Chip(
                            label: Text(t),
                            materialTapTargetSize:
                                MaterialTapTargetSize.shrinkWrap,
                            visualDensity: VisualDensity.compact,
                            labelStyle: Theme.of(context).textTheme.labelSmall,
                          ))
                      .toList(),
                ),
              ),
              if (gmFields.contains('tags'))
                _SubjectGmLockBadge(
                  tooltip: 'Tags protégés par le GM — cliquer pour déverrouiller',
                  onUnlock: () => _unlockField(context, ref, s.id, 'tags'),
                ),
            ],
          ),
        ],

        // Description
        if (s.description != null && s.description!.isNotEmpty) ...[
          const SizedBox(height: 16),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(s.description!,
                    style: Theme.of(context).textTheme.bodyMedium),
              ),
              if (gmFields.contains('description'))
                _SubjectGmLockBadge(
                  tooltip: 'Description protégée par le GM — cliquer pour déverrouiller',
                  onUnlock: () => _unlockField(context, ref, s.id, 'description'),
                ),
            ],
          ),
        ],

        // Verbatim source quote
        if (s.sourceQuote != null && s.sourceQuote!.isNotEmpty) ...[
          const SizedBox(height: 8),
          _SourceQuoteTile(
              quote: s.sourceQuote!, label: 'Extrait source (tour MJ)'),
        ],

        // Options
        if (detail.options.isNotEmpty) ...[
          const SizedBox(height: 24),
          const SectionHeader(title: 'Options proposées'),
          const SizedBox(height: 8),
          ...detail.options.map((opt) => _OptionTile(
                option: opt,
                isChosen: detail.bestResolution?.chosenOptionId == opt.id,
              )),
        ],

        // Resolutions
        const SizedBox(height: 24),
        SectionHeader(
          title: isResolved
              ? 'Résolutions (${detail.resolutionCount})'
              : 'Tentatives de résolution (${detail.resolutionCount})',
        ),
        const SizedBox(height: 8),

        if (detail.allResolutions.isEmpty)
          Text(
            'Aucune résolution détectée',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                  fontStyle: FontStyle.italic,
                ),
          )
        else
          ...detail.allResolutions.map((r) => _ResolutionCard(
                resolution: r,
                isAccepted:
                    detail.bestResolution?.id == r.resolution.id && isResolved,
              )),
      ],
    );
  }

  // ---------------------------------------------------------------------------
  // Edit body (inline form)
  // ---------------------------------------------------------------------------

  Widget _buildEditBody(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Status
        DropdownButtonFormField<String>(
          decoration: const InputDecoration(
            labelText: 'Statut',
            border: OutlineInputBorder(),
            isDense: true,
          ),
          value: _status,
          items: const [
            DropdownMenuItem(value: 'open', child: Text('Ouvert')),
            DropdownMenuItem(value: 'resolved', child: Text('Résolu')),
            DropdownMenuItem(value: 'abandoned', child: Text('Abandonné')),
            DropdownMenuItem(value: 'superseded', child: Text('Supplanté')),
          ],
          onChanged: (v) => setState(() => _status = v!),
        ),
        const SizedBox(height: 12),

        // Direction
        DropdownButtonFormField<String>(
          decoration: const InputDecoration(
            labelText: 'Direction',
            border: OutlineInputBorder(),
            isDense: true,
          ),
          value: _direction,
          items: const [
            DropdownMenuItem(value: 'mj_to_pj', child: Text('MJ → PJ')),
            DropdownMenuItem(value: 'pj_to_mj', child: Text('PJ → MJ')),
          ],
          onChanged: (v) => setState(() => _direction = v!),
        ),
        const SizedBox(height: 12),

        // Category
        DropdownButtonFormField<String>(
          decoration: const InputDecoration(
            labelText: 'Catégorie',
            border: OutlineInputBorder(),
            isDense: true,
          ),
          value: _category,
          items: const [
            DropdownMenuItem(value: 'choice', child: Text('Choix')),
            DropdownMenuItem(value: 'question', child: Text('Question')),
            DropdownMenuItem(value: 'initiative', child: Text('Initiative')),
            DropdownMenuItem(value: 'request', child: Text('Demande')),
          ],
          onChanged: (v) => setState(() => _category = v!),
        ),
        const SizedBox(height: 12),

        // Title
        TextField(
          controller: _titleCtrl,
          decoration: const InputDecoration(
            labelText: 'Titre',
            border: OutlineInputBorder(),
            isDense: true,
          ),
          textCapitalization: TextCapitalization.sentences,
        ),
        const SizedBox(height: 12),

        // Description
        TextField(
          controller: _descCtrl,
          decoration: const InputDecoration(
            labelText: 'Description',
            border: OutlineInputBorder(),
            isDense: true,
          ),
          maxLines: 5,
          textCapitalization: TextCapitalization.sentences,
        ),
        const SizedBox(height: 12),

        // Source quote (verbatim extract from the GM turn)
        TextField(
          controller: _quoteCtrl,
          decoration: const InputDecoration(
            labelText: 'Extrait source (optionnel)',
            border: OutlineInputBorder(),
            isDense: true,
            hintText: 'Citation verbatim depuis le tour MJ…',
          ),
          maxLines: 4,
          textCapitalization: TextCapitalization.sentences,
        ),
        const SizedBox(height: 20),

        // Tags section
        _buildTagsEdit(context),
      ],
    );
  }

  Widget _buildTagsEdit(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(
          title: 'Tags',
          trailing: PopupMenuButton<String>(
            icon: const Icon(Icons.add, size: 18),
            tooltip: 'Ajouter un tag',
            onSelected: (tag) {
              if (!_editTags.contains(tag)) {
                setState(() => _editTags.add(tag));
              }
            },
            itemBuilder: (_) => _kTagVocab
                .where((t) => !_editTags.contains(t))
                .map((t) => PopupMenuItem(value: t, child: Text(t)))
                .toList(),
          ),
        ),
        const SizedBox(height: 6),
        if (_editTags.isEmpty)
          Text(
            'Aucun tag',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                  fontStyle: FontStyle.italic,
                ),
          )
        else
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: _editTags
                .map((t) => InputChip(
                      label: Text(t),
                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      visualDensity: VisualDensity.compact,
                      labelStyle: Theme.of(context).textTheme.labelSmall,
                      onDeleted: () =>
                          setState(() => _editTags.remove(t)),
                    ))
                .toList(),
          ),
      ],
    );
  }

  // ---------------------------------------------------------------------------
  // Close dialog
  // ---------------------------------------------------------------------------

  Future<void> _confirmClose(
      BuildContext context, WidgetRef ref, int subjectId, String status) async {
    final label = status == 'resolved' ? 'résolu' : 'abandonné';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Clore le sujet'),
        content: Text('Marquer ce sujet comme $label ?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: Text(status == 'resolved' ? 'Résolu' : 'Abandonné'),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      await closeSubject(ref, subjectId, status);
    }
  }
}

// ===========================================================================
// Read-only sub-widgets (unchanged from previous version)
// ===========================================================================

class _OptionTile extends StatelessWidget {
  final SubjectOptionRow option;
  final bool isChosen;

  const _OptionTile({required this.option, required this.isChosen});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isChosen
            ? Colors.green.withValues(alpha: 0.1)
            : Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isChosen
              ? Colors.green.withValues(alpha: 0.5)
              : Theme.of(context).colorScheme.outline.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: isChosen
                  ? Colors.green
                  : Theme.of(context).colorScheme.primaryContainer,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Text(
              option.isLibre ? 'L' : '${option.optionNumber}',
              style: TextStyle(
                color: isChosen
                    ? Colors.white
                    : Theme.of(context).colorScheme.onPrimaryContainer,
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(option.label,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          fontWeight:
                              isChosen ? FontWeight.bold : FontWeight.normal,
                        )),
                if (option.description != null && option.description!.isNotEmpty)
                  Text(option.description!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context)
                                .colorScheme
                                .onSurfaceVariant,
                          )),
              ],
            ),
          ),
          if (isChosen)
            const Icon(Icons.check_circle, color: Colors.green, size: 18),
        ],
      ),
    );
  }
}

class _ResolutionCard extends StatelessWidget {
  final ResolutionWithTurn resolution;
  final bool isAccepted;

  const _ResolutionCard({required this.resolution, required this.isAccepted});

  @override
  Widget build(BuildContext context) {
    final r = resolution.resolution;
    final pct = (r.confidence * 100).round();
    final barColor = pct >= 70
        ? Colors.green
        : pct >= 40
            ? Colors.orange
            : Colors.red;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isAccepted
            ? Colors.green.withValues(alpha: 0.07)
            : Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isAccepted
              ? Colors.green.withValues(alpha: 0.4)
              : Colors.transparent,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: r.confidence,
                    backgroundColor: Theme.of(context)
                        .colorScheme
                        .outline
                        .withValues(alpha: 0.2),
                    valueColor: AlwaysStoppedAnimation<Color>(barColor),
                    minHeight: 6,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Text(
                '$pct%',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: barColor,
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(width: 10),
              InkWell(
                onTap: () => context.push(
                  '/turns/${resolution.turnId}',
                  extra: {
                    'highlight':
                        (resolution.resolution.sourceQuote?.isNotEmpty == true)
                            ? resolution.resolution.sourceQuote
                            : resolution.resolution.resolutionText,
                  },
                ),
                borderRadius: BorderRadius.circular(4),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                  child: Text(
                    'T${resolution.turnNumber}',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: Theme.of(context).colorScheme.primary,
                          decoration: TextDecoration.underline,
                        ),
                  ),
                ),
              ),
              if (isAccepted) ...[
                const SizedBox(width: 6),
                const Icon(Icons.verified, color: Colors.green, size: 16),
              ],
            ],
          ),
          const SizedBox(height: 8),
          Text(r.resolutionText, style: Theme.of(context).textTheme.bodySmall),
          if (r.sourceQuote != null && r.sourceQuote!.isNotEmpty) ...[
            const SizedBox(height: 6),
            _SourceQuoteTile(quote: r.sourceQuote!, label: 'Extrait source'),
          ],
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Source quote — collapsible blockquote
// ---------------------------------------------------------------------------

class _SourceQuoteTile extends StatelessWidget {
  final String quote;
  final String label;

  const _SourceQuoteTile({required this.quote, required this.label});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Theme(
      data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
      child: ExpansionTile(
        tilePadding: EdgeInsets.zero,
        childrenPadding: EdgeInsets.zero,
        dense: true,
        leading: Icon(Icons.format_quote,
            size: 16, color: colorScheme.onSurfaceVariant),
        title: Text(
          label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
        ),
        children: [
          Container(
            width: double.infinity,
            margin: const EdgeInsets.only(bottom: 6),
            padding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(6),
              border: Border(
                left: BorderSide(
                  color: colorScheme.primary.withValues(alpha: 0.5),
                  width: 3,
                ),
              ),
            ),
            child: SelectableText(
              quote,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    fontStyle: FontStyle.italic,
                    color: colorScheme.onSurfaceVariant,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Badge widgets
// ---------------------------------------------------------------------------

class _DirectionBadge extends StatelessWidget {
  final bool isMjToPj;
  const _DirectionBadge({required this.isMjToPj});

  @override
  Widget build(BuildContext context) {
    final color = isMjToPj ? Colors.blue : Colors.purple;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        isMjToPj ? '→ MJ→PJ' : '← PJ→MJ',
        style: Theme.of(context)
            .textTheme
            .labelSmall
            ?.copyWith(color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}

class _CategoryBadge extends StatelessWidget {
  final String category;
  const _CategoryBadge({required this.category});

  @override
  Widget build(BuildContext context) {
    final color = switch (category) {
      'choice' => Colors.orange,
      'question' => Colors.cyan,
      'initiative' => Colors.purple,
      'request' => Colors.teal,
      _ => Colors.grey,
    };
    final label = switch (category) {
      'choice' => 'Choix',
      'question' => 'Question',
      'initiative' => 'Initiative',
      'request' => 'Demande',
      _ => category,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(label,
          style: Theme.of(context)
              .textTheme
              .labelSmall
              ?.copyWith(color: color, fontWeight: FontWeight.w600)),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final String status;
  const _StatusBadge({required this.status});

  @override
  Widget build(BuildContext context) {
    final (color, label) = switch (status) {
      'open' => (Colors.orange, 'Ouvert'),
      'resolved' => (Colors.green, 'Résolu'),
      'superseded' => (Colors.grey, 'Remplacé'),
      'abandoned' => (Colors.red, 'Abandonné'),
      _ => (Colors.grey, status),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(label,
          style: Theme.of(context)
              .textTheme
              .labelSmall
              ?.copyWith(color: color, fontWeight: FontWeight.w600)),
    );
  }
}

class _TurnChip extends StatelessWidget {
  final int turnId;
  final String label;
  final String? highlight;
  const _TurnChip({required this.turnId, required this.label, this.highlight});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => context.push(
        '/turns/$turnId',
        extra: highlight != null ? {'highlight': highlight} : null,
      ),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: Theme.of(context)
              .colorScheme
              .primaryContainer
              .withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
              color: Theme.of(context)
                  .colorScheme
                  .primary
                  .withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.open_in_new,
                size: 10,
                color: Theme.of(context).colorScheme.primary),
            const SizedBox(width: 4),
            Text(label,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                      fontWeight: FontWeight.w600,
                    )),
          ],
        ),
      ),
    );
  }
}

/// Small amber lock badge for GM-protected subject fields.
class _SubjectGmLockBadge extends StatelessWidget {
  final String tooltip;
  final VoidCallback onUnlock;

  const _SubjectGmLockBadge({required this.tooltip, required this.onUnlock});

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onUnlock,
        borderRadius: BorderRadius.circular(12),
        child: const Padding(
          padding: EdgeInsets.all(4),
          child: Icon(Icons.lock, size: 14, color: Colors.amber),
        ),
      ),
    );
  }
}