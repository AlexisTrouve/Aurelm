import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../providers/subject_provider.dart';
import '../../../widgets/common/section_header.dart';
import '../../subjects/widgets/subject_list_tile.dart';

/// Frame affiché sur CivDetailScreen : 5 sujets récents + lien "View all" filtré.
class CivSubjectsFrame extends ConsumerWidget {
  final int civId;

  const CivSubjectsFrame({super.key, required this.civId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final subjectsAsync = ref.watch(civRecentSubjectsProvider(civId));
    final statsAsync = ref.watch(subjectStatsProvider(civId));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(
          title: 'Sujets',
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Compteurs open/resolved
              statsAsync.maybeWhen(
                data: (stats) => Text(
                  '${stats['open'] ?? 0} ouverts · ${stats['resolved'] ?? 0} résolus',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                ),
                orElse: () => const SizedBox.shrink(),
              ),
              const SizedBox(width: 8),
              // Navigue vers /subjects avec filtre civ pré-sélectionné
              TextButton(
                onPressed: () {
                  ref.read(subjectFilterProvider.notifier).setCivId(civId);
                  context.go('/subjects');
                },
                child: const Text('View all'),
              ),
            ],
          ),
        ),
        subjectsAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => const Text('Erreur chargement sujets'),
          data: (subjects) {
            if (subjects.isEmpty) {
              return const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: Text('Aucun sujet pour cette civilisation'),
              );
            }
            return Column(
              children:
                  subjects.map((s) => SubjectListTile(subject: s)).toList(),
            );
          },
        ),
      ],
    );
  }
}
