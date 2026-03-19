import 'dart:math';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../data/database.dart';
import '../../../models/map_pawn_with_details.dart';
import '../../../providers/database_provider.dart';
import '../../../providers/map_provider.dart';

// Entity type → badge border color
const _typeColors = {
  'person':       Color(0xFFE57373),
  'civilization': Color(0xFF64B5F6),
  'institution':  Color(0xFFFFD54F),
  'place':        Color(0xFF81C784),
  'technology':   Color(0xFF4DD0E1),
  'resource':     Color(0xFFA1887F),
  'creature':     Color(0xFFCE93D8),
  'event':        Color(0xFFFF8A65),
  'caste':        Color(0xFFB0BEC5),
  'belief':       Color(0xFFF48FB1),
};

Color _typeColor(String type) =>
    _typeColors[type] ?? const Color(0xFF90A4AE);

/// Overlay that renders draggable pawn tokens on top of the map canvas.
/// Long-press a pawn to drag it to a new cell.
/// Tap a pawn to navigate to its entity detail screen.
class PawnsOverlay extends ConsumerWidget {
  final int mapId;
  final String gridType;
  final int gridCols;
  final int gridRows;
  final double cellSize;
  final double canvasW;
  final double canvasH;

  const PawnsOverlay({
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
    final pawnsAsync = ref.watch(mapPawnsProvider(mapId));
    final assetsAsync = ref.watch(allAssetsProvider);

    return pawnsAsync.when(
      data: (pawns) {
        // Build asset lookup id → bytes
        final assetBytes = <int, Uint8List>{};
        for (final a in assetsAsync.valueOrNull ?? []) {
          assetBytes[a.id] = a.data;
        }

        // We need entity info — query synchronously via db
        final db = ref.read(databaseProvider);

        return FutureBuilder<List<MapPawnWithDetails>>(
          future: _enrichPawns(pawns, assetBytes, db),
          builder: (ctx, snap) {
            final details = snap.data ?? [];
            return SizedBox(
              width: canvasW,
              height: canvasH,
              child: Stack(
                children: details
                    .map((d) => _PawnToken(
                          detail: d,
                          gridType: gridType,
                          cellSize: cellSize,
                          canvasW: canvasW,
                          canvasH: canvasH,
                          onMove: (q, r) async {
                            await db?.mapDao
                                .movePawn(d.pawn.id, q, r);
                          },
                          onTap: () =>
                              context.push('/entities/${d.pawn.entityId}'),
                          onRemove: () =>
                              db?.mapDao.removePawn(d.pawn.id),
                        ))
                    .toList(),
              ),
            );
          },
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
    );
  }

  Future<List<MapPawnWithDetails>> _enrichPawns(
    List<MapPawnRow> pawns,
    Map<int, Uint8List> assetBytes,
    AurelmDatabase? db,
  ) async {
    if (db == null || pawns.isEmpty) return [];

    // Fetch all entities needed in one query
    final entityIds = pawns.map((p) => p.entityId).toSet().toList();
    final entities = await db.entityDao.getEntitiesByIds(entityIds);
    final entityMap = {for (final e in entities) e.id: e};

    return pawns.map((p) {
      final entity = entityMap[p.entityId];
      return MapPawnWithDetails(
        pawn: p,
        entityName: entity?.canonicalName ?? '?',
        entityType: entity?.entityType ?? 'person',
        assetBytes:
            p.assetId != null ? assetBytes[p.assetId!] : null,
      );
    }).toList();
  }

  Offset _cellCenter(int q, int r) {
    if (gridType == 'hex') {
      return Offset(
        cellSize * sqrt(3) * (q + (r % 2) * 0.5),
        cellSize * 1.5 * r,
      );
    }
    return Offset(q * cellSize + cellSize / 2, r * cellSize + cellSize / 2);
  }
}

// ---------------------------------------------------------------------------
// Single pawn token widget
// ---------------------------------------------------------------------------

class _PawnToken extends StatelessWidget {
  final MapPawnWithDetails detail;
  final String gridType;
  final double cellSize;
  final double canvasW;
  final double canvasH;
  final void Function(int q, int r) onMove;
  final VoidCallback onTap;
  final VoidCallback onRemove;

  const _PawnToken({
    required this.detail,
    required this.gridType,
    required this.cellSize,
    required this.canvasW,
    required this.canvasH,
    required this.onMove,
    required this.onTap,
    required this.onRemove,
  });

  Offset _center() {
    final q = detail.pawn.q;
    final r = detail.pawn.r;
    if (gridType == 'hex') {
      return Offset(
        cellSize * sqrt(3) * (q + (r % 2) * 0.5),
        cellSize * 1.5 * r,
      );
    }
    return Offset(q * cellSize + cellSize / 2, r * cellSize + cellSize / 2);
  }

  @override
  Widget build(BuildContext context) {
    final center = _center();
    final size = (cellSize * 0.55).clamp(20.0, 48.0);
    final color = _typeColor(detail.entityType);

    final badge = _PawnBadge(
      detail: detail,
      size: size,
      color: color,
    );

    return Positioned(
      left: center.dx - size / 2,
      // Offset slightly upward so pawn sits "above" the cell center
      top: center.dy - size / 2 - cellSize * 0.12,
      child: GestureDetector(
        onTap: onTap,
        onSecondaryTap: () => _showContextMenu(context, center),
        child: LongPressDraggable<int>(
          data: detail.pawn.id,
          feedback: Material(
            elevation: 6,
            shape: const CircleBorder(),
            child: _PawnBadge(detail: detail, size: size * 1.2, color: color),
          ),
          childWhenDragging: Opacity(opacity: 0.3, child: badge),
          child: badge,
        ),
      ),
    );
  }

  Future<void> _showContextMenu(BuildContext context, Offset center) async {
    final result = await showMenu<String>(
      context: context,
      position: RelativeRect.fromLTRB(
        center.dx, center.dy, center.dx + 1, center.dy + 1),
      items: [
        PopupMenuItem(
          value: 'detail',
          child: Row(children: [
            const Icon(Icons.info_outline, size: 16),
            const SizedBox(width: 8),
            Text(detail.entityName),
          ]),
        ),
        const PopupMenuItem(
          value: 'remove',
          child: Row(children: [
            Icon(Icons.remove_circle_outline, size: 16, color: Colors.red),
            SizedBox(width: 8),
            Text('Retirer du terrain', style: TextStyle(color: Colors.red)),
          ]),
        ),
      ],
    );
    if (result == 'detail') onTap();
    if (result == 'remove') onRemove();
  }
}

class _PawnBadge extends StatelessWidget {
  final MapPawnWithDetails detail;
  final double size;
  final Color color;

  const _PawnBadge(
      {required this.detail, required this.size, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.grey[900],
        border: Border.all(color: color, width: 2.5),
        boxShadow: const [
          BoxShadow(blurRadius: 4, spreadRadius: 0.5,
              color: Colors.black54, offset: Offset(0, 2)),
        ],
      ),
      child: ClipOval(
        child: detail.assetBytes != null
            ? Image.memory(
                Uint8List.fromList(detail.assetBytes!),
                fit: BoxFit.cover,
                gaplessPlayback: true,
              )
            : Center(
                child: Text(
                  detail.initial,
                  style: TextStyle(
                    fontSize: size * 0.42,
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
              ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Drop target overlay for pawn moves
// ---------------------------------------------------------------------------

/// Invisible DragTarget<int> overlay to receive pawn drops.
/// Separate from asset targets — listens for pawn ids.
class PawnDragTargetOverlay extends ConsumerWidget {
  final int mapId;
  final String gridType;
  final int gridCols;
  final int gridRows;
  final double cellSize;
  final double canvasW;
  final double canvasH;

  const PawnDragTargetOverlay({
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
    final db = ref.read(databaseProvider);

    return SizedBox(
      width: canvasW,
      height: canvasH,
      child: Stack(
        children: [
          for (int r = 0; r < gridRows; r++)
            for (int q = 0; q < gridCols; q++)
              _buildTarget(q, r, db),
        ],
      ),
    );
  }

  Widget _buildTarget(int q, int r, AurelmDatabase? db) {
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
      child: DragTarget<int>(
        onAcceptWithDetails: (details) async {
          await db?.mapDao.movePawn(details.data, q, r);
        },
        builder: (ctx, candidateData, _) {
          final isHovered = candidateData.isNotEmpty;
          return Container(
            decoration: isHovered
                ? BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                        color: Colors.amber.withOpacity(0.9), width: 2),
                    color: Colors.amber.withOpacity(0.12),
                  )
                : null,
          );
        },
      ),
    );
  }
}
