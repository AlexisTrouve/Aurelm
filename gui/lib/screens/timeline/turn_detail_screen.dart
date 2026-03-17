import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../data/database.dart';
import '../../providers/turn_provider.dart';
import '../../providers/entity_provider.dart';
import '../../providers/favorites_provider.dart';
import '../../providers/database_provider.dart';
import '../../utils/lore_linker.dart';
import '../../widgets/common/entity_type_icon.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/section_header.dart';
import '../entities/widgets/notes_menu_button.dart';

/// Full turn detail — GM segments with type labels, PJ content as a single
/// readable block. Search bar highlights matches across all text.
/// [highlightText]: optional entity name to highlight on open (from naming history links).
class TurnDetailScreen extends ConsumerStatefulWidget {
  final int turnId;
  final String? highlightText;

  const TurnDetailScreen({
    super.key,
    required this.turnId,
    this.highlightText,
  });

  @override
  ConsumerState<TurnDetailScreen> createState() => _TurnDetailScreenState();
}

class _TurnDetailScreenState extends ConsumerState<TurnDetailScreen> {
  // --------------- search state ---------------
  bool _searchVisible = false;
  final TextEditingController _searchCtrl = TextEditingController();
  final FocusNode _scaffoldFocus = FocusNode();
  final FocusNode _searchFocus = FocusNode();
  final ScrollController _scrollCtrl = ScrollController();
  // GlobalKeys to locate each text block for scroll-to-first-match
  final GlobalKey _summaryKey = GlobalKey();
  final GlobalKey _gmKey = GlobalKey();
  final GlobalKey _pjKey = GlobalKey();
  // Set in initState when opened with highlightText; cleared after first scroll
  bool _pendingScrollToMatch = false;
  String _query = '';

  // --------------- edit mode state ---------------
  bool _editMode = false;
  bool _saving = false;
  final TextEditingController _titleCtrl = TextEditingController();
  final TextEditingController _summaryCtrl = TextEditingController();
  List<String> _editTags = [];
  List<String> _editStrategy = [];
  // GM-locked fields snapshot — populated on _enterEditMode
  Set<String> _gmFields = {};

  @override
  void initState() {
    super.initState();
    // If opened via a naming history / mention link, pre-fill search and
    // schedule a scroll to the first match once data is loaded
    if (widget.highlightText != null) {
      _searchVisible = true;
      _query = widget.highlightText!;
      _searchCtrl.text = widget.highlightText!;
      _pendingScrollToMatch = true;
    }
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    _scaffoldFocus.dispose();
    _searchFocus.dispose();
    _scrollCtrl.dispose();
    _titleCtrl.dispose();
    _summaryCtrl.dispose();
    super.dispose();
  }

  // --------------- edit mode helpers ---------------

  List<String> _parseTags(String? raw) {
    if (raw == null || raw.isEmpty) return [];
    try {
      return List<String>.from(jsonDecode(raw));
    } catch (_) {
      return [];
    }
  }

  void _enterEditMode(TurnRow t) {
    // Snapshot current gm_fields so save can merge correctly
    _gmFields = ref.read(turnGmFieldsProvider(widget.turnId)).valueOrNull ?? {};
    _titleCtrl.text = t.title ?? '';
    _summaryCtrl.text = t.summary ?? '';
    _editTags = _parseTags(t.thematicTags);
    _editStrategy = _parseTags(t.playerStrategy);
    setState(() => _editMode = true);
  }

  void _cancelEditMode() => setState(() => _editMode = false);

  Future<void> _saveEditMode() async {
    final db = ref.read(databaseProvider);
    if (db == null) return;
    setState(() => _saving = true);
    try {
      await db.turnDao.updateTurn(
        turnId: widget.turnId,
        title: _titleCtrl.text.trim(),
        summary: _summaryCtrl.text.trim(),
        thematicTags: _editTags,
        playerStrategy: _editStrategy,
      );

      // Auto-lock non-empty fields the GM has explicitly set — pipeline won't overwrite them.
      // Empty fields stay unlocked so the pipeline can fill them in.
      final newGmFields = Set<String>.from(_gmFields);
      if (_summaryCtrl.text.trim().isNotEmpty) newGmFields.add('summary');
      if (_editTags.isNotEmpty) newGmFields.add('thematic_tags');
      if (_editStrategy.isNotEmpty) newGmFields.add('player_strategy');
      await db.turnDao.updateGmFields(widget.turnId, newGmFields);

      if (mounted) setState(() { _editMode = false; _gmFields = newGmFields; });
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  /// Show confirmation dialog then remove [field] from gm_fields — pipeline can re-fill it.
  Future<void> _unlockField(String field) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Déverrouiller ce champ ?'),
        content: Text('Le pipeline pourra à nouveau modifier "$field". Continuer ?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Déverrouiller'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    final db = ref.read(databaseProvider);
    if (db == null) return;
    final updated = Set<String>.from(_gmFields)..remove(field);
    await db.turnDao.updateGmFields(widget.turnId, updated);
    // _gmFields will be refreshed via the provider stream on next render
  }

  /// Scroll the view so the first text block containing [query] is centered.
  /// [keys] are tried in order — first non-null context with a match wins.
  void _scrollToFirstMatch(
      String query, List<({GlobalKey key, String text})> blocks) {
    if (query.isEmpty) return;
    final regex = fuzzyRegex(query);
    for (final block in blocks) {
      if (regex.hasMatch(block.text)) {
        final ctx = block.key.currentContext;
        if (ctx != null) {
          Scrollable.ensureVisible(
            ctx,
            alignment: 0.3, // place match ~30% from top of viewport
            duration: const Duration(milliseconds: 350),
            curve: Curves.easeOut,
          );
        }
        return;
      }
    }
  }

  void _toggleSearch() {
    setState(() {
      _searchVisible = !_searchVisible;
      if (_searchVisible) {
        // Focus the search field after the frame rebuilds
        WidgetsBinding.instance.addPostFrameCallback((_) => _searchFocus.requestFocus());
      } else {
        _searchCtrl.clear();
        _query = '';
        // Return focus to scaffold so Ctrl+F keeps working
        _scaffoldFocus.requestFocus();
      }
    });
  }

  /// Count all non-overlapping fuzzy matches of [query] in [text].
  int _countMatches(String text, String query) {
    if (query.isEmpty) return 0;
    return fuzzyRegex(query).allMatches(text).length;
  }

  @override
  Widget build(BuildContext context) {
    final dataAsync = ref.watch(turnDetailDataProvider(widget.turnId));

    return dataAsync.when(
      loading: () => const Scaffold(body: LoadingIndicator()),
      error: (e, _) => Scaffold(body: ErrorView(message: e.toString())),
      data: (data) {
        if (data == null) {
          return Scaffold(
            appBar: AppBar(),
            body: const Center(child: Text('Tour introuvable')),
          );
        }

        final t = data.turn;
        final typeColor = AppColors.turnTypeColors[t.turnType] ?? Colors.grey;

        // GM-locked fields — used to show lock badges on protected sections
        final gmFields = ref.watch(turnGmFieldsProvider(widget.turnId)).valueOrNull ?? {};

        // Build entity name → id map for auto-hyperlinking in turn text
        final turnEntities = ref.watch(turnEntitiesProvider(widget.turnId));
        final entityLinks = turnEntities.valueOrNull != null
            ? {for (final e in turnEntities.valueOrNull!)
                e.entity.canonicalName: e.entity.id}
            : <String, int>{};

        // Merge GM and PJ segments into single blocks each
        final gmText = data.segments
            .where((s) => s.source == 'gm')
            .map((s) => s.content)
            .join('\n\n');
        final pjText = data.segments
            .where((s) => s.source == 'pj')
            .map((s) => s.content)
            .join('\n\n');

        // Once data loads: scroll to first block containing the highlight query
        if (_pendingScrollToMatch) {
          _pendingScrollToMatch = false; // clear before addPostFrameCallback to avoid re-fire
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (!mounted) return;
            _scrollToFirstMatch(_query, [
              (key: _summaryKey, text: t.summary ?? ''),
              (key: _gmKey,      text: gmText),
              (key: _pjKey,      text: pjText),
            ]);
          });
        }

        // Total match count across all text blocks — shown in search bar
        final totalMatches = _query.isEmpty ? 0 :
            _countMatches(t.summary ?? '', _query) +
            _countMatches(gmText, _query) +
            _countMatches(pjText, _query);

        // Edit mode — full-screen form overlaid instead of the normal content
        if (_editMode) {
          return _buildEditScaffold(context, t);
        }

        // Ctrl+F intercepted at scaffold level — works when search bar is not focused
        return Focus(
          focusNode: _scaffoldFocus,
          autofocus: !_searchVisible, // don't steal focus from pre-filled search
          onKeyEvent: (_, event) {
            if (event is KeyDownEvent &&
                event.logicalKey == LogicalKeyboardKey.keyF &&
                HardwareKeyboard.instance.isControlPressed) {
              _toggleSearch();
              return KeyEventResult.handled;
            }
            return KeyEventResult.ignored;
          },
          child: Scaffold(
          appBar: AppBar(
            toolbarHeight: 44,
            leadingWidth: 88,
            title: _searchVisible
                ? Row(children: [
                    Expanded(
                      child: TextField(
                        controller: _searchCtrl,
                        focusNode: _searchFocus,
                        autofocus: true,
                        decoration: const InputDecoration(
                          hintText: 'Rechercher dans ce tour… (Ctrl+F)',
                          border: InputBorder.none,
                        ),
                        style: Theme.of(context).textTheme.bodyMedium,
                        onChanged: (v) => setState(() => _query = v),
                      ),
                    ),
                    // Match count badge
                    if (_query.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: Text(
                          '$totalMatches résultat${totalMatches != 1 ? 's' : ''}',
                          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                color: totalMatches > 0
                                    ? Theme.of(context).colorScheme.primary
                                    : Theme.of(context).colorScheme.onSurfaceVariant,
                              ),
                        ),
                      ),
                  ])
                : Text(t.title ?? 'Tour ${t.turnNumber}',
                    overflow: TextOverflow.ellipsis),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.canPop() ? context.pop() : context.go('/timeline'),
            ),
            actions: [
              // Favorite toggle — ref available from ConsumerState
              _TurnFavButton(turnId: widget.turnId, civId: t.civId),
              IconButton(
                icon: const Icon(Icons.edit_outlined),
                tooltip: 'Modifier ce tour',
                onPressed: () => _enterEditMode(t),
              ),
              IconButton(
                icon: Icon(_searchVisible ? Icons.close : Icons.search),
                tooltip: _searchVisible ? 'Fermer (Ctrl+F)' : 'Rechercher (Ctrl+F)',
                onPressed: _toggleSearch,
              ),
            ],
          ),
          body: NotesSideRail(
            attachment: NoteAttachment.turn,
            attachmentId: widget.turnId,
            child: SingleChildScrollView(
            controller: _scrollCtrl,
            padding: const EdgeInsets.fromLTRB(24, 20, 24, 40),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header badges
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    _Badge(
                      label: 'Tour ${t.turnNumber}',
                      color: typeColor,
                      bold: true,
                    ),
                    _Badge(
                      label: t.turnType.replaceAll('_', ' '),
                      color: typeColor,
                      outlined: true,
                    ),
                    _Badge(
                      label: data.civName,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                      surface: true,
                    ),
                    _Badge(
                      label: '${data.entityCount} entités',
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                      surface: true,
                    ),
                  ],
                ),

                // AI summary
                if (t.summary != null && t.summary!.isNotEmpty) ...[
                  const SizedBox(height: 20),
                  Row(children: [
                    const SectionHeader(title: 'Résumé'),
                    if (gmFields.contains('summary'))
                      _TurnGmLockBadge(
                        onTap: () => _unlockField('summary'),
                      ),
                  ]),
                  const SizedBox(height: 8),
                  Container(
                    key: _summaryKey,
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: Theme.of(context)
                          .colorScheme
                          .surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: _SearchableText(
                      text: t.summary!,
                      query: _query,
                      entityLinks: entityLinks,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontStyle: FontStyle.italic,
                            height: 1.6,
                          ),
                    ),
                  ),
                ],

                // GM block — single merged markdown block
                if (gmText.isNotEmpty) ...[
                  const SizedBox(height: 28),
                  const SectionHeader(title: 'Tour MJ'),
                  const SizedBox(height: 10),
                  Container(
                    key: _gmKey,
                    width: double.infinity,
                    padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
                    decoration: BoxDecoration(
                      border: Border(
                        left: BorderSide(
                          color: typeColor.withValues(alpha: 0.6),
                          width: 3,
                        ),
                      ),
                    ),
                    child: _SearchableText(
                      text: gmText,
                      query: _query,
                      entityLinks: entityLinks,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.7),
                    ),
                  ),
                ],

                // PJ block — single merged markdown block
                if (pjText.isNotEmpty) ...[
                  const SizedBox(height: 28),
                  const SectionHeader(title: 'Réponse Joueur'),
                  const SizedBox(height: 10),
                  Container(
                    key: _pjKey,
                    width: double.infinity,
                    padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
                    decoration: BoxDecoration(
                      border: Border(
                        left: BorderSide(
                          color: Colors.purple.withValues(alpha: 0.6),
                          width: 3,
                        ),
                      ),
                    ),
                    child: _SearchableText(
                      text: pjText,
                      query: _query,
                      entityLinks: entityLinks,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.7),
                    ),
                  ),
                ],

                // Fallback pre-migration (no source column)
                if (gmText.isEmpty && pjText.isEmpty && data.segments.isNotEmpty) ...[
                  const SizedBox(height: 28),
                  const SectionHeader(title: 'Contenu du tour'),
                  const SizedBox(height: 10),
                  _SearchableText(
                    text: data.segments.map((s) => s.content).join('\n\n'),
                    query: _query,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.7),
                  ),
                ],

                // Preanalysis — novelty + player strategy
                _PreanalysisSection(turn: t, gmFields: gmFields, onUnlock: _unlockField),

                // Analysis tags — thematic_tags, tech_era, fantasy_level
                _TurnTagsSection(turn: t, gmFields: gmFields, onUnlock: _unlockField),

                // Entities mentioned in this turn — fast travel
                _TurnEntitiesSection(turnId: widget.turnId),

                // Game date
                if (t.gameDateStart != null) ...[
                  const SizedBox(height: 20),
                  Text(
                    'Période : ${t.gameDateStart}'
                    '${t.gameDateEnd != null ? ' → ${t.gameDateEnd}' : ''}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context)
                              .colorScheme
                              .onSurfaceVariant,
                          fontStyle: FontStyle.italic,
                        ),
                  ),
                ],

              ],
            ),
          ),
          ), // NotesSideRail
        )); // closes Focus + Scaffold
      },
    );
  }

  // ---------------------------------------------------------------------------
  // Edit mode scaffold
  // ---------------------------------------------------------------------------

  Widget _buildEditScaffold(BuildContext context, TurnRow t) {
    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 44,
        title: Text('Modifier Tour ${t.turnNumber}'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          tooltip: 'Annuler',
          onPressed: _cancelEditMode,
        ),
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
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
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
            const SizedBox(height: 16),

            // Summary
            TextField(
              controller: _summaryCtrl,
              decoration: const InputDecoration(
                labelText: 'Résumé',
                border: OutlineInputBorder(),
                isDense: true,
                alignLabelWithHint: true,
              ),
              maxLines: 6,
              textCapitalization: TextCapitalization.sentences,
            ),
            const SizedBox(height: 20),

            // Thematic tags
            _buildTagsEdit(context),
            const SizedBox(height: 20),

            // Player strategy tags
            _buildStrategyEdit(context),
          ],
        ),
      ),
    );
  }

  // Fixed strategy tag vocabulary (mirrors _strategyTagColors in _PreanalysisSection)
  static const _strategyVocab = [
    'expansion', 'diplomatie', 'defense', 'economie',
    'culture', 'exploration', 'militaire', 'religieux',
  ];

  Widget _buildTagsEdit(BuildContext context) {
    final tagAsync = ref.watch(turnTagsProvider);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Tags thématiques', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: 8),
        if (_editTags.isNotEmpty)
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: _editTags.map((tag) => InputChip(
              label: Text(tag, style: const TextStyle(fontSize: 12)),
              onDeleted: () => setState(() => _editTags.remove(tag)),
            )).toList(),
          ),
        const SizedBox(height: 8),
        tagAsync.when(
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
          data: (allTags) {
            final available = allTags.where((t) => !_editTags.contains(t)).toList();
            return DropdownButton<String>(
              hint: const Text('+ Ajouter un tag'),
              value: null,
              items: available
                  .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                  .toList(),
              onChanged: (tag) {
                if (tag != null) setState(() => _editTags.add(tag));
              },
            );
          },
        ),
      ],
    );
  }

  Widget _buildStrategyEdit(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Stratégie joueur', style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: 8),
        if (_editStrategy.isNotEmpty)
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: _editStrategy.map((tag) => InputChip(
              label: Text(tag, style: const TextStyle(fontSize: 12)),
              onDeleted: () => setState(() => _editStrategy.remove(tag)),
            )).toList(),
          ),
        const SizedBox(height: 8),
        DropdownButton<String>(
          hint: const Text('+ Ajouter une stratégie'),
          value: null,
          items: _strategyVocab
              .where((t) => !_editStrategy.contains(t))
              .map((t) => DropdownMenuItem(value: t, child: Text(t)))
              .toList(),
          onChanged: (tag) {
            if (tag != null) setState(() => _editStrategy.add(tag));
          },
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Preanalysis — novelty detection + player strategy
// ---------------------------------------------------------------------------

class _PreanalysisSection extends StatelessWidget {
  final TurnRow turn;
  final Set<String> gmFields;
  final void Function(String field) onUnlock;

  const _PreanalysisSection({
    required this.turn,
    this.gmFields = const {},
    required this.onUnlock,
  });

  List<String> _parseTags(String? raw) {
    if (raw == null || raw.isEmpty) return [];
    return raw
        .replaceAll('[', '')
        .replaceAll(']', '')
        .split(',')
        .map((s) => s.trim().replaceAll('"', '').replaceAll("'", ''))
        .where((s) => s.isNotEmpty)
        .toList();
  }

  static const _strategyTagColors = <String, Color>{
    'expansion': Colors.green,
    'diplomatie': Colors.blue,
    'defense': Colors.orange,
    'economie': Colors.amber,
    'culture': Colors.purple,
    'exploration': Colors.teal,
    'militaire': Colors.red,
    'religieux': Colors.indigo,
  };

  @override
  Widget build(BuildContext context) {
    final hasNovelty = turn.noveltySummary != null && turn.noveltySummary!.isNotEmpty;
    final hasStrategy = turn.playerStrategy != null && turn.playerStrategy!.isNotEmpty;

    if (!hasNovelty && !hasStrategy) return const SizedBox.shrink();

    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 24),
        const SectionHeader(title: 'Preanalyse'),
        const SizedBox(height: 10),

        // Novelty summary
        if (hasNovelty)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            margin: const EdgeInsets.only(bottom: 10),
            decoration: BoxDecoration(
              color: Colors.green.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.green.withValues(alpha: 0.25)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.new_releases_outlined, size: 16,
                    color: Colors.green.shade300),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    turn.noveltySummary!,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: cs.onSurface,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),

        // Player strategy
        if (hasStrategy)
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.blue.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.blue.withValues(alpha: 0.25)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.psychology_outlined, size: 16,
                        color: Colors.blue.shade300),
                    const SizedBox(width: 8),
                    Text('Strategie joueur',
                        style: theme.textTheme.labelMedium?.copyWith(
                          color: Colors.blue.shade300,
                          fontWeight: FontWeight.w600,
                        )),
                    if (gmFields.contains('player_strategy'))
                      _TurnGmLockBadge(onTap: () => onUnlock('player_strategy')),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  turn.playerStrategy!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: cs.onSurface,
                    height: 1.5,
                  ),
                ),
                // Strategy tags
                if (_parseTags(turn.strategyTags).isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: _parseTags(turn.strategyTags).map((tag) {
                      final color = _strategyTagColors[tag] ?? cs.primary;
                      return _TagChip(label: tag, color: color);
                    }).toList(),
                  ),
                ],
              ],
            ),
          ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Tags de l'analyse — thematic_tags, tech_era, fantasy_level
// ---------------------------------------------------------------------------

class _TurnTagsSection extends StatelessWidget {
  final TurnRow turn;
  final Set<String> gmFields;
  final void Function(String field) onUnlock;

  const _TurnTagsSection({
    required this.turn,
    this.gmFields = const {},
    required this.onUnlock,
  });

  /// Parse a JSON-like list stored as text: '["tag1","tag2"]' → ['tag1','tag2']
  List<String> _parseTags(String? raw) {
    if (raw == null || raw.isEmpty) return [];
    // Strip brackets and split on commas, clean up quotes/whitespace
    return raw
        .replaceAll('[', '')
        .replaceAll(']', '')
        .split(',')
        .map((s) => s.trim().replaceAll('"', '').replaceAll("'", ''))
        .where((s) => s.isNotEmpty)
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final thematicTags = _parseTags(turn.thematicTags);
    final techEra = turn.techEra;
    final fantasyLevel = turn.fantasyLevel;

    if (thematicTags.isEmpty && techEra == null && fantasyLevel == null) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 20),
        Row(children: [
          const SectionHeader(title: 'Analyse'),
          if (gmFields.contains('thematic_tags'))
            _TurnGmLockBadge(onTap: () => onUnlock('thematic_tags')),
        ]),
        const SizedBox(height: 8),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            if (techEra != null)
              _TagChip(label: techEra, icon: Icons.science_outlined,
                  color: Colors.teal),
            if (fantasyLevel != null)
              _TagChip(label: fantasyLevel, icon: Icons.auto_awesome,
                  color: Colors.purple),
            ...thematicTags.map((tag) => _TagChip(label: tag,
                color: Theme.of(context).colorScheme.primary)),
          ],
        ),
      ],
    );
  }
}

class _TagChip extends StatelessWidget {
  final String label;
  final Color color;
  final IconData? icon;

  const _TagChip({required this.label, required this.color, this.icon});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 12, color: color),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w500,
                ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Entités du tour — liste cliquable pour fast travel
// ---------------------------------------------------------------------------

class _TurnEntitiesSection extends ConsumerWidget {
  final int turnId;

  const _TurnEntitiesSection({required this.turnId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final entitiesAsync = ref.watch(turnEntitiesProvider(turnId));

    return entitiesAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (entities) {
        if (entities.isEmpty) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 20),
            const SectionHeader(title: 'Entités'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: entities.map((e) {
                final color = AppColors.entityColor(e.entity.entityType);
                return InkWell(
                  onTap: () => context.push('/entities/${e.entity.id}'),
                  borderRadius: BorderRadius.circular(12),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(12),
                      border:
                          Border.all(color: color.withValues(alpha: 0.35)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        EntityTypeIcon(
                            entityType: e.entity.entityType, size: 12),
                        const SizedBox(width: 4),
                        Text(
                          e.entity.canonicalName,
                          style: Theme.of(context)
                              .textTheme
                              .labelSmall
                              ?.copyWith(
                                color: color,
                                fontWeight: FontWeight.w500,
                              ),
                        ),
                      ],
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
        );
      },
    );
  }
}

// fuzzyRegex() moved to lore_linker.dart — imported as fuzzyRegex()

// ---------------------------------------------------------------------------
// MD-aware text — renders Markdown when no search, highlights when searching
// ---------------------------------------------------------------------------

class _SearchableText extends StatelessWidget {
  final String text;
  final String query;
  final TextStyle? style;
  // If true, use a dialogue-style markdown sheet (colored bullets for choices)
  final bool isChoice;
  // Map of entity canonical name → entity ID for auto-hyperlinking in text
  final Map<String, int> entityLinks;

  const _SearchableText({
    required this.text,
    required this.query,
    this.style,
    this.isChoice = false,
    this.entityLinks = const {},
  });

  /// Build a LoreLink map from the entity name->id map and delegate to injectLoreLinks().
  String _injectEntityLinks(String text) {
    if (entityLinks.isEmpty) return text;

    // Convert entityLinks (name->id) to a LoreLink map sorted by length desc
    final loreLinkMap = Map.fromEntries(
      entityLinks.entries
          .toList()
        ..sort((a, b) => b.key.length.compareTo(a.key.length)),
    ).map((name, id) => MapEntry(
          name,
          LoreLink(id: id, type: LoreLinkType.entity, route: '/entities/$id'),
        ));

    return injectLoreLinks(text, loreLinkMap);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final base = style ?? theme.textTheme.bodyMedium!;

    // When searching: strip MD and highlight all fuzzy matches in plain text
    if (query.isNotEmpty) {
      final plain = text
          .replaceAll(RegExp(r'\*\*(.+?)\*\*'), r'$1')
          .replaceAll(RegExp(r'\*(.+?)\*'), r'$1')
          .replaceAll(RegExp(r'#{1,6}\s+'), '')
          .replaceAll(RegExp(r'!\[.*?\]\(.*?\)'), '');
      final regex = fuzzyRegex(query);
      final spans = <TextSpan>[];
      int start = 0;
      for (final match in regex.allMatches(plain)) {
        if (match.start > start) {
          spans.add(TextSpan(text: plain.substring(start, match.start)));
        }
        spans.add(TextSpan(
          text: plain.substring(match.start, match.end),
          style: const TextStyle(
            backgroundColor: Color(0xFFFFE066),
            color: Colors.black,
            fontWeight: FontWeight.w600,
          ),
        ));
        start = match.end;
      }
      if (start < plain.length) spans.add(TextSpan(text: plain.substring(start)));
      return SelectableText.rich(TextSpan(children: spans, style: base));
    }

    // No search: full Markdown rendering with entity hyperlinks
    final sheet = _buildStyleSheet(context, base);
    final processed = _injectEntityLinks(text);
    return MarkdownBody(
      data: processed,
      selectable: true,
      styleSheet: sheet,
      onTapLink: (_, href, __) {
        if (href == null) return;
        // Handle lore:// links (from injectLoreLinks) — extract the route
        if (href.startsWith('lore://')) {
          final uri = Uri.tryParse(href);
          if (uri == null) return;
          final id = int.tryParse(uri.pathSegments.lastOrNull ?? '');
          if (id == null) return;
          // Map lore type to route prefix
          final route = switch (uri.host) {
            'entity' => '/entities/$id',
            'civ' => '/civs/$id',
            'subject' => '/subjects/$id',
            'turn' => '/turns/$id',
            _ => null,
          };
          if (route != null) context.push(route);
        } else if (href.startsWith('/')) {
          context.push(href);
        }
      },
    );
  }

  MarkdownStyleSheet _buildStyleSheet(BuildContext context, TextStyle base) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    // Choice segments get orange/amber bullets; PJ gets purple; default neutral
    final bulletColor = isChoice
        ? Colors.orange.shade300
        : cs.onSurfaceVariant;

    return MarkdownStyleSheet(
      p: base,
      strong: base.copyWith(fontWeight: FontWeight.w700, color: cs.onSurface),
      em: base.copyWith(fontStyle: FontStyle.italic),
      h1: base.copyWith(fontSize: (base.fontSize ?? 14) + 4, fontWeight: FontWeight.bold),
      h2: base.copyWith(fontSize: (base.fontSize ?? 14) + 2, fontWeight: FontWeight.bold,
          color: cs.primary),
      h3: base.copyWith(fontSize: (base.fontSize ?? 14) + 1, fontWeight: FontWeight.w600,
          color: cs.primary),
      listBullet: base.copyWith(color: bulletColor),
      blockquote: base.copyWith(color: cs.onSurfaceVariant, fontStyle: FontStyle.italic),
      blockquoteDecoration: BoxDecoration(
        border: Border(left: BorderSide(color: cs.outlineVariant, width: 3)),
      ),
      blockquotePadding: const EdgeInsets.only(left: 12),
      horizontalRuleDecoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: cs.outlineVariant)),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Small header badge
// ---------------------------------------------------------------------------

class _Badge extends StatelessWidget {
  final String label;
  final Color color;
  final bool bold;
  final bool outlined;
  final bool surface;

  const _Badge({
    required this.label,
    required this.color,
    this.bold = false,
    this.outlined = false,
    this.surface = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: surface
            ? Theme.of(context).colorScheme.surfaceContainerHighest
            : color.withValues(alpha: outlined ? 0.08 : 0.15),
        borderRadius: BorderRadius.circular(8),
        border: outlined ? Border.all(color: color.withValues(alpha: 0.4)) : null,
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: color,
              fontWeight: bold ? FontWeight.bold : FontWeight.normal,
            ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// GM lock badge — amber lock icon, tappable to unlock
// ---------------------------------------------------------------------------

/// Small amber lock icon shown next to a GM-protected field label.
/// Tapping opens a confirmation dialog to unlock the field.
class _TurnGmLockBadge extends StatelessWidget {
  final VoidCallback onTap;

  const _TurnGmLockBadge({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 6),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(4),
        child: const Padding(
          padding: EdgeInsets.all(2),
          child: Icon(Icons.lock, size: 14, color: Colors.amber),
        ),
      ),
    );
  }
}

/// Favorite toggle button for a turn — extracted to keep build() clean.
class _TurnFavButton extends ConsumerWidget {
  final int turnId;
  final int civId;

  const _TurnFavButton({required this.turnId, required this.civId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isFav = ref.watch(favoritesProvider).contains('turn_$turnId');
    return IconButton(
      icon: Icon(
        isFav ? Icons.star : Icons.star_border,
        color: isFav ? Colors.amber : null,
      ),
      tooltip: isFav ? 'Retirer des favoris' : 'Ajouter aux favoris',
      onPressed: () =>
          ref.read(favoritesProvider.notifier).toggle('turn', turnId, civId),
    );
  }
}
