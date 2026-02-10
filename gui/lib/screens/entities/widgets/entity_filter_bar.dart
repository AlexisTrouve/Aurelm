import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/app_constants.dart';
import '../../../core/theme/app_colors.dart';
import '../../../providers/entity_provider.dart';
import '../../../providers/civilization_provider.dart';

class EntityFilterBar extends ConsumerWidget {
  const EntityFilterBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filters = ref.watch(entityFilterProvider);
    final civs = ref.watch(civListProvider);

    return Row(
      children: [
        // Entity type chips
        Expanded(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                FilterChip(
                  label: const Text('All types'),
                  selected: filters.entityType == null,
                  onSelected: (_) {
                    ref.read(entityFilterProvider.notifier).setEntityType(null);
                  },
                ),
                const SizedBox(width: 4),
                ...AppConstants.entityTypes.map((type) {
                  return Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: FilterChip(
                      label: Text(type),
                      selected: filters.entityType == type,
                      selectedColor: AppColors.entityColor(type).withOpacity(0.2),
                      onSelected: (_) {
                        ref.read(entityFilterProvider.notifier).setEntityType(
                            filters.entityType == type ? null : type);
                      },
                    ),
                  );
                }),
              ],
            ),
          ),
        ),

        const SizedBox(width: 8),

        // Civ dropdown
        civs.when(
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
          data: (civList) {
            return DropdownButton<int?>(
              hint: const Text('All civs'),
              value: filters.civId,
              items: [
                const DropdownMenuItem(value: null, child: Text('All civs')),
                ...civList.map((c) => DropdownMenuItem(
                      value: c.civ.id,
                      child: Text(c.civ.name),
                    )),
              ],
              onChanged: (id) {
                ref.read(entityFilterProvider.notifier).setCivId(id);
              },
            );
          },
        ),
      ],
    );
  }
}
