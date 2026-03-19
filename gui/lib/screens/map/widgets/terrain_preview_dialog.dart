import 'dart:math';

import 'package:drift/drift.dart' show Value;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/database.dart';
import '../../../providers/database_provider.dart';
import '../terrain_detector.dart';

// Terrain → display color (matches GridPainter palette)
const _terrainColors = {
  'plain':    Color(0xFF8BC34A),
  'forest':   Color(0xFF388E3C),
  'mountain': Color(0xFF9E9E9E),
  'hills':    Color(0xFFA1887F),
  'river':    Color(0xFF29B6F6),
  'coast':    Color(0xFF80DEEA),
  'sea':      Color(0xFF1565C0),
  'desert':   Color(0xFFFFD54F),
  'swamp':    Color(0xFF558B2F),
  'tundra':   Color(0xFF80CBC4),
  'glacier':  Color(0xFFE0F7FA),
  'ruins':    Color(0xFF8D6E63),
};

Color _color(String t) => _terrainColors[t] ?? const Color(0xFF616161);

/// Dialog shown after terrain auto-detection.
/// Displays a mini-grid preview and lets the GM confirm or cancel.
class TerrainPreviewDialog extends ConsumerStatefulWidget {
  final int mapId;
  final List<CellTerrainProposal> proposals;
  final int gridCols;
  final int gridRows;
  final String gridType;

  const TerrainPreviewDialog({
    super.key,
    required this.mapId,
    required this.proposals,
    required this.gridCols,
    required this.gridRows,
    required this.gridType,
  });

  @override
  ConsumerState<TerrainPreviewDialog> createState() =>
      _TerrainPreviewDialogState();
}

class _TerrainPreviewDialogState
    extends ConsumerState<TerrainPreviewDialog> {
  // Local editable copy — GM can tap a cell to override before applying
  late final List<CellTerrainProposal> _proposals;
  bool _applying = false;

  @override
  void initState() {
    super.initState();
    _proposals = List.of(widget.proposals);
  }

  // Build a fast lookup (q,r) → index in _proposals
  Map<({int q, int r}), int> get _idx {
    final m = <({int q, int r}), int>{};
    for (int i = 0; i < _proposals.length; i++) {
      final p = _proposals[i];
      m[(q: p.q, r: p.r)] = i;
    }
    return m;
  }

  Future<void> _apply() async {
    final db = ref.read(databaseProvider);
    if (db == null) return;
    setState(() => _applying = true);

    for (final p in _proposals) {
      await db.mapDao.upsertCell(MapCellsCompanion(
        mapId: Value(widget.mapId),
        q: Value(p.q),
        r: Value(p.r),
        terrainType: Value(p.terrain),
      ));
    }

    if (mounted) Navigator.of(context).pop(true);
  }

  // Override dialog for a single cell
  Future<void> _editCell(int idx) async {
    final current = _proposals[idx];
    String selected = current.terrain;

    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Cellule (${current.q},${current.r})'),
        content: SizedBox(
          width: 200,
          child: ListView(
            shrinkWrap: true,
            children: _terrainColors.keys.map((t) => RadioListTile<String>(
              title: Row(children: [
                Container(
                  width: 14, height: 14,
                  color: _color(t),
                  margin: const EdgeInsets.only(right: 8),
                ),
                Text(t),
              ]),
              value: t,
              groupValue: selected,
              onChanged: (v) {
                if (v != null) {
                  selected = v;
                  Navigator.pop(ctx, v);
                }
              },
            )).toList(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Annuler'),
          ),
        ],
      ),
    );

    if (result != null) {
      setState(() {
        _proposals[idx] = CellTerrainProposal(
          q: current.q,
          r: current.r,
          terrain: result,
          hue: current.hue,
          sat: current.sat,
          val: current.val,
        );
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final cellCount = _proposals.length;
    // Legend: unique terrains detected
    final terrains = _proposals.map((p) => p.terrain).toSet().toList()..sort();

    // Cell pixel size in preview (clamp so grid fits in ~480px wide dialog)
    final previewCellPx =
        min(20.0, (460.0 / widget.gridCols).floorToDouble());
    final gridW = previewCellPx * widget.gridCols;
    final gridH = previewCellPx * widget.gridRows;

    final idxMap = _idx;

    return AlertDialog(
      title: const Text('Terrain auto-détecté — aperçu'),
      content: SizedBox(
        width: max(400, gridW + 40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '$cellCount cellules analysées. '
              'Clique sur une cellule pour corriger.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 12),

            // Mini grid preview
            SizedBox(
              width: gridW,
              height: gridH,
              child: Stack(
                children: [
                  for (final p in _proposals)
                    Positioned(
                      left: p.q * previewCellPx,
                      top: p.r * previewCellPx,
                      child: Tooltip(
                        message: '${p.terrain}\n'
                            'H:${p.hue.toStringAsFixed(0)}° '
                            'S:${(p.sat * 100).toStringAsFixed(0)}% '
                            'V:${(p.val * 100).toStringAsFixed(0)}%',
                        child: GestureDetector(
                          onTap: () {
                            final i = idxMap[(q: p.q, r: p.r)];
                            if (i != null) _editCell(i);
                          },
                          child: Container(
                            width: previewCellPx,
                            height: previewCellPx,
                            decoration: BoxDecoration(
                              color: _color(p.terrain),
                              border: Border.all(
                                  color: Colors.black12, width: 0.5),
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // Legend
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: terrains.map((t) => Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 12, height: 12,
                    color: _color(t),
                    margin: const EdgeInsets.only(right: 4),
                  ),
                  Text(t, style: const TextStyle(fontSize: 11)),
                ],
              )).toList(),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _applying ? null : () => Navigator.of(context).pop(false),
          child: const Text('Annuler'),
        ),
        FilledButton.icon(
          onPressed: _applying ? null : _apply,
          icon: _applying
              ? const SizedBox(
                  width: 14, height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.check, size: 16),
          label: const Text('Appliquer'),
        ),
      ],
    );
  }
}
