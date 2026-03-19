import 'dart:math';

import 'package:flutter/material.dart';

import '../../../models/map_with_details.dart';

// ---------------------------------------------------------------------------
// Terrain → color palette
// ---------------------------------------------------------------------------

const _terrainColors = {
  'plain':    Color(0xFF8BC34A),
  'forest':   Color(0xFF388E3C),
  'mountain': Color(0xFF9E9E9E),
  'coast':    Color(0xFF80DEEA),
  'sea':      Color(0xFF1565C0),
  'desert':   Color(0xFFFFD54F),
  'swamp':    Color(0xFF558B2F),
};

Color _terrainColor(String type) =>
    _terrainColors[type] ?? const Color(0xFF616161);

// ---------------------------------------------------------------------------
// Civ border colors (solid, cycled by civ index)
// ---------------------------------------------------------------------------

const _civColors = [
  Color(0xFFE53935), // red
  Color(0xFF1E88E5), // blue
  Color(0xFF43A047), // green
  Color(0xFFFB8C00), // orange
  Color(0xFF8E24AA), // purple
  Color(0xFF00ACC1), // cyan
];

// ---------------------------------------------------------------------------
// GridPainter
// ---------------------------------------------------------------------------

/// CustomPainter that draws a hex (pointy-top) or square grid over [cells].
/// Selected cell is highlighted with a white border.
class GridPainter extends CustomPainter {
  final List<MapCellWithDetails> cells;
  final String gridType; // 'hex' | 'square'
  final int gridCols;
  final int gridRows;
  final double cellSize; // hex: size = outer radius; square: side length
  final ({int q, int r})? selectedCell;

  /// Maps civ name → tint index so each civ gets a consistent overlay color.
  final Map<String, int> _civIndex = {};

  GridPainter({
    required this.cells,
    required this.gridType,
    required this.gridCols,
    required this.gridRows,
    required this.cellSize,
    this.selectedCell,
  }) {
    // Pre-assign tint indices for all civs encountered in cells
    int idx = 0;
    for (final c in cells) {
      if (c.civName != null && !_civIndex.containsKey(c.civName)) {
        _civIndex[c.civName!] = idx++ % _civColors.length;
      }
    }
  }

  @override
  void paint(Canvas canvas, Size size) {
    // Build a fast lookup: (q,r) → civName
    final cellMap = <({int q, int r}), MapCellWithDetails>{};
    for (final c in cells) {
      cellMap[(q: c.cell.q, r: c.cell.r)] = c;
    }

    final terrainPaint = Paint()..style = PaintingStyle.fill;
    final borderPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.8
      ..color = Colors.black26;
    final selectedPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5
      ..color = Colors.white;
    // Civ border: thick stroke on exterior edges only
    final civBorderPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final labelStyle = TextStyle(
      fontSize: cellSize * 0.22,
      color: Colors.white,
      shadows: const [Shadow(blurRadius: 2, color: Colors.black54)],
    );

    for (int r = 0; r < gridRows; r++) {
      for (int q = 0; q < gridCols; q++) {
        final key = (q: q, r: r);
        final detail = cellMap[key];
        final terrain = detail?.cell.terrainType ?? 'plain';
        final civName = detail?.civName;
        final label = detail?.cell.label;
        final isSelected = selectedCell?.q == q && selectedCell?.r == r;

        final path = gridType == 'hex'
            ? _hexPath(q, r, cellSize)
            : _squarePath(q, r, cellSize);

        // Fill terrain color
        terrainPaint.color = _terrainColor(terrain);
        canvas.drawPath(path, terrainPaint);

        // Grid border
        canvas.drawPath(path, borderPaint);

        // Civ territory border — only on exterior edges
        if (civName != null) {
          final civIdx = _civIndex[civName] ?? 0;
          final civColor = _civColors[civIdx % _civColors.length];
          civBorderPaint
            ..color = civColor
            ..strokeWidth = (cellSize * 0.18).clamp(2.0, 8.0);

          final edgePath = gridType == 'hex'
              ? _hexExteriorEdges(q, r, cellSize, civName, cellMap)
              : _squareExteriorEdges(q, r, cellSize, civName, cellMap);

          if (edgePath != null) {
            canvas.drawPath(edgePath, civBorderPaint);
          }
        }

        // Selection highlight
        if (isSelected) {
          canvas.drawPath(path, selectedPaint);
        }

        // Label text
        if (label != null && label.isNotEmpty) {
          final center = gridType == 'hex'
              ? _hexCenter(q, r, cellSize)
              : _squareCenter(q, r, cellSize);
          _drawLabel(canvas, label, center, labelStyle);
        }
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Exterior edge helpers
  // ---------------------------------------------------------------------------

  /// Returns a Path containing only the edges of hex (q,r) that border a cell
  /// with a different civ (or no civ).  Returns null if all edges are interior.
  Path? _hexExteriorEdges(
    int q,
    int r,
    double size,
    String civName,
    Map<({int q, int r}), MapCellWithDetails> cellMap,
  ) {
    // Pointy-top hex: 6 neighbours in odd-r offset coordinates.
    // Each neighbour corresponds to an edge between corner i and i+1.
    final neighbors = _hexNeighbors(q, r);
    final center = _hexCenter(q, r, size);

    // Pre-compute the 6 corner points
    final corners = List.generate(6, (i) {
      final angle = (pi / 180) * (60 * i - 30);
      return Offset(center.dx + size * cos(angle),
                    center.dy + size * sin(angle));
    });

    final path = Path();
    bool hasEdge = false;

    for (int i = 0; i < 6; i++) {
      final nb = neighbors[i];
      final nbCiv = nb != null ? cellMap[nb]?.civName : null;
      if (nbCiv != civName) {
        // Exterior edge — draw from corner i to corner (i+1)%6
        final a = corners[i];
        final b = corners[(i + 1) % 6];
        path.moveTo(a.dx, a.dy);
        path.lineTo(b.dx, b.dy);
        hasEdge = true;
      }
    }
    return hasEdge ? path : null;
  }

  /// Hex neighbours in odd-r offset coordinates.
  /// Returns a list of 6 nullable coords (null if out of bounds),
  /// indexed by edge: [0]=NE, [1]=E, [2]=SE, [3]=SW, [4]=W, [5]=NW.
  List<({int q, int r})?> _hexNeighbors(int q, int r) {
    // Odd-r offset: parity-dependent neighbour offsets
    final parity = r % 2; // 0 = even row, 1 = odd row
    final offsets = parity == 0
        ? const [
            (dq:  0, dr: -1), // NE (edge 0: corner 0→1)
            (dq:  1, dr:  0), // E  (edge 1: corner 1→2)
            (dq:  0, dr:  1), // SE (edge 2: corner 2→3)
            (dq: -1, dr:  1), // SW (edge 3: corner 3→4)
            (dq: -1, dr:  0), // W  (edge 4: corner 4→5)
            (dq: -1, dr: -1), // NW (edge 5: corner 5→0)
          ]
        : const [
            (dq:  1, dr: -1),
            (dq:  1, dr:  0),
            (dq:  1, dr:  1),
            (dq:  0, dr:  1),
            (dq: -1, dr:  0),
            (dq:  0, dr: -1),
          ];

    return offsets.map((o) {
      final nq = q + o.dq;
      final nr = r + o.dr;
      if (nq < 0 || nq >= gridCols || nr < 0 || nr >= gridRows) return null;
      return (q: nq, r: nr);
    }).toList();
  }

  /// Returns exterior edges path for a square cell.
  Path? _squareExteriorEdges(
    int q,
    int r,
    double size,
    String civName,
    Map<({int q, int r}), MapCellWithDetails> cellMap,
  ) {
    // 4 neighbours: top, right, bottom, left
    final neighbors = [
      (q: q,   r: r-1), // top
      (q: q+1, r: r  ), // right
      (q: q,   r: r+1), // bottom
      (q: q-1, r: r  ), // left
    ];
    final x = q * size;
    final y = r * size;
    // Corners: TL, TR, BR, BL
    final corners = [
      Offset(x,        y       ), // TL
      Offset(x + size, y       ), // TR
      Offset(x + size, y + size), // BR
      Offset(x,        y + size), // BL
    ];
    // Edge i goes from corner i to corner (i+1)%4
    // [0]=top(TL→TR), [1]=right(TR→BR), [2]=bottom(BR→BL), [3]=left(BL→TL)
    final path = Path();
    bool hasEdge = false;

    for (int i = 0; i < 4; i++) {
      final nb = neighbors[i];
      final nbCiv = (nb.q >= 0 && nb.q < gridCols && nb.r >= 0 && nb.r < gridRows)
          ? cellMap[(q: nb.q, r: nb.r)]?.civName
          : null;
      if (nbCiv != civName) {
        final a = corners[i];
        final b = corners[(i + 1) % 4];
        path.moveTo(a.dx, a.dy);
        path.lineTo(b.dx, b.dy);
        hasEdge = true;
      }
    }
    return hasEdge ? path : null;
  }

  // ---------------------------------------------------------------------------
  // Geometry — hex (pointy-top)
  // ---------------------------------------------------------------------------

  /// Center pixel of hex cell (q,r) — offset coordinates (odd-r).
  /// Even rows: no offset. Odd rows: shifted right by half a hex.
  /// This keeps columns visually straight (rectangular bounding box).
  Offset _hexCenter(int q, int r, double size) {
    final x = size * sqrt(3) * (q + (r % 2) * 0.5);
    final y = size * 1.5 * r;
    return Offset(x, y);
  }

  /// Hexagonal path for cell (q,r).
  Path _hexPath(int q, int r, double size) {
    final center = _hexCenter(q, r, size);
    final path = Path();
    for (int i = 0; i < 6; i++) {
      // Pointy-top: angle starts at -30°
      final angle = (pi / 180) * (60 * i - 30);
      final px = center.dx + size * cos(angle);
      final py = center.dy + size * sin(angle);
      if (i == 0) {
        path.moveTo(px, py);
      } else {
        path.lineTo(px, py);
      }
    }
    path.close();
    return path;
  }

  // ---------------------------------------------------------------------------
  // Geometry — square
  // ---------------------------------------------------------------------------

  Offset _squareCenter(int q, int r, double size) =>
      Offset(q * size + size / 2, r * size + size / 2);

  Path _squarePath(int q, int r, double size) {
    return Path()
      ..addRect(Rect.fromLTWH(q * size, r * size, size, size));
  }

  // ---------------------------------------------------------------------------
  // Label drawing
  // ---------------------------------------------------------------------------

  void _drawLabel(Canvas canvas, String text, Offset center, TextStyle style) {
    final tp = TextPainter(
      text: TextSpan(text: text, style: style),
      textDirection: TextDirection.ltr,
      maxLines: 1,
    )..layout(maxWidth: cellSize * 1.5);
    tp.paint(
      canvas,
      center - Offset(tp.width / 2, tp.height / 2),
    );
  }

  @override
  bool shouldRepaint(GridPainter old) =>
      old.cells != cells ||
      old.selectedCell != selectedCell ||
      old.cellSize != cellSize;

  // ---------------------------------------------------------------------------
  // Hit testing — inverse geometry for tap detection
  // ---------------------------------------------------------------------------

  /// Convert a local tap position to (q, r) grid coordinates.
  /// Returns null if outside the grid.
  static ({int q, int r})? coordAt(
    Offset localPos,
    String gridType,
    int gridCols,
    int gridRows,
    double cellSize,
  ) {
    if (gridType == 'square') {
      final q = (localPos.dx / cellSize).floor();
      final r = (localPos.dy / cellSize).floor();
      if (q < 0 || r < 0 || q >= gridCols || r >= gridRows) return null;
      return (q: q, r: r);
    }

    // Hex offset-coordinates (odd-r): invert the forward formula.
    // Forward: x = size*sqrt(3)*(q + (r%2)*0.5), y = size*1.5*r
    // From y: r_approx = y / (1.5 * size)  → round to get r
    // From x: q_approx = x / (sqrt(3)*size) - (r%2)*0.5
    final s = cellSize;
    final fracR = localPos.dy / (1.5 * s);
    final rr0 = fracR.round().clamp(0, gridRows - 1);
    final fracQ = localPos.dx / (sqrt(3) * s) - (rr0 % 2) * 0.5;
    // Cube coordinates
    final rq = fracQ.round().clamp(0, gridCols - 1);
    if (rq < 0 || rr0 < 0 || rq >= gridCols || rr0 >= gridRows) return null;
    return (q: rq, r: rr0);
  }
}
