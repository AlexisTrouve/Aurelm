import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../data/repositories/civ_relations_repository.dart';
import '../../providers/civilization_provider.dart';
import '../../providers/database_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/section_header.dart';

/// Detail screen for a single inter-civ relation.
///
/// Shows the LLM profile (opinion, description, treaties) at the top,
/// then every civ_mention turn-by-turn with context + link to the turn.
class CivRelationDetailScreen extends ConsumerWidget {
  /// The relation row id (from civ_relations.id).
  final int relationId;

  const CivRelationDetailScreen({super.key, required this.relationId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final relationsAsync = ref.watch(allCivRelationsProvider);

    return relationsAsync.when(
      loading: () => const Scaffold(body: LoadingIndicator()),
      error: (e, _) => Scaffold(
        appBar: AppBar(),
        body: Center(child: Text('Erreur: $e')),
      ),
      data: (relations) {
        final relation =
            relations.where((r) => r.id == relationId).firstOrNull;
        if (relation == null) {
          return Scaffold(
            appBar: AppBar(),
            body: const Center(child: Text('Relation introuvable')),
          );
        }
        return _RelationDetailBody(relation: relation);
      },
    );
  }
}

class _RelationDetailBody extends ConsumerStatefulWidget {
  final CivRelation relation;

  const _RelationDetailBody({required this.relation});

  @override
  ConsumerState<_RelationDetailBody> createState() =>
      _RelationDetailBodyState();
}

class _RelationDetailBodyState
    extends ConsumerState<_RelationDetailBody> {
  List<CivRelationMention>? _mentions;
  bool _loadingMentions = true;

  static const _opinionColors = <String, Color>{
    'allied':     Color(0xFF4CAF50),
    'friendly':   Color(0xFF8BC34A),
    'neutral':    Color(0xFF9E9E9E),
    'suspicious': Color(0xFFFF9800),
    'hostile':    Color(0xFFF44336),
    'unknown':    Color(0xFF757575),
  };

  static const _opinionLabels = <String, String>{
    'allied':     'Allié',
    'friendly':   'Favorable',
    'neutral':    'Neutre',
    'suspicious': 'Méfiant',
    'hostile':    'Hostile',
    'unknown':    'Inconnu',
  };

  @override
  void initState() {
    super.initState();
    _loadMentions();
  }

  Future<void> _loadMentions() async {
    final db = ref.read(databaseProvider);
    if (db == null) {
      setState(() => _loadingMentions = false);
      return;
    }
    final mentions = await CivRelationsRepository(db).loadMentions(
      widget.relation.sourceCivId,
      widget.relation.targetCivId,
    );
    if (mounted) setState(() { _mentions = mentions; _loadingMentions = false; });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final r = widget.relation;
    final color = _opinionColors[r.opinion] ?? _opinionColors['unknown']!;
    final label = _opinionLabels[r.opinion] ?? r.opinion;

    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 44,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () =>
              context.canPop() ? context.pop() : context.go('/civs/relations'),
        ),
        title: Text('${r.sourceCivName} → ${r.targetCivName}',
            overflow: TextOverflow.ellipsis),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Opinion chip + header
            Row(
              children: [
                InkWell(
                  onTap: () => context.push('/civs/${r.sourceCivId}'),
                  child: Text(r.sourceCivName,
                      style: theme.textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: cs.primary,
                      )),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  child: Icon(Icons.arrow_forward, color: cs.onSurfaceVariant),
                ),
                InkWell(
                  onTap: () => context.push('/civs/${r.targetCivId}'),
                  child: Text(r.targetCivName,
                      style: theme.textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: cs.primary,
                      )),
                ),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: color.withValues(alpha: 0.4)),
                  ),
                  child: Text(label,
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: color,
                        fontWeight: FontWeight.w700,
                      )),
                ),
              ],
            ),

            // LLM description
            if (r.description != null && r.description!.isNotEmpty) ...[
              const SizedBox(height: 20),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: color.withValues(alpha: 0.2)),
                ),
                child: Text(r.description!,
                    style: theme.textTheme.bodyMedium
                        ?.copyWith(height: 1.7)),
              ),
            ],

            // Treaties
            if (r.treaties.isNotEmpty) ...[
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: r.treaties
                    .map((t) => Chip(
                          avatar: const Icon(Icons.handshake_outlined,
                              size: 14),
                          label: Text(t),
                          visualDensity: VisualDensity.compact,
                        ))
                    .toList(),
              ),
            ],

            // Mention count summary
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: SectionHeader(
                      title:
                          'Mentions par tour (${r.mentionCount})'),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Turn-by-turn mentions
            if (_loadingMentions)
              const Center(child: CircularProgressIndicator())
            else if (_mentions == null || _mentions!.isEmpty)
              Text('Aucune mention enregistrée.',
                  style: theme.textTheme.bodySmall
                      ?.copyWith(color: cs.onSurfaceVariant))
            else
              ...(_mentions!.map((m) => _MentionCard(mention: m))),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Single mention card — context + link to turn
// ---------------------------------------------------------------------------

class _MentionCard extends StatelessWidget {
  final CivRelationMention mention;

  const _MentionCard({required this.mention});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: cs.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: cs.outlineVariant),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        // Open turn detail with context highlighted
        onTap: () => context.push(
          '/turns/${mention.turnId}',
          extra: <String, dynamic>{'highlight': mention.context},
        ),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Turn number badge
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: cs.primaryContainer,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'Tour ${mention.turnNumber}',
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: cs.onPrimaryContainer,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              // Context text
              Expanded(
                child: Text(
                  mention.context.isNotEmpty
                      ? mention.context
                      : '(pas de contexte)',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: mention.context.isEmpty
                        ? cs.onSurfaceVariant
                        : cs.onSurface,
                    height: 1.6,
                    fontStyle: mention.context.isEmpty
                        ? FontStyle.italic
                        : null,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Icon(Icons.open_in_new,
                  size: 14, color: cs.onSurfaceVariant),
            ],
          ),
        ),
      ),
    );
  }
}
