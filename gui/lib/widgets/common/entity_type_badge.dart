import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

class EntityTypeBadge extends StatelessWidget {
  final String entityType;
  final bool compact;

  const EntityTypeBadge({
    super.key,
    required this.entityType,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    final color = AppColors.entityColor(entityType);
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 6 : 8,
        vertical: compact ? 2 : 4,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        entityType,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: color,
              fontWeight: FontWeight.w600,
            ),
      ),
    );
  }
}
