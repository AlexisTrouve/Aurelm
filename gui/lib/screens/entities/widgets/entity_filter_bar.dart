import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/app_constants.dart';
import '../../../core/theme/app_colors.dart';
import '../../../providers/entity_provider.dart';
import '../../../providers/civilization_provider.dart';

/// Semantic tag colors — same vocabulary as pipeline/pipeline/entity_profiler.py.
Color _tagColor(String tag) => switch (tag) {
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

/// Base chip used for every filter pill in this bar.
/// Fixed size, smooth color transition, no checkmark weirdness.
class _Chip extends StatelessWidget {
  final String label;
  final Color color;
  final bool selected;
  final IconData? icon;
  final VoidCallback onTap;

  const _Chip({
    required this.label,
    required this.color,
    required this.selected,
    required this.onTap,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final bg = selected ? color.withValues(alpha: 0.85) : color.withValues(alpha: 0.10);
    final fg = selected ? Colors.white : color;
    final border = selected ? color : color.withValues(alpha: 0.40);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 140),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: border, width: selected ? 1.5 : 1),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(icon, size: 11, color: fg),
              const SizedBox(width: 4),
            ],
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: fg,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Compact civ selector — styled like a _Chip, opens a popup menu.
class _CivChip extends StatelessWidget {
  final int? selectedCivId;
  final List<({int id, String name})> civs;
  final ValueChanged<int?> onChanged;

  const _CivChip({
    required this.selectedCivId,
    required this.civs,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final selected = selectedCivId != null;
    final label = selected
        ? civs.firstWhere((c) => c.id == selectedCivId).name
        : 'All civs';
    final color = Theme.of(context).colorScheme.outline;
    final bg = selected ? color.withValues(alpha: 0.85) : color.withValues(alpha: 0.10);
    final fg = selected ? Colors.white : color;
    final border = selected ? color : color.withValues(alpha: 0.40);

    return PopupMenuButton<int?>(
      tooltip: 'Filter by civilization',
      onSelected: onChanged,
      itemBuilder: (_) => [
        const PopupMenuItem<int?>(value: null, child: Text('All civs')),
        ...civs.map((c) => PopupMenuItem<int?>(value: c.id, child: Text(c.name))),
      ],
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 140),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: border, width: selected ? 1.5 : 1),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.public, size: 11, color: fg),
            const SizedBox(width: 4),
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: fg,
                  ),
            ),
            const SizedBox(width: 3),
            Icon(Icons.arrow_drop_down, size: 13, color: fg),
          ],
        ),
      ),
    );
  }
}

/// Two-row filter bar for the entity browser.
/// Row 1 — entity type pills + Cachées / Favoris / Civ controls
/// Row 2 — semantic tag pills (DB-driven, colored)
class EntityFilterBar extends ConsumerWidget {
  const EntityFilterBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filters = ref.watch(entityFilterProvider);
    final civs = ref.watch(civListProvider);
    final tagsAsync = ref.watch(entityTagsProvider);
    final neutral = Theme.of(context).colorScheme.outline;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ── Row 1 ──────────────────────────────────────────────────────────
        Row(
          children: [
            // Type chips — scrollable
            Expanded(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _Chip(
                      label: 'All types',
                      color: neutral,
                      selected: filters.entityType == null,
                      onTap: () => ref
                          .read(entityFilterProvider.notifier)
                          .setEntityType(null),
                    ),
                    const SizedBox(width: 4),
                    ...AppConstants.entityTypes.map((type) {
                      final isSelected = filters.entityType == type;
                      return Padding(
                        padding: const EdgeInsets.only(right: 4),
                        child: _Chip(
                          label: type,
                          color: AppColors.entityColor(type),
                          selected: isSelected,
                          onTap: () => ref
                              .read(entityFilterProvider.notifier)
                              .setEntityType(isSelected ? null : type),
                        ),
                      );
                    }),
                  ],
                ),
              ),
            ),

            const SizedBox(width: 8),

            // Controls — fixed right side
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Tooltip(
                  message: filters.showHidden
                      ? 'Masquer les entités cachées'
                      : 'Afficher les entités cachées',
                  child: _Chip(
                    label: 'Cachées',
                    icon: Icons.visibility_off,
                    color: neutral,
                    selected: filters.showHidden,
                    onTap: () => ref
                        .read(entityFilterProvider.notifier)
                        .toggleShowHidden(),
                  ),
                ),
                const SizedBox(width: 4),
                _Chip(
                  label: 'Favoris',
                  icon: Icons.star,
                  color: Colors.amber,
                  selected: filters.favoritesOnly,
                  onTap: () => ref
                      .read(entityFilterProvider.notifier)
                      .setFavoritesOnly(!filters.favoritesOnly),
                ),
                const SizedBox(width: 4),
                civs.when(
                  loading: () => const SizedBox.shrink(),
                  error: (_, __) => const SizedBox.shrink(),
                  data: (civList) => _CivChip(
                    // Global civ filter — shared across all list screens
                    selectedCivId: ref.watch(selectedCivProvider),
                    civs: civList
                        .map((c) => (id: c.civ.id, name: c.civ.name))
                        .toList(),
                    onChanged: (id) =>
                        ref.read(selectedCivProvider.notifier).state = id,
                  ),
                ),
              ],
            ),
          ],
        ),

        // ── Row 2: semantic tag pills ──────────────────────────────────────
        tagsAsync.when(
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
          data: (tags) {
            if (tags.isEmpty) return const SizedBox.shrink();
            return Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Wrap(
                spacing: 4,
                runSpacing: 4,
                children: tags.map((tag) {
                  final isSelected = filters.selectedTag == tag;
                  return _Chip(
                    label: tag,
                    color: _tagColor(tag),
                    selected: isSelected,
                    onTap: () => ref
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
