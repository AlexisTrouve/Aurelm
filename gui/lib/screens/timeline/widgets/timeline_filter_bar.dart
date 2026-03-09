import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../providers/turn_provider.dart';
import '../../../providers/civilization_provider.dart';

/// Couleurs des tags thématiques — doit rester en sync avec timeline_turn_card.dart.
Color _tagColor(String tag) => switch (tag) {
      'religion' => Colors.indigo,
      'culture' => Colors.amber,
      'exploration' => Colors.cyan,
      'construction' => Colors.brown,
      'agriculture' => Colors.green,
      'crise' => Colors.red,
      'migration' => Colors.orange,
      'decouverte' => Colors.lightBlue,
      'politique' => Colors.purple,
      'commerce' => Colors.yellow,
      'technologie' => Colors.blueGrey,
      'diplomatie' => Colors.pink,
      'combat' => Colors.deepOrange,
      'mort' => Colors.grey,
      'ressource' => Colors.lime,
      _ => Colors.blueGrey,
    };

/// Filter bar de la timeline :
/// Ligne 1 — Civ dropdown
/// Ligne 2 — Tag thématiques cliquables (toggle)
class TimelineFilterBar extends ConsumerWidget {
  const TimelineFilterBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filters = ref.watch(timelineFilterProvider);
    final civs = ref.watch(civListProvider);
    final tagsAsync = ref.watch(turnTagsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // --- Civ dropdown ---
        civs.when(
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
          data: (civList) => DropdownButton<int?>(
            hint: const Text('All civilizations'),
            value: filters.civId,
            items: [
              const DropdownMenuItem(
                  value: null, child: Text('All civilizations')),
              ...civList.map((c) => DropdownMenuItem(
                    value: c.civ.id,
                    child: Text(c.civ.name),
                  )),
            ],
            onChanged: (id) =>
                ref.read(timelineFilterProvider.notifier).setCivId(id),
          ),
        ),

        const SizedBox(height: 4),

        // --- Thematic tag chips ---
        tagsAsync.when(
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
          data: (tags) {
            if (tags.isEmpty) return const SizedBox.shrink();
            return Wrap(
              spacing: 4,
              runSpacing: 4,
              children: tags.map((tag) {
                final isSelected = filters.selectedTag == tag;
                final color = _tagColor(tag);
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
                      .read(timelineFilterProvider.notifier)
                      .setSelectedTag(isSelected ? null : tag),
                );
              }).toList(),
            );
          },
        ),
      ],
    );
  }
}
