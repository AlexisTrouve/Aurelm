import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/subject_provider.dart';
import '../../providers/database_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/empty_state.dart';
import 'widgets/subject_filter_bar.dart';
import 'widgets/subject_list_tile.dart';

/// Main subjects screen — lists all MJ↔PJ subjects with filter controls.
class SubjectBrowserScreen extends ConsumerWidget {
  const SubjectBrowserScreen({super.key});

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

    final subjectsAsync = ref.watch(subjectListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Sujets'),
        actions: [
          // Quick stats in app bar
          subjectsAsync.when(
            data: (subjects) {
              final open = subjects.where((s) => s.subject.status == 'open').length;
              final resolved =
                  subjects.where((s) => s.subject.status == 'resolved').length;
              return Padding(
                padding: const EdgeInsets.only(right: 16),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _StatPill(label: '$open ouverts', color: Colors.orange),
                    const SizedBox(width: 8),
                    _StatPill(label: '$resolved résolus', color: Colors.green),
                  ],
                ),
              );
            },
            loading: () => const SizedBox.shrink(),
            error: (_, __) => const SizedBox.shrink(),
          ),
        ],
      ),
      body: Column(
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(24, 16, 24, 8),
            child: SubjectFilterBar(),
          ),
          const Divider(),
          Expanded(
            child: subjectsAsync.when(
              loading: () => const LoadingIndicator(),
              error: (e, _) => ErrorView(message: e.toString()),
              data: (subjects) {
                if (subjects.isEmpty) {
                  return const EmptyState(
                    icon: Icons.task_alt,
                    message: 'Aucun sujet trouvé',
                    subtitle:
                        'Lancez le pipeline pour extraire les sujets MJ↔PJ',
                  );
                }

                return ListView.builder(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                  itemCount: subjects.length,
                  itemBuilder: (context, index) {
                    return SubjectListTile(subject: subjects[index]);
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

class _StatPill extends StatelessWidget {
  final String label;
  final Color color;

  const _StatPill({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: Theme.of(context)
            .textTheme
            .labelSmall
            ?.copyWith(color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}
