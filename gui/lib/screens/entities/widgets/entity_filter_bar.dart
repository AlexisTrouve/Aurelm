import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/app_constants.dart';
import '../../../core/theme/app_colors.dart';
import '../../../providers/entity_provider.dart';
import '../../../providers/civilization_provider.dart';

/// Semantic tag colors — same vocabulary as pipeline/pipeline/entity_profiler.py.
Color _entityTagColor(String tag) => switch (tag) {
      'militaire' => Colors.red,
      'religieux' => Colors.indigo,
      'politique' => Colors.purple,
      'economique' => Colors.green,
      'culturel' => Colors.amber,
      'diplomatique' => Colors.pink,
      'technologique' => Colors.blueGrey,
      'mythologique' => Colors.deepPurple,
      'actif' => Colors.teal,
      'disparu' => Colors.grey,
      'emergent' => Colors.cyan,
      'legendaire' => Colors.orange,
      _ => Colors.blueGrey,
    };

/// Two-row filter bar for the entity browser:
/// Row 1 — entity type chips + "Cachées" toggle + civ dropdown
/// Row 2 — semantic tag chips (from DB, colored)
class EntityFilterBar extends ConsumerWidget {
  const EntityFilterBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filters = ref.watch(entityFilterProvider);
    final civs = ref.watch(civListProvider);
    final tagsAsync = ref.watch(entityTagsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // --- Row 1: type chips + controls ---
        Row(
          children: [
            Expanded(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    FilterChip(
                      label: const Text('All types'),
                      selected: filters.entityType == null,
                      onSelected: (_) => ref
                          .read(entityFilterProvider.notifier)
                          .setEntityType(null),
                    ),
                    const SizedBox(width: 4),
                    ...AppConstants.entityTypes.map((type) => Padding(
                          padding: const EdgeInsets.only(right: 4),
                          child: FilterChip(
                            label: Text(type),
                            selected: filters.entityType == type,
                            selectedColor:
                                AppColors.entityColor(type).withValues(alpha: 0.2),
                            onSelected: (_) => ref
                                .read(entityFilterProvider.notifier)
                                .setEntityType(
                                    filters.entityType == type ? null : type),
                          ),
                        )),
                  ],
                ),
              ),
            ),

            const SizedBox(width: 8),

            // Toggle hidden
            Tooltip(
              message: filters.showHidden
                  ? 'Masquer les entités cachées'
                  : 'Afficher les entités cachées',
              child: FilterChip(
                avatar: const Icon(Icons.visibility_off, size: 16),
                label: const Text('Cachées'),
                selected: filters.showHidden,
                onSelected: (_) =>
                    ref.read(entityFilterProvider.notifier).toggleShowHidden(),
              ),
            ),

            const SizedBox(width: 8),

            // Civ dropdown
            civs.when(
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
              data: (civList) => DropdownButton<int?>(
                hint: const Text('All civs'),
                value: filters.civId,
                items: [
                  const DropdownMenuItem(value: null, child: Text('All civs')),
                  ...civList.map((c) => DropdownMenuItem(
                        value: c.civ.id,
                        child: Text(c.civ.name),
                      )),
                ],
                onChanged: (id) =>
                    ref.read(entityFilterProvider.notifier).setCivId(id),
              ),
            ),
          ],
        ),

        // --- Row 2: semantic tag chips (only if tags exist in DB) ---
        tagsAsync.when(
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
          data: (tags) {
            if (tags.isEmpty) return const SizedBox.shrink();
            return Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Wrap(
                spacing: 4,
                runSpacing: 4,
                children: tags.map((tag) {
                  final isSelected = filters.selectedTag == tag;
                  final color = _entityTagColor(tag);
                  return FilterChip(
                    label: Text(tag),
                    labelStyle: Theme.of(context).textTheme.labelSmall?.copyWith(
                          fontSize: 10,
                          color: isSelected ? Colors.white : color,
                          fontWeight: FontWeight.w600,
                        ),
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    selected: isSelected,
                    selectedColor: color.withValues(alpha: 0.8),
                    checkmarkColor: Colors.white,
                    side: BorderSide(color: color.withValues(alpha: 0.5)),
                    backgroundColor: color.withValues(alpha: 0.08),
                    onSelected: (_) => ref
                        .read(entityFilterProvider.notifier)
                        .setSelectedTag(isSelected ? null : tag),
                  );
                }).toList(),
              ),
            );
          },
        ),
      ],
    );
  }
}
