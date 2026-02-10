import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../providers/entity_provider.dart';
import '../../../widgets/common/search_field.dart';

class EntitySearchField extends ConsumerWidget {
  const EntitySearchField({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return SearchField(
      hint: 'Search entities by name...',
      onChanged: (query) {
        ref.read(entityFilterProvider.notifier).setSearchQuery(query);
      },
    );
  }
}
