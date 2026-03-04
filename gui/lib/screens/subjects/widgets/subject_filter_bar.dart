import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../providers/subject_provider.dart';
import '../../../providers/civilization_provider.dart';

// civListProvider from civilization_provider.dart

/// Filter bar for the Subjects screen.
/// Controls direction (MJ→PJ / PJ→MJ), status (open/resolved), and civilization.
class SubjectFilterBar extends ConsumerWidget {
  const SubjectFilterBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filters = ref.watch(subjectFilterProvider);
    final civs = ref.watch(civListProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Direction chips
        Row(
          children: [
            Text('Direction:',
                style: Theme.of(context).textTheme.labelMedium),
            const SizedBox(width: 8),
            _DirectionChip(
              label: 'All',
              selected: filters.direction == null,
              onSelected: (_) =>
                  ref.read(subjectFilterProvider.notifier).setDirection(null),
            ),
            const SizedBox(width: 4),
            _DirectionChip(
              label: '→ MJ→PJ',
              selected: filters.direction == 'mj_to_pj',
              onSelected: (_) => ref
                  .read(subjectFilterProvider.notifier)
                  .setDirection('mj_to_pj'),
            ),
            const SizedBox(width: 4),
            _DirectionChip(
              label: '← PJ→MJ',
              selected: filters.direction == 'pj_to_mj',
              onSelected: (_) => ref
                  .read(subjectFilterProvider.notifier)
                  .setDirection('pj_to_mj'),
            ),
          ],
        ),
        const SizedBox(height: 8),

        // Status chips
        Row(
          children: [
            Text('Statut:', style: Theme.of(context).textTheme.labelMedium),
            const SizedBox(width: 8),
            _DirectionChip(
              label: 'Tous',
              selected: filters.subjectStatus == null,
              onSelected: (_) =>
                  ref.read(subjectFilterProvider.notifier).setStatus(null),
            ),
            const SizedBox(width: 4),
            _DirectionChip(
              label: '🔴 Ouvert',
              selected: filters.subjectStatus == 'open',
              onSelected: (_) =>
                  ref.read(subjectFilterProvider.notifier).setStatus('open'),
            ),
            const SizedBox(width: 4),
            _DirectionChip(
              label: '✅ Résolu',
              selected: filters.subjectStatus == 'resolved',
              onSelected: (_) =>
                  ref.read(subjectFilterProvider.notifier).setStatus('resolved'),
            ),
          ],
        ),

        // Civ dropdown (if multiple civs)
        civs.when(
          data: (civList) {
            if (civList.length <= 1) return const SizedBox.shrink();
            return Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Row(
                children: [
                  Text('Civ:', style: Theme.of(context).textTheme.labelMedium),
                  const SizedBox(width: 8),
                  DropdownButton<int?>(
                    value: filters.civId,
                    hint: const Text('Toutes'),
                    items: [
                      const DropdownMenuItem(value: null, child: Text('Toutes')),
                      ...civList.map((c) => DropdownMenuItem(
                            value: c.civ.id,
                            child: Text(c.civ.name),
                          )),
                    ],
                    onChanged: (v) =>
                        ref.read(subjectFilterProvider.notifier).setCivId(v),
                  ),
                ],
              ),
            );
          },
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
        ),
      ],
    );
  }
}

class _DirectionChip extends StatelessWidget {
  final String label;
  final bool selected;
  final ValueChanged<bool> onSelected;

  const _DirectionChip({
    required this.label,
    required this.selected,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return FilterChip(
      label: Text(label),
      selected: selected,
      onSelected: onSelected,
      visualDensity: VisualDensity.compact,
    );
  }
}
