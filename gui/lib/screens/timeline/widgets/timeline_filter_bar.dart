import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/app_constants.dart';
import '../../../core/theme/app_colors.dart';
import '../../../providers/turn_provider.dart';
import '../../../providers/civilization_provider.dart';

class TimelineFilterBar extends ConsumerWidget {
  const TimelineFilterBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filters = ref.watch(timelineFilterProvider);
    final civs = ref.watch(civListProvider);

    return Row(
      children: [
        // Civ dropdown
        civs.when(
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
          data: (civList) {
            return DropdownButton<int?>(
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
              onChanged: (id) {
                ref.read(timelineFilterProvider.notifier).setCivId(id);
              },
            );
          },
        ),

        const SizedBox(width: 16),

        // Turn type chips
        Expanded(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                FilterChip(
                  label: const Text('All'),
                  selected: filters.turnType == null,
                  onSelected: (_) {
                    ref
                        .read(timelineFilterProvider.notifier)
                        .setTurnType(null);
                  },
                ),
                const SizedBox(width: 4),
                ...AppConstants.turnTypes.map((type) {
                  final color = AppColors.turnTypeColors[type] ?? Colors.grey;
                  return Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: FilterChip(
                      label: Text(type.replaceAll('_', ' ')),
                      selected: filters.turnType == type,
                      selectedColor: color.withValues(alpha: 0.2),
                      onSelected: (_) {
                        ref.read(timelineFilterProvider.notifier).setTurnType(
                            filters.turnType == type ? null : type);
                      },
                    ),
                  );
                }),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
