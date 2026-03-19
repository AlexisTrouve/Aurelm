import 'dart:math';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/database.dart';
import '../../../providers/database_provider.dart';
import '../../../providers/map_provider.dart';
import '../map_drag_types.dart';

// ---------------------------------------------------------------------------
// Slot layout — offsets as fractions of cellSize from cell center.
// Index in outer list = (iconCount - 1), inner list = per-slot (dx, dy).
// ---------------------------------------------------------------------------

const _slots = [
  // 1 icon
  [(0.0, 0.0)],
  // 2 icons
  [(-0.28, 0.0), (0.28, 0.0)],
  // 3 icons
  [(0.0, -0.28), (-0.26, 0.20), (0.26, 0.20)],
  // 4 icons
  [(-0.26, -0.24), (0.26, -0.24), (-0.26, 0.24), (0.26, 0.24)],
  // 5 icons
  [(-0.28, -0.22), (0.28, -0.22), (0.0, 0.0), (-0.28, 0.22), (0.28, 0.22)],
  // 6 icons
  [
    (-0.28, -0.22), (0.0, -0.22), (0.28, -0.22),
    (-0.28,  0.22), (0.0,  0.22), (0.28,  0.22),
  ],
  // 7 icons
  [
    (-0.28, -0.28), (0.0, -0.28), (0.28, -0.28),
    (-0.28,  0.0 ), (0.28,  0.0),
    (-0.14,  0.28), (0.14,  0.28),
  ],
];

// ---------------------------------------------------------------------------
// Overlay widget
// ---------------------------------------------------------------------------

/// Stacks image widgets on top of the grid canvas for each cell's assets.
/// Must be inside the same InteractiveViewer as the canvas to zoom correctly.
class CellAssetsOverlay extends ConsumerWidget {
  final int mapId;
  final String gridType;
  final int gridCols;
  final int gridRows;
  final double cellSize;
  final double canvasW;
  final double canvasH;

  const CellAssetsOverlay({
    super.key,
    required this.mapId,
    required this.gridType,
    required this.gridCols,
    required this.gridRows,
    required this.cellSize,
    required this.canvasW,
    required this.canvasH,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final placementsAsync = ref.watch(mapCellAssetsProvider(mapId));
    final assetsAsync = ref.watch(allAssetsProvider);

    return placementsAsync.when(
      data: (placements) => assetsAsync.when(
        data: (assets) {
          // Build fast lookup: asset_id → bytes
          final assetBytes = <int, Uint8List>{
            for (final a in assets) a.id: a.data,
          };

          // Group placements by cell
          final byCell = <({int q, int r}), List<MapCellAssetRow>>{};
          for (final p in placements) {
            final key = (q: p.q, r: p.r);
            byCell.putIfAbsent(key, () => []).add(p);
          }

          return SizedBox(
            width: canvasW,
            height: canvasH,
            child: Stack(
              children: [
                for (final entry in byCell.entries)
                  ..._buildCellIcons(
                    entry.key,
                    entry.value,
                    assetBytes,
                  ),
              ],
            ),
          );
        },
        loading: () => const SizedBox.shrink(),
        error: (_, __) => const SizedBox.shrink(),
      ),
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
    );
  }

  List<Widget> _buildCellIcons(
    ({int q, int r}) coord,
    List<MapCellAssetRow> placements,
    Map<int, Uint8List> assetBytes,
  ) {
    // Cell center in canvas pixels
    final Offset center;
    if (gridType == 'hex') {
      center = Offset(
        cellSize * sqrt(3) * (coord.q + (coord.r % 2) * 0.5),
        cellSize * 1.5 * coord.r,
      );
    } else {
      center = Offset(
        coord.q * cellSize + cellSize / 2,
        coord.r * cellSize + cellSize / 2,
      );
    }

    final count = placements.length.clamp(1, 7);
    // Icon size: bigger base, shrinks as count grows to keep all icons in cell
    final iconSize = cellSize * (count == 1 ? 0.80 : count <= 2 ? 0.62 : count <= 4 ? 0.50 : 0.38);
    final slotDefs = _slots[count - 1];

    final widgets = <Widget>[];
    for (int i = 0; i < placements.length; i++) {
      final p = placements[i];
      final bytes = assetBytes[p.assetId];
      if (bytes == null) continue;

      final slotFrac = i < slotDefs.length ? slotDefs[i] : (0.0, 0.0);
      final dx = slotFrac.$1 * cellSize * 2;
      final dy = slotFrac.$2 * cellSize * 2;

      final left = center.dx + dx - iconSize / 2;
      final top = center.dy + dy - iconSize / 2;

      widgets.add(
        Positioned(
          left: left,
          top: top,
          width: iconSize,
          height: iconSize,
          child: Image.memory(
            bytes,
            fit: BoxFit.contain,
            gaplessPlayback: true,
          ),
        ),
      );
    }
    return widgets;
  }
}

// ---------------------------------------------------------------------------
// DragTarget overlay — invisible targets on every cell for asset drops
// ---------------------------------------------------------------------------

/// Transparent overlay that covers each cell with a [DragTarget<int>].
/// When an asset is dropped, calls [onDrop] with (assetId, q, r).
class CellDragTargetOverlay extends StatelessWidget {
  final String gridType;
  final int gridCols;
  final int gridRows;
  final double cellSize;
  final double canvasW;
  final double canvasH;
  final void Function(int assetId, int q, int r) onDrop;

  const CellDragTargetOverlay({
    super.key,
    required this.gridType,
    required this.gridCols,
    required this.gridRows,
    required this.cellSize,
    required this.canvasW,
    required this.canvasH,
    required this.onDrop,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: canvasW,
      height: canvasH,
      child: Stack(
        children: [
          for (int r = 0; r < gridRows; r++)
            for (int q = 0; q < gridCols; q++)
              _buildTarget(q, r),
        ],
      ),
    );
  }

  Widget _buildTarget(int q, int r) {
    final Offset center;
    if (gridType == 'hex') {
      center = Offset(
        cellSize * sqrt(3) * (q + (r % 2) * 0.5),
        cellSize * 1.5 * r,
      );
    } else {
      center = Offset(
        q * cellSize + cellSize / 2,
        r * cellSize + cellSize / 2,
      );
    }

    // Hit area = cell inscribed circle
    final hitR = cellSize * 0.85;

    return Positioned(
      left: center.dx - hitR,
      top: center.dy - hitR,
      width: hitR * 2,
      height: hitR * 2,
      child: DragTarget<MapAssetDrag>(
        onAcceptWithDetails: (details) =>
            onDrop(details.data.assetId, q, r),
        builder: (ctx, candidateData, _) {
          // Subtle highlight when an asset is hovering over this cell
          final isHovered = candidateData.isNotEmpty;
          return Container(
            decoration: isHovered
                ? BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                        color: Colors.white.withOpacity(0.8), width: 2),
                    color: Colors.white.withOpacity(0.15),
                  )
                : null,
          );
        },
      ),
    );
  }
}
