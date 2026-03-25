import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../providers/subject_provider.dart';
import '../../../providers/civilization_provider.dart';
import '../../../core/theme/app_colors.dart';

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

        const SizedBox(height: 8),

        // Tag filter chips — colored per domain, same palette as entity tags
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              Text('Tag:', style: Theme.of(context).textTheme.labelMedium),
              const SizedBox(width: 8),
              _DirectionChip(
                label: 'Tous',
                selected: filters.selectedTag == null,
                onSelected: (_) =>
                    ref.read(subjectFilterProvider.notifier).setTag(null),
              ),
              const SizedBox(width: 4),
              for (final tag in const [
                'militaire', 'politique', 'religieux', 'economique',
                'culturel', 'social', 'diplomatique', 'technologique', 'mythologique',
              ]) ...[
                _TagChip(
                  tag: tag,
                  selected: filters.selectedTag == tag,
                  onTap: () => ref
                      .read(subjectFilterProvider.notifier)
                      .setTag(filters.selectedTag == tag ? null : tag),
                ),
                const SizedBox(width: 4),
              ],
            ],
          ),
        ),

        const SizedBox(height: 8),

        // Favorites filter chip
        FilterChip(
          avatar: const Icon(Icons.star, size: 14, color: Colors.amber),
          label: const Text('Favoris'),
          selected: filters.favoritesOnly,
          selectedColor: Colors.amber.withValues(alpha: 0.2),
          visualDensity: VisualDensity.compact,
          onSelected: (v) =>
              ref.read(subjectFilterProvider.notifier).setFavoritesOnly(v),
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
                    // Global civ filter — shared across all list screens
                    value: ref.watch(selectedCivProvider),
                    hint: const Text('Toutes'),
                    items: [
                      const DropdownMenuItem(value: null, child: Text('Toutes')),
                      ...civList.map((c) => DropdownMenuItem(
                            value: c.civ.id,
                            child: Text(c.civ.name),
                          )),
                    ],
                    onChanged: (v) =>
                        ref.read(selectedCivProvider.notifier).state = v,
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

/// Colored tag filter chip — uses the same color palette as entity tags.
class _TagChip extends StatelessWidget {
  final String tag;
  final bool selected;
  final VoidCallback onTap;

  const _TagChip({
    required this.tag,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = AppColors.entityTagColor(tag);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 140),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: selected ? color.withValues(alpha: 0.85) : color.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: selected ? color : color.withValues(alpha: 0.4)),
        ),
        child: Text(
          tag,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: selected ? Colors.white : color,
                fontWeight: FontWeight.w600,
              ),
        ),
      ),
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
