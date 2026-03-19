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
// Civ tint colors (cycled by civ index)
// ---------------------------------------------------------------------------

const _civTints = [
  Color(0x55E53935), // red
  Color(0x551E88E5), // blue
  Color(0x5543A047), // green
  Color(0x55FB8C00), // orange
  Color(0x558E24AA), // purple
  Color(0x5500ACC1), // cyan
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
        _civIndex[c.civName!] = idx++ % _civTints.length;
      }
    }
  }

  @override
  void paint(Canvas canvas, Size size) {
    // Build a fast lookup: (q,r) → cell
    final cellMap = <({int q, int r}), MapCellWithDetails>{};
    for (final c in cells) {
      cellMap[(q: c.cell.q, r: c.cell.r)] = c;
    }

    final terrainPaint = Paint()..style = PaintingStyle.fill;
    final civPaint = Paint()..style = PaintingStyle.fill;
    final borderPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.8
      ..color = Colors.black26;
    final selectedPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5
      ..color = Colors.white;

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

        // Overlay civ tint
        if (civName != null) {
          final tintIdx = _civIndex[civName] ?? 0;
          civPaint.color = _civTints[tintIdx];
          canvas.drawPath(path, civPaint);
        }

        // Grid border
        canvas.drawPath(path, borderPaint);

        // Selection highlight
        if (isSelected) {
          canvas.drawPath(path, selectedPaint);
        }

        // Label text (clipped to cell)
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
