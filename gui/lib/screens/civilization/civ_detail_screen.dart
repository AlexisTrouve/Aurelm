import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/civilization_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/stat_card.dart';
import '../../widgets/common/section_header.dart';
import 'widgets/entity_breakdown_chart.dart';
import 'widgets/top_entities_list.dart';
import 'widgets/recent_turns_list.dart';

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
        return Scaffold(
          appBar: AppBar(
            title: Text(civ.name),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.go('/'),
            ),
          ),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
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

                // Top entities
                SectionHeader(
                  title: 'Top Entities',
                  trailing: TextButton(
                    onPressed: () => context.go('/entities'),
                    child: const Text('View all'),
                  ),
                ),
                TopEntitiesList(civId: civId),

                const SizedBox(height: 24),

                // Recent turns
                SectionHeader(
                  title: 'Recent Turns',
                  trailing: TextButton(
                    onPressed: () => context.go('/timeline'),
                    child: const Text('View all'),
                  ),
                ),
                RecentTurnsList(civId: civId),
              ],
            ),
          ),
        );
      },
    );
  }
}
