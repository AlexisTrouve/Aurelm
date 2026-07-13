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
      color: colors.onSurfaceVariant.withValues(alpha: 0.9),
      fontWeight: FontWeight.w400,
    );

    // Obstacles for label placement. Node circles + node labels are FIXED and
    // take priority, so edge labels flow around them; each placed edge label is
    // then added so later labels avoid it too. Prevents the pile-up of relation
    // labels in the convergence zone near the ego center.
    final placed = <Rect>[];
    for (final n in data.nodes) {
      final p = layout.positions[n.id];
      if (p == null) continue;
      placed.add(Rect.fromCircle(center: p, radius: EgoGraphLayout.radiusForDepth(n.depth)));
      placed.add(_nodeLabelRect(n, p));
    }

    // Deterministic order so placement is stable frame-to-frame (no flicker on
    // hover — hover doesn't move nodes, so labels must not jump).
    final edges = [...data.edges]
      ..sort((a, b) {
        final c = a.sourceId.compareTo(b.sourceId);
        return c != 0 ? c : a.targetId.compareTo(b.targetId);
      });

    // Endpoints on the node borders (shared by both passes).
    Offset? p1Of(GraphEdge e) {
      final from = layout.positions[e.sourceId], to = layout.positions[e.targetId];
      if (from == null || to == null) return null;
      final dir = to - from;
      final len = dir.distance;
      if (len < 1) return null;
      return from + (dir / len) * EgoGraphLayout.radiusForDepth(_depthOf(e.sourceId));
    }

    Offset? p2Of(GraphEdge e) {
      final from = layout.positions[e.sourceId], to = layout.positions[e.targetId];
      if (from == null || to == null) return null;
      final dir = to - from;
      final len = dir.distance;
      if (len < 1) return null;
      return to - (dir / len) * EgoGraphLayout.radiusForDepth(_depthOf(e.targetId));
    }

    // Pass 1 — all lines first, so every label sits above every edge.
    for (final edge in edges) {
      final p1 = p1Of(edge), p2 = p2Of(edge);
      if (p1 == null || p2 == null) continue;
      paint.color = _edgeColor(edge.relationType).withValues(alpha: 0.5);
      canvas.drawLine(p1, p2, paint);
    }

    // Pass 2 — labels, always-on + pill, each lightly nudged to avoid overlap.
    for (final edge in edges) {
      final p1 = p1Of(edge), p2 = p2Of(edge);
      if (p1 == null || p2 == null) continue;

      final label = edge.relationType.replaceAll('_', ' ');
      final tp = TextPainter(
        text: TextSpan(text: label, style: labelStyle),
        textDirection: TextDirection.ltr,
      )..layout();
      final sz = Size(tp.width + 6, tp.height + 2);

      // Base slightly outward of the midpoint (roomier angular spacing), then a
      // small collision-aware perpendicular nudge.
      final dir = p2 - p1;
      final len = dir.distance;
      final unit = len < 1 ? const Offset(1, 0) : dir / len;
      final base = p1 + dir * 0.55;
      final perp = Offset(-unit.dy, unit.dx);
      final pos = _placeLabel(base, sz, unit, perp, placed);
      final rect = Rect.fromCenter(center: pos, width: sz.width, height: sz.height);

      canvas.drawRRect(
        RRect.fromRectAndRadius(rect, const Radius.circular(4)),
        Paint()..color = colors.surface.withValues(alpha: 0.9),
      );
      tp.paint(canvas, pos - Offset(tp.width / 2, tp.height / 2));
      placed.add(rect);
    }
  }

  /// Laid-out TextPainter for a node's name label — shared by the node draw and
  /// the edge-label collision pass so both agree on the label box.
  TextPainter _nodeLabelTp(GraphNode node) {
    final isCenter = node.depth == 0;
    final style = TextStyle(
      fontSize: isCenter ? 11 : node.depth == 1 ? 10 : 9,
      color: isCenter ? colors.onSurface : colors.onSurfaceVariant,
      fontWeight: isCenter ? FontWeight.w600 : FontWeight.w400,
    );
    return TextPainter(
      text: TextSpan(text: node.name, style: style),
      textDirection: TextDirection.ltr,
      maxLines: 2,
      ellipsis: '…',
    )..layout(maxWidth: isCenter ? 120.0 : 90.0);
  }

  /// Bounding rect of a node's name label (drawn just below the node).
  Rect _nodeLabelRect(GraphNode node, Offset pos) {
    final r = EgoGraphLayout.radiusForDepth(node.depth);
    final tp = _nodeLabelTp(node);
    final labelPos = pos + Offset(0, r + 4);
    return Rect.fromCenter(
      center: labelPos + Offset(0, tp.height / 2),
      width: tp.width + 6,
      height: tp.height + 2,
    );
  }

  /// Place an edge label near [base], nudging LIGHTLY to avoid [placed] rects.
  /// Candidates are a small grid: along the edge ([unit], gives each label a
  /// distinct radius to break the radial pile-up near the center) crossed with a
  /// perpendicular offset ([perp]). Labels are never dropped (always-on): the
  /// first fully-clear spot wins, else the least-overlapping one. Displacement is
  /// capped small (~≤28px along, ≤18px perp) so labels stay tied to their edge.
  Offset _placeLabel(Offset base, Size sz, Offset unit, Offset perp, List<Rect> placed) {
    const along = [0.0, -14.0, 14.0, -28.0, 28.0];
    const cross = [0.0, 9.0, -9.0, 18.0, -18.0];
    var best = base;
    var bestOverlap = double.infinity;
    for (final a in along) {
      for (final p in cross) {
        final c = base + unit * a + perp * p;
        final rect = Rect.fromCenter(center: c, width: sz.width, height: sz.height);
        var overlap = 0.0;
        for (final r in placed) {
          final inter = r.intersect(rect);
          if (inter.width > 0 && inter.height > 0) overlap += inter.width * inter.height;
        }
        if (overlap == 0) return c;
        if (overlap < bestOverlap) {
          bestOverlap = overlap;
          best = c;
        }
      }
    }
    return best;
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

      // Node label below (or inside for center) — same box the collision pass used.
      final tp = _nodeLabelTp(node);

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

