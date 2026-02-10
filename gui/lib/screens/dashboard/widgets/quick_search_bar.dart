import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../providers/search_provider.dart';

class QuickSearchBar extends ConsumerStatefulWidget {
  const QuickSearchBar({super.key});

  @override
  ConsumerState<QuickSearchBar> createState() => _QuickSearchBarState();
}

class _QuickSearchBarState extends ConsumerState<QuickSearchBar> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  bool _showResults = false;

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final results = ref.watch(globalSearchResultsProvider);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        TextField(
          controller: _controller,
          focusNode: _focusNode,
          decoration: InputDecoration(
            hintText: 'Search entities...',
            prefixIcon: const Icon(Icons.search, size: 20),
            isDense: true,
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
          onChanged: (value) {
            ref.read(globalSearchQueryProvider.notifier).state = value;
            setState(() => _showResults = value.length >= 2);
          },
          onTap: () {
            if (_controller.text.length >= 2) {
              setState(() => _showResults = true);
            }
          },
        ),
        if (_showResults)
          results.when(
            loading: () => const SizedBox.shrink(),
            error: (_, __) => const SizedBox.shrink(),
            data: (entities) {
              if (entities.isEmpty) return const SizedBox.shrink();
              return Material(
                elevation: 4,
                borderRadius: BorderRadius.circular(8),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 200),
                  child: ListView.builder(
                    shrinkWrap: true,
                    itemCount: entities.length,
                    itemBuilder: (context, index) {
                      final e = entities[index];
                      return ListTile(
                        dense: true,
                        title: Text(e.entity.canonicalName),
                        subtitle: Text(e.entity.entityType),
                        onTap: () {
                          context.go('/entities/${e.entity.id}');
                          _controller.clear();
                          setState(() => _showResults = false);
                          _focusNode.unfocus();
                        },
                      );
                    },
                  ),
                ),
              );
            },
          ),
      ],
    );
  }
}
