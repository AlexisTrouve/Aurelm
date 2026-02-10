import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/turn_provider.dart';
import '../../providers/database_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/empty_state.dart';
import 'widgets/timeline_turn_card.dart';
import 'widgets/timeline_filter_bar.dart';

class TimelineScreen extends ConsumerWidget {
  const TimelineScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dbPath = ref.watch(dbPathProvider);
    if (dbPath == null) {
      return const Scaffold(
        body: EmptyState(
          icon: Icons.storage,
          message: 'No database configured',
        ),
      );
    }

    final timeline = ref.watch(timelineProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Timeline')),
      body: Column(
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(24, 16, 24, 8),
            child: TimelineFilterBar(),
          ),
          const Divider(),
          Expanded(
            child: timeline.when(
              loading: () => const LoadingIndicator(),
              error: (e, _) => ErrorView(message: e.toString()),
              data: (turns) {
                if (turns.isEmpty) {
                  return const EmptyState(
                    icon: Icons.timeline,
                    message: 'No turns found',
                    subtitle: 'Try adjusting your filters',
                  );
                }
                return ListView.builder(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 24, vertical: 8),
                  itemCount: turns.length,
                  itemBuilder: (context, index) {
                    return TimelineTurnCard(turn: turns[index]);
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
