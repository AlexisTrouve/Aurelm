import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
/// Ligne 1 — Civ dropdown + champs De/À tour
/// Ligne 2 — Tags thématiques cliquables (toggle)
class TimelineFilterBar extends ConsumerStatefulWidget {
  const TimelineFilterBar({super.key});

  @override
  ConsumerState<TimelineFilterBar> createState() => _TimelineFilterBarState();
}

class _TimelineFilterBarState extends ConsumerState<TimelineFilterBar> {
  final _fromCtrl = TextEditingController();
  final _toCtrl = TextEditingController();

  @override
  void dispose() {
    _fromCtrl.dispose();
    _toCtrl.dispose();
    super.dispose();
  }

  /// Compact integer field for turn number input.
  Widget _turnField(String hint, TextEditingController ctrl, void Function(int?) onChanged) {
    return SizedBox(
      width: 64,
      child: TextField(
        controller: ctrl,
        keyboardType: TextInputType.number,
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
        decoration: InputDecoration(
          hintText: hint,
          isDense: true,
          contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(6)),
        ),
        onChanged: (v) => onChanged(int.tryParse(v)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final filters = ref.watch(timelineFilterProvider);
    final civs = ref.watch(civListProvider);
    final tagsAsync = ref.watch(turnTagsProvider);
    final notifier = ref.read(timelineFilterProvider.notifier);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // --- Row 1: Civ dropdown + tour range ---
        Row(
          children: [
            // Civ dropdown
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
                onChanged: (id) => notifier.setCivId(id),
              ),
            ),
            const SizedBox(width: 16),
            // Turn number range: De / À
            Text('Tours :', style: Theme.of(context).textTheme.labelSmall),
            const SizedBox(width: 6),
            _turnField('De', _fromCtrl, notifier.setFromTurn),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 4),
              child: Text('–'),
            ),
            _turnField('À', _toCtrl, notifier.setToTurn),
          ],
        ),

        const SizedBox(height: 4),

        const SizedBox(height: 4),

        // Favorites filter chip
        FilterChip(
          avatar: const Icon(Icons.star, size: 14, color: Colors.amber),
          label: const Text('Favoris'),
          selected: filters.favoritesOnly,
          selectedColor: Colors.amber.withValues(alpha: 0.2),
          visualDensity: VisualDensity.compact,
          onSelected: (v) => notifier.setFavoritesOnly(v),
        ),

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
