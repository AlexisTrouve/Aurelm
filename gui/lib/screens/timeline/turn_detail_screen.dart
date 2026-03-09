import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../data/database.dart';
import '../../providers/turn_provider.dart';
import '../../providers/entity_provider.dart';
import '../../widgets/common/entity_type_icon.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/section_header.dart';

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
  bool _searchVisible = false;
  final TextEditingController _searchCtrl = TextEditingController();
  String _query = '';

  @override
  void initState() {
    super.initState();
    // If opened via a naming history link, pre-fill the search with the entity name
    if (widget.highlightText != null) {
      _searchVisible = true;
      _query = widget.highlightText!;
      _searchCtrl.text = widget.highlightText!;
    }
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  void _toggleSearch() {
    setState(() {
      _searchVisible = !_searchVisible;
      if (!_searchVisible) {
        _searchCtrl.clear();
        _query = '';
      }
    });
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

        return Scaffold(
          appBar: AppBar(
            title: _searchVisible
                ? TextField(
                    controller: _searchCtrl,
                    autofocus: true,
                    decoration: const InputDecoration(
                      hintText: 'Rechercher dans ce tour…',
                      border: InputBorder.none,
                    ),
                    style: Theme.of(context).textTheme.bodyMedium,
                    onChanged: (v) => setState(() => _query = v),
                  )
                : Text(t.title ?? 'Tour ${t.turnNumber}',
                    overflow: TextOverflow.ellipsis),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.canPop() ? context.pop() : context.go('/timeline'),
            ),
            actions: [
              IconButton(
                icon: Icon(_searchVisible ? Icons.close : Icons.search),
                tooltip: _searchVisible ? 'Fermer' : 'Rechercher',
                onPressed: _toggleSearch,
              ),
            ],
          ),
          body: SingleChildScrollView(
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
                  const SectionHeader(title: 'Résumé'),
                  const SizedBox(height: 8),
                  Container(
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

                // Analysis tags — thematic_tags, tech_era, fantasy_level
                _TurnTagsSection(turn: t),

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
        );
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Tags de l'analyse — thematic_tags, tech_era, fantasy_level
// ---------------------------------------------------------------------------

class _TurnTagsSection extends StatelessWidget {
  final TurnRow turn;

  const _TurnTagsSection({required this.turn});

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
        const SectionHeader(title: 'Analyse'),
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

  /// Replace entity names in text with Markdown links [name](/entities/id).
  /// Names sorted by length desc so "Argile Vivante" matches before "Argile".
  /// Skips names shorter than 4 chars to avoid noise.
  /// Avoids replacing text already inside a Markdown link [...](...)
  String _injectEntityLinks(String text) {
    if (entityLinks.isEmpty) return text;

    // Sort by name length descending — longest match wins
    final sorted = entityLinks.entries
        .where((e) => e.key.length >= 4)
        .toList()
      ..sort((a, b) => b.key.length.compareTo(a.key.length));

    String result = text;
    for (final entry in sorted) {
      final escaped = RegExp.escape(entry.key);
      // Match the name case-insensitively, not already inside [...](...)
      final regex = RegExp(escaped, caseSensitive: false);
      // Replace only occurrences not already inside a Markdown link
      result = result.replaceAllMapped(regex, (match) {
        final start = match.start;
        // Check if preceded by '[' (already a link label) — skip
        if (start > 0 && result[start - 1] == '[') return match.group(0)!;
        return '[${match.group(0)}](/entities/${entry.value})';
      });
    }
    return result;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final base = style ?? theme.textTheme.bodyMedium!;

    // When searching: strip MD and highlight matches in plain text
    if (query.isNotEmpty) {
      final plain = text
          .replaceAll(RegExp(r'\*\*(.+?)\*\*'), r'$1')
          .replaceAll(RegExp(r'\*(.+?)\*'), r'$1')
          .replaceAll(RegExp(r'#{1,6}\s+'), '')
          .replaceAll(RegExp(r'!\[.*?\]\(.*?\)'), '');
      final lower = plain.toLowerCase();
      final lowerQ = query.toLowerCase();
      final spans = <TextSpan>[];
      int start = 0;
      while (true) {
        final idx = lower.indexOf(lowerQ, start);
        if (idx == -1) break;
        if (idx > start) spans.add(TextSpan(text: plain.substring(start, idx)));
        spans.add(TextSpan(
          text: plain.substring(idx, idx + query.length),
          style: const TextStyle(
            backgroundColor: Color(0xFFFFE066),
            color: Colors.black,
            fontWeight: FontWeight.w600,
          ),
        ));
        start = idx + query.length;
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
        if (href != null && href.startsWith('/entities/')) {
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
