import 'dart:io';

import 'package:drift/drift.dart' show Value;
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;

import '../../data/database.dart';
import '../../models/map_with_details.dart';
import '../../providers/database_provider.dart';
import '../../providers/map_provider.dart';
import '../../widgets/common/empty_state.dart';
import 'terrain_detector.dart';
import 'widgets/asset_panel.dart';
import 'widgets/cell_assets_overlay.dart';
import 'widgets/cell_editor_panel.dart';
import 'widgets/grid_painter.dart';
import 'widgets/pawns_overlay.dart';
import 'widgets/pawns_panel.dart';
import 'widgets/terrain_preview_dialog.dart';

// ---------------------------------------------------------------------------
// Map screen — 3-panel layout
// ---------------------------------------------------------------------------

class MapScreen extends ConsumerWidget {
  const MapScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dbPath = ref.watch(dbPathProvider);
    if (dbPath == null) {
      return const Scaffold(
        body: EmptyState(
          icon: Icons.storage,
          message: 'No database configured',
        ),
      );
    }

    final selectedMapId = ref.watch(selectedMapIdProvider);
    final selectedCell = ref.watch(selectedCellProvider);

    // Cells for the selected map
    final cellsAsync = selectedMapId != null
        ? ref.watch(mapCellsProvider(selectedMapId))
        : const AsyncValue<List<MapCellWithDetails>>.data([]);

    // Find the detail for the selected cell
    MapCellWithDetails? selectedCellDetail;
    if (selectedCell != null) {
      selectedCellDetail = cellsAsync.valueOrNull?.firstWhere(
        (c) => c.cell.q == selectedCell.q && c.cell.r == selectedCell.r,
        orElse: () => MapCellWithDetails(
          cell: MapCellRow(
            mapId: selectedMapId!,
            q: selectedCell.q,
            r: selectedCell.r,
            terrainType: 'plain',
            label: null,
            controllingCivId: null,
            entityId: null,
            childMapId: null,
            metadata: null,
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Cartes'),
        actions: [
          // New map button
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'Nouvelle carte',
            onPressed: () => _showCreateMapDialog(context, ref),
          ),
        ],
      ),
      body: Row(
        children: [
          // Left panel: tabbed (Cartes | Assets | Pions)
          SizedBox(
            width: 220,
            child: DefaultTabController(
              length: 3,
              child: Column(
                children: [
                  const TabBar(tabs: [
                    Tab(text: 'Cartes', icon: Icon(Icons.map_outlined, size: 14)),
                    Tab(text: 'Assets', icon: Icon(Icons.image_outlined, size: 14)),
                    Tab(text: 'Pions', icon: Icon(Icons.people_outline, size: 14)),
                  ]),
                  Expanded(
                    child: TabBarView(children: [
                      _MapSelectorPanel(selectedMapId: selectedMapId),
                      const AssetPanel(),
                      selectedMapId != null
                          ? PawnsPanel(mapId: selectedMapId)
                          : const Center(
                              child: Text('Sélectionne une carte',
                                  style: TextStyle(color: Colors.grey, fontSize: 12))),
                    ]),
                  ),
                ],
              ),
            ),
          ),
          const VerticalDivider(width: 1, thickness: 1),

          // Centre: canvas
          Expanded(
            child: selectedMapId == null
                ? const EmptyState(
                    icon: Icons.map_outlined,
                    message: 'Sélectionne une carte',
                  )
                : _MapCanvas(
                    mapId: selectedMapId,
                    cellsAsync: cellsAsync,
                  ),
          ),

          // Right panel: cell editor (visible only when a cell is selected)
          if (selectedCell != null && selectedMapId != null) ...[
            const VerticalDivider(width: 1, thickness: 1),
            CellEditorPanel(
              mapId: selectedMapId,
              coord: selectedCell,
              cellDetail: selectedCellDetail,
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _showCreateMapDialog(BuildContext context, WidgetRef ref) async {
    final db = ref.read(databaseProvider);
    if (db == null) return;

    String name = '';
    String gridType = 'hex';
    int cols = 20;
    int rows = 15;

    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDlg) => AlertDialog(
          title: const Text('Nouvelle carte'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                decoration: const InputDecoration(
                    labelText: 'Nom', border: OutlineInputBorder()),
                onChanged: (v) => name = v,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: gridType,
                decoration: const InputDecoration(
                    labelText: 'Grille', border: OutlineInputBorder()),
                items: const [
                  DropdownMenuItem(value: 'hex', child: Text('Hexagonale')),
                  DropdownMenuItem(value: 'square', child: Text('Carrée')),
                ],
                onChanged: (v) => setDlg(() => gridType = v ?? 'hex'),
              ),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(
                  child: TextField(
                    decoration: const InputDecoration(
                        labelText: 'Colonnes', border: OutlineInputBorder()),
                    keyboardType: TextInputType.number,
                    controller:
                        TextEditingController(text: cols.toString()),
                    onChanged: (v) =>
                        cols = int.tryParse(v) ?? cols,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    decoration: const InputDecoration(
                        labelText: 'Lignes', border: OutlineInputBorder()),
                    keyboardType: TextInputType.number,
                    controller:
                        TextEditingController(text: rows.toString()),
                    onChanged: (v) =>
                        rows = int.tryParse(v) ?? rows,
                  ),
                ),
              ]),
            ],
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Annuler')),
            FilledButton(
              onPressed: () async {
                if (name.trim().isEmpty) return;
                final now = DateTime.now().toIso8601String();
                final id = await db.mapDao.upsertMap(MapMapsCompanion(
                  name: Value(name.trim()),
                  gridType: Value(gridType),
                  gridCols: Value(cols),
                  gridRows: Value(rows),
                  createdAt: Value(now),
                ));
                ref.read(selectedMapIdProvider.notifier).state = id;
                if (ctx.mounted) Navigator.pop(ctx);
              },
              child: const Text('Créer'),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Left panel: map selector
// ---------------------------------------------------------------------------

class _MapSelectorPanel extends ConsumerWidget {
  final int? selectedMapId;
  const _MapSelectorPanel({required this.selectedMapId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mapsAsync = ref.watch(allMapsProvider);

    return mapsAsync.when(
      data: (maps) {
        if (maps.isEmpty) {
          return const EmptyState(
              icon: Icons.map_outlined, message: 'Aucune carte');
        }

        // Build hierarchy: root maps first, then children indented
        final roots = maps.where((m) => m.parentMapId == null).toList();
        final byParent = <int, List<MapRow>>{};
        for (final m in maps) {
          if (m.parentMapId != null) {
            byParent.putIfAbsent(m.parentMapId!, () => []).add(m);
          }
        }

        final items = <({MapRow map, int depth})>[];
        void addItems(List<MapRow> list, int depth) {
          for (final m in list) {
            items.add((map: m, depth: depth));
            if (byParent.containsKey(m.id)) {
              addItems(byParent[m.id]!, depth + 1);
            }
          }
        }
        addItems(roots, 0);

        return ListView.builder(
          itemCount: items.length,
          itemBuilder: (_, i) {
            final item = items[i];
            final isSelected = item.map.id == selectedMapId;
            return InkWell(
              onTap: () {
                ref.read(selectedMapIdProvider.notifier).state = item.map.id;
                ref.read(selectedCellProvider.notifier).state = null;
              },
              child: Container(
                color: isSelected
                    ? Theme.of(context).colorScheme.primaryContainer
                    : null,
                padding: EdgeInsets.only(
                  left: 12.0 + item.depth * 16,
                  right: 8,
                  top: 10,
                  bottom: 10,
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.map_outlined,
                      size: 16,
                      color: isSelected
                          ? Theme.of(context).colorScheme.primary
                          : null,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        item.map.name,
                        style: TextStyle(
                          fontWeight: isSelected
                              ? FontWeight.bold
                              : FontWeight.normal,
                          fontSize: 13,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Text(
                      '${item.map.gridCols}×${item.map.gridRows}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(child: Text('$err')),
    );
  }
}

// ---------------------------------------------------------------------------
// Centre: map canvas
// ---------------------------------------------------------------------------

class _MapCanvas extends ConsumerStatefulWidget {
  final int mapId;
  final AsyncValue<List<MapCellWithDetails>> cellsAsync;
  const _MapCanvas({required this.mapId, required this.cellsAsync});

  @override
  ConsumerState<_MapCanvas> createState() => _MapCanvasState();
}

class _MapCanvasState extends ConsumerState<_MapCanvas> {
  // Cell size drives grid rendering resolution (toolbar slider)
  double _cellSize = 30.0;

  // InteractiveViewer transform controller — allows programmatic pan/zoom
  final _transformCtrl = TransformationController();

  // Focus node to capture keyboard events on the canvas area
  final _focusNode = FocusNode();

  // Canvas units moved per key press (before scale factor).
  // Actual screen-space movement = _panStep * currentScale, so the amount
  // of canvas terrain covered per key press stays constant regardless of zoom.
  static const _panStep = 40.0;
  // Zoom factor per A/E key press
  static const _zoomIn  = 1.15;
  static const _zoomOut = 0.87;

  @override
  void dispose() {
    _transformCtrl.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  /// True when a text input widget has keyboard focus — navigation keys should
  /// not fire in that case to avoid interfering with typing.
  bool get _textFieldFocused {
    final focus = FocusManager.instance.primaryFocus;
    // EditableText is the base widget behind TextField / TextFormField
    return focus?.context?.widget is EditableText;
  }

  /// Handle keyboard navigation: arrows + ZQSD → pan, A → zoom out, E → zoom in.
  KeyEventResult _onKeyEvent(FocusNode _, KeyEvent event) {
    // Only act on down or repeat events, and never steal from text fields
    if (event is! KeyDownEvent && event is! KeyRepeatEvent) {
      return KeyEventResult.ignored;
    }
    if (_textFieldFocused) return KeyEventResult.ignored;

    final scale = _transformCtrl.value.getMaxScaleOnAxis();
    // Screen-space step: constant canvas-space movement → scales with zoom
    final step = _panStep * scale;

    Offset? pan;
    double? zoomFactor;

    switch (event.logicalKey) {
      case LogicalKeyboardKey.arrowLeft:
      case LogicalKeyboardKey.keyQ:
        pan = Offset(step, 0);
      case LogicalKeyboardKey.arrowRight:
      case LogicalKeyboardKey.keyD:
        pan = Offset(-step, 0);
      case LogicalKeyboardKey.arrowUp:
      case LogicalKeyboardKey.keyZ:
        pan = Offset(0, step);
      case LogicalKeyboardKey.arrowDown:
      case LogicalKeyboardKey.keyS:
        pan = Offset(0, -step);
      case LogicalKeyboardKey.keyA:
        zoomFactor = _zoomOut;
      case LogicalKeyboardKey.keyE:
        zoomFactor = _zoomIn;
      default:
        return KeyEventResult.ignored;
    }

    if (pan != null) {
      // Shift the translation entries of the matrix directly (screen-space)
      final m = _transformCtrl.value.clone();
      m.storage[12] += pan.dx;
      m.storage[13] += pan.dy;
      _transformCtrl.value = m;
    } else if (zoomFactor != null) {
      final currentScale = _transformCtrl.value.getMaxScaleOnAxis();
      final newScale = (currentScale * zoomFactor).clamp(0.3, 5.0);
      final actualFactor = newScale / currentScale;
      if (actualFactor == 1.0) return KeyEventResult.handled;

      // Zoom around the center of the canvas area
      final size = context.size;
      final cx = (size?.width ?? 400) / 2;
      final cy = (size?.height ?? 300) / 2;

      final m = _transformCtrl.value.clone();
      // Adjust translation so the focal center stays fixed on screen
      m.storage[12] = actualFactor * (m.storage[12] - cx) + cx;
      m.storage[13] = actualFactor * (m.storage[13] - cy) + cy;
      // Scale uniformly (only the diagonal x/y entries)
      m.storage[0]  *= actualFactor;
      m.storage[5]  *= actualFactor;
      _transformCtrl.value = m;
    }

    return KeyEventResult.handled;
  }

  @override
  Widget build(BuildContext context) {
    final dbPath = ref.watch(dbPathProvider);
    final mapsAsync = ref.watch(allMapsProvider);
    final selectedCell = ref.watch(selectedCellProvider);

    final mapRow = mapsAsync.valueOrNull
        ?.where((m) => m.id == widget.mapId)
        .firstOrNull;
    if (mapRow == null) {
      return const Center(child: CircularProgressIndicator());
    }

    final cells = widget.cellsAsync.valueOrNull ?? [];

    // Grid dimensions
    final cols = mapRow.gridCols;
    final rows = mapRow.gridRows;
    final gridType = mapRow.gridType;

    // Canvas size: accommodate all cells
    final canvasW = gridType == 'hex'
        ? _cellSize * 1.732 * (cols + 0.5)
        : _cellSize * cols.toDouble();
    final canvasH = gridType == 'hex'
        ? _cellSize * 1.5 * rows + _cellSize * 0.5
        : _cellSize * rows.toDouble();

    return Focus(
      focusNode: _focusNode,
      autofocus: true,
      onKeyEvent: _onKeyEvent,
      child: Column(
      children: [
        // Toolbar: image upload + zoom slider
        _CanvasToolbar(
          mapId: widget.mapId,
          mapRow: mapRow,
          dbPath: dbPath,
          cellSize: _cellSize,
          onCellSizeChanged: (v) => setState(() => _cellSize = v),
        ),
        const Divider(height: 1),
        Expanded(
          child: GestureDetector(
            // Clicking the canvas re-requests focus so keys work after
            // the user clicks away to a text field and back
            onTap: () => _focusNode.requestFocus(),
            child: InteractiveViewer(
            transformationController: _transformCtrl,
            constrained: false,
            // Pan disabled — use ZQSD/arrows for navigation.
            // This prevents InteractiveViewer from stealing drag gestures
            // from pawn Draggables.
            panEnabled: false,
            minScale: 0.3,
            maxScale: 5,
            child: Stack(
              children: [
                // Background image
                if (mapRow.imagePath != null)
                  SizedBox(
                    width: canvasW,
                    height: canvasH,
                    child: Image.file(
                      File(_resolveImagePath(mapRow.imagePath!, dbPath ?? '')),
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) =>
                          const SizedBox.shrink(),
                    ),
                  ),
                // Grid overlay
                GestureDetector(
                  onTapDown: (details) {
                    final coord = GridPainter.coordAt(
                      details.localPosition,
                      gridType,
                      cols,
                      rows,
                      _cellSize,
                    );
                    if (coord != null) {
                      ref.read(selectedCellProvider.notifier).state = coord;
                    }
                  },
                  child: CustomPaint(
                    size: Size(canvasW, canvasH),
                    painter: GridPainter(
                      cells: cells,
                      gridType: gridType,
                      gridCols: cols,
                      gridRows: rows,
                      cellSize: _cellSize,
                      selectedCell: selectedCell,
                    ),
                  ),
                ),
                // Asset icons overlay (above grid, below drag targets)
                CellAssetsOverlay(
                  mapId: widget.mapId,
                  gridType: gridType,
                  gridCols: cols,
                  gridRows: rows,
                  cellSize: _cellSize,
                  canvasW: canvasW,
                  canvasH: canvasH,
                ),
                // Pawn tokens (above asset icons)
                PawnsOverlay(
                  mapId: widget.mapId,
                  gridType: gridType,
                  gridCols: cols,
                  gridRows: rows,
                  cellSize: _cellSize,
                  canvasW: canvasW,
                  canvasH: canvasH,
                ),
                // Pawn drag targets (long-press to move)
                PawnDragTargetOverlay(
                  mapId: widget.mapId,
                  gridType: gridType,
                  gridCols: cols,
                  gridRows: rows,
                  cellSize: _cellSize,
                  canvasW: canvasW,
                  canvasH: canvasH,
                ),
                // Invisible drag targets on every cell (assets)
                CellDragTargetOverlay(
                  gridType: gridType,
                  gridCols: cols,
                  gridRows: rows,
                  cellSize: _cellSize,
                  canvasW: canvasW,
                  canvasH: canvasH,
                  onDrop: (assetId, q, r) async {
                    final db = ref.read(databaseProvider);
                    await db?.mapDao.placeAsset(
                        widget.mapId, q, r, assetId);
                  },
                ),
              ],
            ),
          ),
        ),
        ),
      ],
      ),
    );
  }

  /// Resolve image path: if relative, join with db directory.
  String _resolveImagePath(String imagePath, String dbPath) {
    if (p.isAbsolute(imagePath)) return imagePath;
    return p.join(p.dirname(dbPath), imagePath);
  }
}

// ---------------------------------------------------------------------------
// Canvas toolbar
// ---------------------------------------------------------------------------

class _CanvasToolbar extends ConsumerWidget {
  final int mapId;
  final MapRow mapRow;
  final String? dbPath;
  final double cellSize;
  final ValueChanged<double> onCellSizeChanged;

  const _CanvasToolbar({
    required this.mapId,
    required this.mapRow,
    required this.dbPath,
    required this.cellSize,
    required this.onCellSizeChanged,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Row(
        children: [
          // Map name
          Text(mapRow.name,
              style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(width: 8),
          Text('${mapRow.gridType} · ${mapRow.gridCols}×${mapRow.gridRows}',
              style: Theme.of(context).textTheme.bodySmall),
          const Spacer(),
          // Zoom slider
          const Icon(Icons.zoom_out, size: 16),
          SizedBox(
            width: 100,
            child: Slider(
              value: cellSize,
              min: 10,
              max: 80,
              onChanged: onCellSizeChanged,
            ),
          ),
          const Icon(Icons.zoom_in, size: 16),
          const SizedBox(width: 8),
          // Auto-detect terrain from image
          IconButton(
            icon: const Icon(Icons.auto_fix_high, size: 18),
            tooltip: mapRow.imagePath == null
                ? 'Charger une image d\'abord'
                : 'Auto-détecter le terrain',
            onPressed: mapRow.imagePath == null || dbPath == null
                ? null
                : () => _autoDetect(context, ref, mapRow, dbPath!),
          ),
          // Image upload
          IconButton(
            icon: const Icon(Icons.image_outlined, size: 18),
            tooltip: 'Image de fond',
            onPressed: dbPath == null
                ? null
                : () => _pickImage(context, ref, dbPath!),
          ),
        ],
      ),
    );
  }

  Future<void> _autoDetect(
    BuildContext context,
    WidgetRef ref,
    MapRow mapRow,
    String dbPath,
  ) async {
    // Resolve absolute image path
    final imagePath = p.isAbsolute(mapRow.imagePath!)
        ? mapRow.imagePath!
        : p.join(p.dirname(dbPath), mapRow.imagePath!);

    // Confirmation — évite les missclicks
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        icon: const Icon(Icons.warning_amber_rounded,
            color: Colors.red, size: 48),
        title: const Text(
          'ATTENTION — Action irréversible',
          style: TextStyle(
              color: Colors.red, fontWeight: FontWeight.bold),
        ),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'L\'auto-détection va ÉCRASER DÉFINITIVEMENT le terrain '
              'de toutes les cellules de cette carte.',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            SizedBox(height: 12),
            Text(
              'Tout terrain modifié manuellement sera perdu. '
              'Il n\'y a aucun moyen d\'annuler cette opération.',
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
        actions: [
          // Destructif à gauche, gris discret
          TextButton(
            style: TextButton.styleFrom(foregroundColor: Colors.grey),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Oui, écraser quand même'),
          ),
          // Safe à droite, vert bien visible
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.green),
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Annuler'),
          ),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;

    // Show loading indicator while sampling pixels
    if (context.mounted) {
      showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (_) => const AlertDialog(
          content: Row(children: [
            CircularProgressIndicator(),
            SizedBox(width: 16),
            Text('Analyse en cours…'),
          ]),
        ),
      );
    }

    final proposals = await detectTerrainFromImage(
      imagePath: imagePath,
      gridType: mapRow.gridType,
      gridCols: mapRow.gridCols,
      gridRows: mapRow.gridRows,
      cellSize: 30.0, // reference cell size — only proportions matter
    );

    // Dismiss loading
    if (context.mounted) Navigator.of(context).pop();

    if (proposals.isEmpty || !context.mounted) return;

    // Show preview dialog
    await showDialog<bool>(
      context: context,
      builder: (_) => TerrainPreviewDialog(
        mapId: mapId,
        proposals: proposals,
        gridCols: mapRow.gridCols,
        gridRows: mapRow.gridRows,
        gridType: mapRow.gridType,
      ),
    );
  }

  Future<void> _pickImage(
      BuildContext context, WidgetRef ref, String dbPath) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.image,
      allowMultiple: false,
    );
    if (result == null || result.files.isEmpty) return;

    final srcPath = result.files.single.path;
    if (srcPath == null) return;

    // Copy image to {db_dir}/maps/
    final mapsDir = Directory(p.join(p.dirname(dbPath), 'maps'));
    if (!mapsDir.existsSync()) mapsDir.createSync(recursive: true);

    final filename = p.basename(srcPath);
    final destPath = p.join(mapsDir.path, filename);
    await File(srcPath).copy(destPath);

    // Store relative path so it works on any machine layout
    final relativePath = p.join('maps', filename);

    final db = ref.read(databaseProvider);
    if (db == null) return;
    await db.mapDao.updateMapMeta(mapId, imagePath: relativePath);
  }
}
