// Pure-layout tests for the ego-graph — no app pump, no DB, no sqlite DLL.
//
// WHAT: exercises `EgoGraphLayout.compute`, the deterministic radial layout math
// behind the graph screen's CustomPainter. Because it's a pure function
// (Size + GraphData -> node positions), we can prove its geometric invariants
// directly, which is the cheapest honest proof of the "graph polish" work.
//
// WHY these invariants: the pre-polish layout used fixed radius caps (220/340px)
// with the ego pinned at the canvas centre. On a wide pane that left large dead
// margins (the graph never grew to use the space); on a small pane the outer
// ring clipped past the edges. The polish replaces the caps with an auto-fit
// (scale + centre-on-content), mirroring the headless exporter's set_xlim/ylim.
// These tests lock BOTH ends: fill the space when there's room, shrink to fit
// when there isn't — and stay deterministic (no physics, no randomness).
import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:aurelm_gui/models/graph_data.dart';
import 'package:aurelm_gui/screens/graph/widgets/ego_painter.dart';

/// Builds a star hub: one centre (id 0) + [directNeighbors] depth-1 nodes, each
/// wired to the centre by an edge. Optionally [depth2Each] extended nodes hang
/// off every depth-1 node. IDs are deterministic so assertions are stable.
GraphData _hub(int directNeighbors, {int depth2Each = 0}) {
  final nodes = <GraphNode>[
    const GraphNode(id: 0, name: 'Centre', entityType: 'civilization', mentionCount: 14, depth: 0),
  ];
  final edges = <GraphEdge>[];
  var nextId = 1;
  for (var i = 0; i < directNeighbors; i++) {
    final d1 = nextId++;
    nodes.add(GraphNode(id: d1, name: 'Voisin $d1', entityType: 'person', mentionCount: 3, depth: 1));
    edges.add(GraphEdge(sourceId: 0, targetId: d1, relationType: 'allied_with'));
    for (var j = 0; j < depth2Each; j++) {
      final d2 = nextId++;
      nodes.add(GraphNode(id: d2, name: 'Loin $d2', entityType: 'place', mentionCount: 1, depth: 2));
      edges.add(GraphEdge(sourceId: d1, targetId: d2, relationType: 'located_in'));
    }
  }
  return GraphData(nodes: nodes, edges: edges, centerId: 0);
}

/// Axis-aligned bounding box over the laid-out node centres.
Rect _bbox(EgoGraphLayout layout) {
  var minX = double.infinity, minY = double.infinity;
  var maxX = -double.infinity, maxY = -double.infinity;
  for (final p in layout.positions.values) {
    minX = math.min(minX, p.dx);
    maxX = math.max(maxX, p.dx);
    minY = math.min(minY, p.dy);
    maxY = math.max(maxY, p.dy);
  }
  return Rect.fromLTRB(minX, minY, maxX, maxY);
}

void main() {
  group('EgoGraphLayout auto-fit', () {
    test('fills a wide pane instead of leaving dead margins', () {
      // A 12-neighbour hub on a large pane. The old fixed 340px outer-ring cap
      // let the graph span only ~680px here, marooned in the middle. Auto-fit
      // must grow it to use a solid fraction of the pane.
      const size = Size(1400, 1000);
      final layout = EgoGraphLayout.compute(size, _hub(12));
      final box = _bbox(layout);
      final shortest = size.shortestSide; // 1000
      // Span at least 72% of the shortest side on at least one axis.
      final spanFrac = math.max(box.width, box.height) / shortest;
      expect(spanFrac, greaterThanOrEqualTo(0.72),
          reason: 'graph should fill the pane, not sit tiny in the centre '
              '(got ${(spanFrac * 100).toStringAsFixed(0)}%)');
    });

    test('shrinks so a dense hub never clips past a small pane', () {
      // 18 neighbours + extended ring on a small pane. The old layout put the
      // outer ring at a fixed radius that overflowed the top/bottom edges.
      const size = Size(640, 480);
      final layout = EgoGraphLayout.compute(size, _hub(18, depth2Each: 1));
      const inset = 30.0; // node centres must stay this far inside every edge
      for (final entry in layout.positions.entries) {
        final p = entry.value;
        expect(p.dx, inInclusiveRange(inset, size.width - inset),
            reason: 'node ${entry.key} X clips the pane');
        expect(p.dy, inInclusiveRange(inset, size.height - inset),
            reason: 'node ${entry.key} Y clips the pane');
      }
    });

    test('centres the content cloud on the canvas', () {
      const size = Size(1200, 800);
      final layout = EgoGraphLayout.compute(size, _hub(8, depth2Each: 2));
      final box = _bbox(layout);
      // Content centre within 6% of the canvas centre on each axis.
      expect((box.center.dx - size.width / 2).abs(), lessThan(size.width * 0.06));
      expect((box.center.dy - size.height / 2).abs(), lessThan(size.height * 0.06));
    });

    test('is deterministic — same input, identical positions', () {
      const size = Size(900, 700);
      final data = _hub(10, depth2Each: 1);
      final a = EgoGraphLayout.compute(size, data).positions;
      final b = EgoGraphLayout.compute(size, data).positions;
      expect(a.length, b.length);
      for (final id in a.keys) {
        expect(a[id], b[id], reason: 'position for $id must be stable');
      }
    });

    test('places every node and keeps the centre node', () {
      const size = Size(1000, 800);
      final data = _hub(6, depth2Each: 2);
      final layout = EgoGraphLayout.compute(size, data);
      expect(layout.positions.length, data.nodes.length);
      expect(layout.positions.containsKey(0), isTrue);
    });

    test('empty graph yields no positions', () {
      final layout = EgoGraphLayout.compute(const Size(800, 600), GraphData.empty);
      expect(layout.positions, isEmpty);
    });
  });
}
