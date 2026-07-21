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
  ///
  /// Two-step: (1) lay the ego graph out in a UNIT coordinate space (center at
  /// origin, depth-1 ring at radius 1, depth-2 at 1.7); (2) auto-fit that cloud
  /// into the real canvas — scale to fill the pane, translate to center on the
  /// content. Fitting (rather than the old fixed 220/340px radius caps) is what
  /// stops the graph from sitting tiny in a big pane or clipping in a small one;
  /// it mirrors the headless exporter's matplotlib set_xlim/ylim framing.
  static EgoGraphLayout compute(Size size, GraphData data) {
    if (data.nodes.isEmpty) return const EgoGraphLayout(positions: {}, nodeRadius: 28);

    // --- 1. Unit-space radial layout, center at origin ----------------------
    const rawR1 = 1.0; // depth-1 ring radius (unit)
    const rawR2 = 1.7; // depth-2 ring radius (unit) — matches exporter ring gap
    final raw = <int, Offset>{};

    final centerNode = data.nodes.where((n) => n.depth == 0).firstOrNull;
    final depth1 = data.nodes.where((n) => n.depth == 1).toList();
    final depth2 = data.nodes.where((n) => n.depth == 2).toList();

    if (centerNode != null) raw[centerNode.id] = Offset.zero;

    // Depth-1 ring — evenly spaced, 12 o'clock start.
    final parentAngles = <int, double>{};
    for (int i = 0; i < depth1.length; i++) {
      final angle = (2 * pi * i / depth1.length) - pi / 2;
      parentAngles[depth1[i].id] = angle;
      raw[depth1[i].id] = Offset(cos(angle) * rawR1, sin(angle) * rawR1);
    }

    // Depth-2 ring — clustered within +/-45 degrees of their depth-1 parent.
    if (depth2.isNotEmpty) {
      // Assign each depth-2 node to a parent via edges (first depth-1 hit wins).
      final parentOf = <int, int>{};
      for (final d2 in depth2) {
        for (final edge in data.edges) {
          if (edge.sourceId == d2.id && parentAngles.containsKey(edge.targetId)) {
            parentOf[d2.id] = edge.targetId;
            break;
          }
          if (edge.targetId == d2.id && parentAngles.containsKey(edge.sourceId)) {
            parentOf[d2.id] = edge.sourceId;
            break;
          }
        }
      }

      final byParent = <int, List<int>>{};
      for (final d2 in depth2) {
        final pid = parentOf[d2.id];
        if (pid != null) byParent.putIfAbsent(pid, () => []).add(d2.id);
      }

      // Unparented depth-2 nodes get evenly distributed around the outer ring.
      final unparented = depth2.where((n) => !parentOf.containsKey(n.id)).toList();
      for (int i = 0; i < unparented.length; i++) {
        final angle = (2 * pi * i / max(unparented.length, 1)) - pi / 2;
        raw[unparented[i].id] = Offset(cos(angle) * rawR2, sin(angle) * rawR2);
      }

      for (final entry in byParent.entries) {
        final parentAngle = parentAngles[entry.key] ?? 0.0;
        final siblings = entry.value;
        const spread = pi / 4; // +/- 45 degrees around parent
        for (int i = 0; i < siblings.length; i++) {
          final offset = siblings.length == 1
              ? 0.0
              : -spread / 2 + spread * i / (siblings.length - 1);
          final angle = parentAngle + offset;
          raw[siblings[i]] = Offset(cos(angle) * rawR2, sin(angle) * rawR2);
        }
      }
    }

    // --- 2. Auto-fit the unit cloud into the real canvas --------------------
    return _fit(raw, size);
  }

  /// Scale + translate the unit-space [raw] positions to fill [size] while
  /// leaving a margin for node discs and their labels, then center the content
  /// cloud on the canvas.
  ///
  /// HOW: measure the raw bounding box; scale it to the largest factor that
  /// still fits inside the pane minus margins; cap that factor so a 1-2 node
  /// graph doesn't blow up (outer ring <= 42% of the shortest side); finally
  /// map the raw bbox center onto the canvas center.
  static EgoGraphLayout _fit(Map<int, Offset> raw, Size size) {
    if (raw.isEmpty) return const EgoGraphLayout(positions: {}, nodeRadius: 28);

    var minX = double.infinity, minY = double.infinity;
    var maxX = -double.infinity, maxY = -double.infinity, maxR = 0.0;
    raw.forEach((_, p) {
      minX = min(minX, p.dx);
      maxX = max(maxX, p.dx);
      minY = min(minY, p.dy);
      maxY = max(maxY, p.dy);
      maxR = max(maxR, p.distance);
    });
    final rawW = max(maxX - minX, 1e-6);
    final rawH = max(maxY - minY, 1e-6);
    final rawCenter = Offset((minX + maxX) / 2, (minY + maxY) / 2);

    // Margins reserve room for node discs (radius up to 28) + name labels drawn
    // below them; proportional to the pane so wide/tall panes breathe.
    final marginX = max(80.0, size.width * 0.07);
    final marginY = max(80.0, size.height * 0.09);
    final availW = max(size.width - 2 * marginX, 50.0);
    final availH = max(size.height - 2 * marginY, 50.0);

    var scale = min(availW / rawW, availH / rawH);
    if (maxR > 0) {
      // Don't let a tiny graph expand past 42% of the shortest side.
      scale = min(scale, 0.42 * size.shortestSide / maxR);
    }

    final canvasCenter = Offset(size.width / 2, size.height / 2);
    final positions = <int, Offset>{};
    raw.forEach((id, p) {
      positions[id] = canvasCenter + (p - rawCenter) * scale;
    });
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
      fontSize: 10,
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

      // Base well outward of the midpoint (0.62) so labels pull OUT of the
      // convergence zone near the ego center where every edge meets — that zone
      // is where relation labels used to pile up. Then a collision-aware nudge.
      final dir = p2 - p1;
      final len = dir.distance;
      final unit = len < 1 ? const Offset(1, 0) : dir / len;
      final base = p1 + dir * 0.62;
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
      fontSize: isCenter ? 13 : node.depth == 1 ? 12 : 11,
      color: isCenter ? colors.onSurface : colors.onSurfaceVariant,
      fontWeight: isCenter ? FontWeight.w600 : FontWeight.w400,
    );
    return TextPainter(
      text: TextSpan(text: node.name, style: style),
      textDirection: TextDirection.ltr,
      maxLines: 2,
      ellipsis: '…',
    )..layout(maxWidth: isCenter ? 130.0 : 100.0);
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
  /// capped (~≤40px along, ≤26px perp) so labels stay tied to their edge while
  /// having enough room to escape the dense center annulus.
  Offset _placeLabel(Offset base, Size sz, Offset unit, Offset perp, List<Rect> placed) {
    const along = [0.0, -14.0, 14.0, -28.0, 28.0, -40.0, 40.0];
    const cross = [0.0, 9.0, -9.0, 18.0, -18.0, 26.0, -26.0];
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

