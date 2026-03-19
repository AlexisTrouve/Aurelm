import 'dart:math';

import 'package:flutter/material.dart';

import '../map_drag_types.dart';
import 'grid_painter.dart';

/// Single drop overlay — one DragTarget<Object> per cell, handles both
/// asset drops (MapAssetDrag) and pawn moves (MapPawnDrag) without conflict.
class CellDropOverlay extends StatelessWidget {
  final String gridType;
  final int gridCols;
  final int gridRows;
  final double cellSize;
  final double canvasW;
  final double canvasH;

  /// Called when an asset is dropped on a cell.
  final void Function(int assetId, int q, int r) onAssetDrop;

  /// Called when a pawn is dropped on a cell.
  final void Function(int pawnId, int q, int r) onPawnDrop;

  const CellDropOverlay({
    super.key,
    required this.gridType,
    required this.gridCols,
    required this.gridRows,
    required this.cellSize,
    required this.canvasW,
    required this.canvasH,
    required this.onAssetDrop,
    required this.onPawnDrop,
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
      center = Offset(q * cellSize + cellSize / 2, r * cellSize + cellSize / 2);
    }

    final hitR = cellSize * 0.85;

    return Positioned(
      left: center.dx - hitR,
      top: center.dy - hitR,
      width: hitR * 2,
      height: hitR * 2,
      child: DragTarget<Object>(
        // Only accept known drag types — rejects everything else
        onWillAcceptWithDetails: (details) =>
            details.data is MapAssetDrag || details.data is MapPawnDrag,
        onAcceptWithDetails: (details) {
          final data = details.data;
          if (data is MapAssetDrag) {
            onAssetDrop(data.assetId, q, r);
          } else if (data is MapPawnDrag) {
            onPawnDrop(data.pawnId, q, r);
          }
        },
        builder: (ctx, candidateData, rejectedData) {
          final isHovered = candidateData.isNotEmpty;
          final isPawn = isHovered && candidateData.first is MapPawnDrag;
          return Container(
            decoration: isHovered
                ? BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isPawn
                          ? Colors.amber.withValues(alpha: 0.9)
                          : Colors.blue.withValues(alpha: 0.7),
                      width: 2,
                    ),
                    color: isPawn
                        ? Colors.amber.withValues(alpha: 0.12)
                        : Colors.blue.withValues(alpha: 0.10),
                  )
                : null,
          );
        },
      ),
    );
  }
}
