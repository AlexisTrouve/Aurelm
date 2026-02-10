import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../models/graph_data.dart';

class GraphNodeWidget extends StatelessWidget {
  final GraphNode node;
  final VoidCallback? onTap;

  const GraphNodeWidget({super.key, required this.node, this.onTap});

  @override
  Widget build(BuildContext context) {
    final color = AppColors.entityColor(node.entityType);
    // Size based on mention count: min 32, max 64
    final size = (24 + math.log(node.mentionCount + 1) * 8).clamp(32.0, 64.0);

    return GestureDetector(
      onTap: () => context.go('/entities/${node.id}'),
      child: Tooltip(
        message: '${node.name} (${node.entityType})\n${node.mentionCount} mentions',
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: size,
              height: size,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: color.withValues(alpha: 0.2),
                border: Border.all(color: color, width: 2),
              ),
              alignment: Alignment.center,
              child: Text(
                node.name.substring(0, math.min(2, node.name.length)).toUpperCase(),
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.bold,
                  fontSize: size * 0.3,
                ),
              ),
            ),
            const SizedBox(height: 2),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 80),
              child: Text(
                node.name,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      fontSize: 9,
                    ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
