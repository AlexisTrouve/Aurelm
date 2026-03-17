import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/civilization_provider.dart';
import '../../providers/entity_provider.dart';
import '../../providers/turn_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/stat_card.dart';
import '../../widgets/common/section_header.dart';
import '../../screens/entities/widgets/notes_menu_button.dart';
import 'widgets/entity_breakdown_chart.dart';
import 'widgets/top_entities_list.dart';
import 'widgets/recent_turns_list.dart';
import 'widgets/civ_subjects_frame.dart';
import 'widgets/civ_sessions_frame.dart';
import 'widgets/civ_relations_frame.dart';
import '../../providers/civ_alias_provider.dart';

class CivDetailScreen extends ConsumerWidget {
  final int civId;

  const CivDetailScreen({super.key, required this.civId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final civAsync = ref.watch(civDetailProvider(civId));

    return civAsync.when(
      loading: () => const Scaffold(body: LoadingIndicator()),
      error: (e, _) => Scaffold(body: ErrorView(message: e.toString())),
      data: (civWithStats) {
        if (civWithStats == null) {
          return Scaffold(
            appBar: AppBar(),
            body: const Center(child: Text('Civilization not found')),
          );
        }

        final civ = civWithStats.civ;
        final briefAsync = ref.watch(civBriefProvider(civId));
        return Scaffold(
          appBar: AppBar(
            title: Text(civ.name),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.go('/'),
            ),
          ),
          body: NotesSideRail(
            attachment: NoteAttachment.civ,
            attachmentId: civId,
            child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Civ brief — recent turn summaries
                briefAsync.when(
                  loading: () => const SizedBox.shrink(),
                  error: (_, __) => const SizedBox.shrink(),
                  data: (turns) {
                    if (turns.isEmpty) return const SizedBox.shrink();
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 24),
                      child: Theme(
                        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                        child: ExpansionTile(
                          tilePadding: EdgeInsets.zero,
                          initiallyExpanded: true,
                          title: Text('Historique récent',
                              style: Theme.of(context).textTheme.titleSmall),
                          children: turns.map((turn) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Tour ${turn.turnNumber}',
                                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                                        color: Theme.of(context).colorScheme.primary,
                                        fontWeight: FontWeight.w600,
                                      ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  turn.detailedSummary!,
                                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                                        height: 1.5,
                                      ),
                                ),
                              ],
                            ),
                          )).toList(),
                        ),
                      ),
                    );
                  },
                ),

                // Header info
                if (civ.playerName != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Text(
                      'Player: ${civ.playerName}',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: Theme.of(context)
                                .colorScheme
                                .onSurfaceVariant,
                          ),
                    ),
                  ),

                // Stats row
                Row(
                  children: [
                    Expanded(
                      child: StatCard(
                        icon: Icons.history,
                        label: 'Turns',
                        value: '${civWithStats.turnCount}',
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: StatCard(
                        icon: Icons.category,
                        label: 'Entities',
                        value: '${civWithStats.entityCount}',
                        color: Theme.of(context).colorScheme.tertiary,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 24),

                // Entity breakdown chart
                const SectionHeader(title: 'Entity Breakdown'),
                SizedBox(
                  height: 250,
                  child: EntityBreakdownChart(civId: civId),
                ),

                const SizedBox(height: 24),

                // Top entities — "View all" pré-filtre par civ
                SectionHeader(
                  title: 'Top Entities',
                  trailing: TextButton(
                    onPressed: () {
                      ref.read(entityFilterProvider.notifier).setCivId(civId);
                      context.go('/entities');
                    },
                    child: const Text('View all'),
                  ),
                ),
                TopEntitiesList(civId: civId),

                const SizedBox(height: 24),

                // Sujets (5 récents + stats + lien filtré)
                CivSubjectsFrame(civId: civId),

                const SizedBox(height: 24),

                // Sessions chat taggées avec cette civ
                CivSessionsFrame(civName: civ.name),

                // Civ aliases — noms alternatifs gérés par le GM
                _CivAliasesSection(civId: civId),


                // Inter-civ relations (populated by pipeline profiler)
                CivRelationsFrame(civId: civId),

                const SizedBox(height: 24),

                // Recent turns — tiles cliquables + "View all" pré-filtré par civ
                SectionHeader(
                  title: 'Recent Turns',
                  trailing: TextButton(
                    onPressed: () {
                      ref.read(timelineFilterProvider.notifier).setCivId(civId);
                      context.go('/timeline');
                    },
                    child: const Text('View all'),
                  ),
                ),
                RecentTurnsList(civId: civId),
              ],
            ),
          ),
          ),
        );
      },
    );
  }
}

/// Shows aliases for a civ with add + delete. Inline, no separate screen.
class _CivAliasesSection extends ConsumerStatefulWidget {
  final int civId;
  const _CivAliasesSection({required this.civId});

  @override
  ConsumerState<_CivAliasesSection> createState() => _CivAliasesSectionState();
}

class _CivAliasesSectionState extends ConsumerState<_CivAliasesSection> {
  final _controller = TextEditingController();
  bool _adding = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _add() async {
    final name = _controller.text.trim();
    if (name.isEmpty) return;
    final repo = ref.read(civAliasRepositoryProvider);
    if (repo == null) return;
    await repo.addAlias(widget.civId, name);
    _controller.clear();
    setState(() => _adding = false);
    ref.invalidate(civAliasesProvider(widget.civId));
  }

  Future<void> _delete(int aliasId) async {
    final repo = ref.read(civAliasRepositoryProvider);
    if (repo == null) return;
    await repo.deleteAlias(aliasId);
    ref.invalidate(civAliasesProvider(widget.civId));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final aliasesAsync = ref.watch(civAliasesProvider(widget.civId));

    final aliases = aliasesAsync.valueOrNull ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 24),
        Row(
          children: [
            Expanded(
              child: Text('Aliases',
                  style: theme.textTheme.titleSmall
                      ?.copyWith(fontWeight: FontWeight.w600)),
            ),
            IconButton(
              icon: const Icon(Icons.add, size: 18),
              tooltip: 'Ajouter un alias',
              onPressed: () => setState(() => _adding = !_adding),
            ),
          ],
        ),
        if (_adding) ...[
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  autofocus: true,
                  decoration: const InputDecoration(
                    hintText: 'Nom alternatif...',
                    isDense: true,
                    border: OutlineInputBorder(),
                    contentPadding:
                        EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  ),
                  onSubmitted: (_) => _add(),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton(onPressed: _add, child: const Text('Ajouter')),
              const SizedBox(width: 4),
              TextButton(
                onPressed: () => setState(() { _adding = false; _controller.clear(); }),
                child: const Text('Annuler'),
              ),
            ],
          ),
        ],
        if (aliases.isEmpty && !_adding)
          Padding(
            padding: const EdgeInsets.only(top: 4, bottom: 4),
            child: Text('Aucun alias',
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: cs.onSurfaceVariant)),
          )
        else ...[
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: aliases.map((a) => Chip(
                  label: Text(a.aliasName,
                      style: theme.textTheme.labelSmall),
                  deleteIcon: const Icon(Icons.close, size: 14),
                  onDeleted: () => _delete(a.id),
                  visualDensity: VisualDensity.compact,
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                )).toList(),
          ),
        ],
      ],
    );
  }
}
