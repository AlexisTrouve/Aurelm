import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/entity_provider.dart';
import '../../providers/database_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/empty_state.dart';
import 'widgets/entity_list_tile.dart';
import 'widgets/entity_filter_bar.dart';
import 'widgets/entity_search_field.dart';
import 'widgets/entity_edit_dialog.dart';

class EntityBrowserScreen extends ConsumerWidget {
  const EntityBrowserScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dbPath = ref.watch(dbPathProvider);
    if (dbPath == null) {
      return SelectionArea(
        child: Scaffold(
          body: EmptyState(
            icon: Icons.storage,
            message: 'No database configured',
          ),
        ),
      );
    }

    final entities = ref.watch(entityListProvider);

    return SelectionArea(
      child: Scaffold(
      floatingActionButton: FloatingActionButton(
        tooltip: 'Créer une entité',
        onPressed: () => showDialog<int>(
          context: context,
          builder: (_) => const EntityEditDialog(),
        ).then((newId) {
          // If created, navigate to the new entity detail page
          if (newId != null && context.mounted) {
            context.go('/entities/$newId');
          }
        }),
        child: const Icon(Icons.add),
      ),
      appBar: AppBar(
        title: const Text('Entities'),
        actions: [
          IconButton(
            icon: const Icon(Icons.block),
            tooltip: 'Entités désactivées',
            onPressed: () => context.go('/entities/disabled'),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 8),
            child: Column(
              children: [
                const EntitySearchField(),
                const SizedBox(height: 8),
                const EntityFilterBar(),
              ],
            ),
          ),
          const Divider(),
          Expanded(
            child: entities.when(
              loading: () => const LoadingIndicator(),
              error: (e, _) => ErrorView(message: e.toString()),
              data: (entityList) {
                if (entityList.isEmpty) {
                  return const EmptyState(
                    icon: Icons.category_outlined,
                    message: 'No entities found',
                    subtitle: 'Try adjusting your filters',
                  );
                }
                return ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: entityList.length,
                  itemBuilder: (context, index) {
                    return EntityListTile(entity: entityList[index]);
                  },
                );
              },
            ),
          ),
        ],
      ),
      ),
    );
  }
}
