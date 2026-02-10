import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../providers/graph_provider.dart';
import '../../../providers/civilization_provider.dart';

class GraphControls extends ConsumerWidget {
  const GraphControls({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedCiv = ref.watch(graphCivFilterProvider);
    final showAll = ref.watch(graphShowAllProvider);
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
              value: selectedCiv,
              items: [
                const DropdownMenuItem(
                    value: null, child: Text('All civilizations')),
                ...civList.map((c) => DropdownMenuItem(
                      value: c.civ.id,
                      child: Text(c.civ.name),
                    )),
              ],
              onChanged: (id) {
                ref.read(graphCivFilterProvider.notifier).state = id;
              },
            );
          },
        ),

        const SizedBox(width: 16),

        // Show all toggle
        FilterChip(
          label: Text(showAll ? 'Showing all' : 'Top 50'),
          selected: showAll,
          onSelected: (val) {
            ref.read(graphShowAllProvider.notifier).state = val;
          },
        ),
      ],
    );
  }
}
