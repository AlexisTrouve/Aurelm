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
