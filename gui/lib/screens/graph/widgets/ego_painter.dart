import 'dart:math';
import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../models/graph_data.dart';

/// Computes and exposes node positions so the screen can handle tap detection.
class EgoGraphLayout {
  final Map<int, Offset> positions;
  final double nodeRadius; // base radius for center node

  const EgoGraphLayout({required this.positions, required this.nodeRadius});

  /// Node radius by depth: center=28, depth1=20, depth2=14
  static double radiusForDepth(int depth) {
    switch (depth) {
      case 0: return 28;
      case 1: return 20;
      default: return 14;
    }
  }

  /// Compute layout for a given canvas size and graph data.
  static EgoGraphLayout compute(Size size, GraphData data) {
    if (data.nodes.isEmpty) return EgoGraphLayout(positions: {}, nodeRadius: 28);

    final center = Offset(size.width / 2, size.height / 2);
    final positions = <int, Offset>{};

    final centerNode = data.nodes.where((n) => n.depth == 0).firstOrNull;
    final depth1 = data.nodes.where((n) => n.depth == 1).toList();
    final depth2 = data.nodes.where((n) => n.depth == 2).toList();

    if (centerNode != null) positions[centerNode.id] = center;

    // Depth-1 ring radius adapts to count — less crowded with few nodes
    final r1 = min(size.shortestSide * 0.30, 220.0);
    for (int i = 0; i < depth1.length; i++) {
      final angle = (2 * pi * i / depth1.length) - pi / 2;
      positions[depth1[i].id] = center + Offset(cos(angle) * r1, sin(angle) * r1);
    }

    // Depth-2 ring — grouped near their depth-1 parent (using edges)
    if (depth2.isNotEmpty) {
      final r2 = min(size.shortestSide * 0.48, 340.0);
      // Group depth-2 nodes by parent
      final parentAngles = <int, double>{};
      for (int i = 0; i < depth1.length; i++) {
        parentAngles[depth1[i].id] = (2 * pi * i / depth1.length) - pi / 2;
      }

      // Assign each depth-2 node to a parent via edges
      final parentOf = <int, int>{};
      for (final d2 in depth2) {
        // Find first edge connecting this node to a depth-1 node
        for (final edge in data.edges) {
          if (edge.sourceId == d2.id && positions.containsKey(edge.targetId)) {
            parentOf[d2.id] = edge.targetId;
            break;
          }
          if (edge.targetId == d2.id && positions.containsKey(edge.sourceId)) {
            parentOf[d2.id] = edge.sourceId;
            break;
          }
        }
      }

      // Group by parent and space evenly around parent angle
      final byParent = <int, List<int>>{};
      for (final d2 in depth2) {
        final pid = parentOf[d2.id];
        if (pid != null) {
          byParent.putIfAbsent(pid, () => []).add(d2.id);
        }
      }

      // Unparented depth-2 nodes get evenly distributed around the outer ring
      final unparented = depth2.where((n) => !parentOf.containsKey(n.id)).toList();
      for (int i = 0; i < unparented.length; i++) {
        final angle = (2 * pi * i / max(unparented.length, 1)) - pi / 2;
        positions[unparented[i].id] = center + Offset(cos(angle) * r2, sin(angle) * r2);
      }

      for (final entry in byParent.entries) {
        final parentAngle = parentAngles[entry.key] ?? 0.0;
        final siblings = entry.value;
        final spread = pi / 4; // +/- 45° spread around parent
        for (int i = 0; i < siblings.length; i++) {
          final offset = siblings.length == 1
              ? 0.0
              : -spread / 2 + spread * i / (siblings.length - 1);
          final angle = parentAngle + offset;
          positions[siblings[i]] = center + Offset(cos(angle) * r2, sin(angle) * r2);
        }
      }
    }

    return EgoGraphLayout(positions: positions, nodeRadius: 28);
  }
}

/// CustomPainter for the ego graph — draws edges then nodes.
class EgoPainter extends CustomPainter {
  final GraphData data;
  final EgoGraphLayout layout;
  final int? hoveredId;
  final Set<int> expandedIds;
  final ColorScheme colors;

  EgoPainter({
    required this.data,
    required this.layout,
    this.hoveredId,
    this.expandedIds = const {},
    required this.colors,
  });

  @override
  void paint(Canvas canvas, Size size) {
    _drawEdges(canvas);
    _drawNodes(canvas);
  }

  /// Returns the depth of a node by id, defaulting to 1 if not found.
  int _depthOf(int nodeId) {
    for (final n in data.nodes) {
      if (n.id == nodeId) return n.depth;
    }
    return 1;
  }

  void _drawEdges(Canvas canvas) {
    final paint = Paint()
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;

    final labelStyle = TextStyle(
      fontSize: 9,
      color: colors.onSurfaceVariant.withValues(alpha: 0.8),
      fontWeight: FontWeight.w400,
    );

    for (final edge in data.edges) {
      final from = layout.positions[edge.sourceId];
      final to = layout.positions[edge.targetId];
      if (from == null || to == null) continue;

      // Color edge by relation category
      paint.color = _edgeColor(edge.relationType).withValues(alpha: 0.5);

      // Draw line with a slight arrow indication (shift endpoints to node borders)
      final srcR = EgoGraphLayout.radiusForDepth(_depthOf(edge.sourceId));
      final tgtR = EgoGraphLayout.radiusForDepth(_depthOf(edge.targetId));

      final dir = (to - from);
      final len = dir.distance;
      if (len < 1) continue;
      final unit = dir / len;
      final p1 = from + unit * srcR;
      final p2 = to - unit * tgtR;

      canvas.drawLine(p1, p2, paint);

      // Relation type label at midpoint
      final mid = Offset((p1.dx + p2.dx) / 2, (p1.dy + p2.dy) / 2);
      final label = edge.relationType.replaceAll('_', ' ');
      final tp = TextPainter(
        text: TextSpan(text: label, style: labelStyle),
        textDirection: TextDirection.ltr,
      )..layout();
      // Small white background pill behind label
      final rect = Rect.fromCenter(
        center: mid,
        width: tp.width + 6,
        height: tp.height + 2,
      );
      canvas.drawRRect(
        RRect.fromRectAndRadius(rect, const Radius.circular(4)),
        Paint()..color = colors.surface.withValues(alpha: 0.85),
      );
      tp.paint(canvas, mid - Offset(tp.width / 2, tp.height / 2));
    }
  }

  void _drawNodes(Canvas canvas) {
    for (final node in data.nodes) {
      final pos = layout.positions[node.id];
      if (pos == null) continue;

      final r = EgoGraphLayout.radiusForDepth(node.depth);
      final color = AppColors.entityColor(node.entityType);
      final isCenter = node.depth == 0;
      final isHovered = node.id == hoveredId;
      final isExpanded = expandedIds.contains(node.id);

      // Outer ring on expanded depth-1 nodes to signal they have visible children.
      if (isExpanded) {
        canvas.drawCircle(
          pos,
          r + 5,
          Paint()
            ..color = color.withValues(alpha: 0.35)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.5,
        );
      }

      // Shadow/glow for center and hovered
      if (isCenter || isHovered) {
        canvas.drawCircle(
          pos,
          r + 6,
          Paint()..color = color.withValues(alpha: 0.15),
        );
      }

      // Node circle
      canvas.drawCircle(pos, r, Paint()..color = color.withValues(alpha: isCenter ? 0.9 : 0.7));
      canvas.drawCircle(
        pos,
        r,
        Paint()
          ..color = isCenter ? color : color.withValues(alpha: 0.5)
          ..style = PaintingStyle.stroke
          ..strokeWidth = isCenter ? 2.5 : 1.5,
      );

      // Mention count badge on center node
      if (isCenter && node.mentionCount > 0) {
        final badge = '${node.mentionCount}';
        final badgeStyle = TextStyle(fontSize: 8, color: colors.surface, fontWeight: FontWeight.bold);
        final btp = TextPainter(text: TextSpan(text: badge, style: badgeStyle), textDirection: TextDirection.ltr)..layout();
        final bPos = pos + Offset(r * 0.6, -r * 0.6);
        canvas.drawCircle(bPos, 8, Paint()..color = color);
        btp.paint(canvas, bPos - Offset(btp.width / 2, btp.height / 2));
      }

      // Node label below (or inside for center)
      final nameStyle = TextStyle(
        fontSize: isCenter ? 11 : node.depth == 1 ? 10 : 9,
        color: isCenter ? colors.onSurface : colors.onSurfaceVariant,
        fontWeight: isCenter ? FontWeight.w600 : FontWeight.w400,
      );
      final maxWidth = isCenter ? 120.0 : 90.0;
      final tp = TextPainter(
        text: TextSpan(text: node.name, style: nameStyle),
        textDirection: TextDirection.ltr,
        maxLines: 2,
        ellipsis: '…',
      )..layout(maxWidth: maxWidth);

      // White background for readability
      final labelPos = pos + Offset(0, r + 4);
      final labelRect = Rect.fromCenter(
        center: labelPos + Offset(0, tp.height / 2),
        width: tp.width + 6,
        height: tp.height + 2,
      );
      canvas.drawRRect(
        RRect.fromRectAndRadius(labelRect, const Radius.circular(3)),
        Paint()..color = colors.surface.withValues(alpha: 0.8),
      );
      tp.paint(canvas, labelPos - Offset(tp.width / 2, 0));
    }
  }

  Color _edgeColor(String type) {
    switch (type) {
      case 'allied_with': return Colors.green;
      case 'enemy_of': return Colors.red;
      case 'trades_with': return Colors.amber;
      case 'worships': return Colors.purple;
      case 'controls': case 'member_of': case 'part_of': return Colors.blue;
      case 'produces': return Colors.orange;
      case 'located_in': return Colors.teal;
      default: return Colors.grey;
    }
  }

  @override
  bool shouldRepaint(EgoPainter old) =>
      old.data != data || old.hoveredId != hoveredId || old.layout != layout;
}

