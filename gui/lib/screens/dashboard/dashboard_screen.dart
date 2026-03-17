import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/civilization_provider.dart';
import '../../providers/database_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/empty_state.dart';
import 'widgets/civ_summary_card.dart';
import 'widgets/pipeline_status_card.dart';
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dbPath = ref.watch(dbPathProvider);

    if (dbPath == null) {
      return EmptyState(
        icon: Icons.storage,
        message: 'No database configured',
        subtitle: 'Go to Settings to select your aurelm.db file.',
        action: FilledButton.icon(
          onPressed: () => context.go('/settings'),
          icon: const Icon(Icons.settings),
          label: const Text('Open Settings'),
        ),
      );
    }

    final civs = ref.watch(civListProvider);

    return SelectionArea(
      child: Scaffold(
        appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.account_tree_outlined),
            tooltip: 'Résoudre alias de civilisations',
            onPressed: () => context.go('/civs/alias-resolver'),
          ),
        ],
      ),
      body: civs.when(
        loading: () => const LoadingIndicator(message: 'Loading civilizations...'),
        error: (e, _) => ErrorView(message: e.toString()),
        data: (civList) {
          if (civList.isEmpty) {
            return const EmptyState(
              icon: Icons.public,
              message: 'No civilizations yet',
              subtitle: 'Run the pipeline to import game data.',
            );
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const PipelineStatusCard(),
                const SizedBox(height: 24),
                Text(
                  'Civilizations',
                  style: Theme.of(context)
                      .textTheme
                      .titleLarge
                      ?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final crossAxisCount =
                        constraints.maxWidth > 900 ? 3 : (constraints.maxWidth > 600 ? 2 : 1);
                    return GridView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: crossAxisCount,
                        crossAxisSpacing: 16,
                        mainAxisSpacing: 16,
                        childAspectRatio: 1.8,
                      ),
                      itemCount: civList.length,
                      itemBuilder: (context, index) {
                        return CivSummaryCard(civWithStats: civList[index]);
                      },
                    );
                  },
                ),
              ],
            ),
          );
        },
      ),
      ),
    );
  }
}
