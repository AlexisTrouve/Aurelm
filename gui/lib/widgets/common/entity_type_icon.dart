import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

class EntityTypeIcon extends StatelessWidget {
  final String entityType;
  final double size;

  const EntityTypeIcon({
    super.key,
    required this.entityType,
    this.size = 20,
  });

  static const Map<String, IconData> _icons = {
    'person': Icons.person,
    'place': Icons.place,
    'technology': Icons.build,
    'institution': Icons.account_balance,
    'resource': Icons.inventory_2,
    'creature': Icons.pets,
    'event': Icons.event,
  };

  @override
  Widget build(BuildContext context) {
    return Icon(
      _icons[entityType] ?? Icons.help_outline,
      size: size,
      color: AppColors.entityColor(entityType),
    );
  }
}
