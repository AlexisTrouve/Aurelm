import 'package:drift/drift.dart' show Value;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/database.dart';
import '../../../models/map_with_details.dart';
import '../../../providers/map_provider.dart';
import '../../../providers/database_provider.dart';
import '../../../providers/civilization_provider.dart';

const _terrainOptions = [
  'plain', 'forest', 'hills', 'mountain',
  'coast', 'sea', 'desert', 'swamp', 'tundra', 'glacier',
];

const _eventTypeOptions = [
  'note', 'settlement', 'battle', 'discovery',
  'diplomatic', 'migration', 'disaster',
];

/// Right panel: shows details + edit controls for the selected cell.
class CellEditorPanel extends ConsumerStatefulWidget {
  final int mapId;
  final ({int q, int r}) coord;
  final MapCellWithDetails? cellDetail;

  const CellEditorPanel({
    super.key,
    required this.mapId,
    required this.coord,
    required this.cellDetail,
  });

  @override
  ConsumerState<CellEditorPanel> createState() => _CellEditorPanelState();
}

class _CellEditorPanelState extends ConsumerState<CellEditorPanel> {
  late TextEditingController _labelCtrl;

  @override
  void initState() {
    super.initState();
    _labelCtrl = TextEditingController(
      text: widget.cellDetail?.cell.label ?? '',
    );
  }

  @override
  void didUpdateWidget(CellEditorPanel old) {
    super.didUpdateWidget(old);
    // Sync label field when a different cell is selected
    if (old.coord != widget.coord) {
      _labelCtrl.text = widget.cellDetail?.cell.label ?? '';
    }
  }

  @override
  void dispose() {
    _labelCtrl.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Save helpers — optimistic field-by-field upsert
  // ---------------------------------------------------------------------------

  Future<void> _upsertCell(MapCellsCompanion companion) async {
    final db = ref.read(databaseProvider);
    if (db == null) return;
    await db.mapDao.upsertCell(companion);
  }

  MapCellsCompanion _baseCompanion() => MapCellsCompanion(
        mapId: Value(widget.mapId),
        q: Value(widget.coord.q),
        r: Value(widget.coord.r),
      );

  // ---------------------------------------------------------------------------
  // Event dialog
  // ---------------------------------------------------------------------------

  Future<void> _addEvent() async {
    final db = ref.read(databaseProvider);
    if (db == null) return;

    String desc = '';
    String eventType = 'note';

    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDlg) => AlertDialog(
          title: const Text('Ajouter un événement'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                decoration:
                    const InputDecoration(labelText: 'Description', border: OutlineInputBorder()),
                maxLines: 3,
                onChanged: (v) => desc = v,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: eventType,
                decoration: const InputDecoration(
                    labelText: 'Type', border: OutlineInputBorder()),
                items: _eventTypeOptions
                    .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                    .toList(),
                onChanged: (v) => setDlg(() => eventType = v ?? 'note'),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Annuler'),
            ),
            FilledButton(
              onPressed: () async {
                if (desc.trim().isEmpty) return;
                await db.mapDao.insertCellEvent(MapCellEventsCompanion(
                  mapId: Value(widget.mapId),
                  q: Value(widget.coord.q),
                  r: Value(widget.coord.r),
                  description: Value(desc.trim()),
                  eventType: Value(eventType),
                ));
                if (ctx.mounted) Navigator.pop(ctx);
              },
              child: const Text('Ajouter'),
            ),
          ],
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final q = widget.coord.q;
    final r = widget.coord.r;
    final cell = widget.cellDetail?.cell;
    final terrain = cell?.terrainType ?? 'plain';
    final civId = cell?.controllingCivId;
    final childMapId = cell?.childMapId;

    final civsAsync = ref.watch(civListProvider);
    final mapsAsync = ref.watch(allMapsProvider);
    final eventsAsync = ref.watch(
        cellEventsProvider((mapId: widget.mapId, q: q, r: r)));

    return Container(
      width: 300,
      color: Theme.of(context).colorScheme.surface,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 8, 4),
            child: Row(
              children: [
                Text('Cellule ($q,$r)',
                    style: Theme.of(context).textTheme.titleMedium),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close, size: 18),
                  onPressed: () =>
                      ref.read(selectedCellProvider.notifier).state = null,
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Label
                TextField(
                  controller: _labelCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Label',
                    border: OutlineInputBorder(),
                  ),
                  onSubmitted: (v) => _upsertCell(
                    _baseCompanion().copyWith(label: Value(v.isEmpty ? null : v)),
                  ),
                ),
                const SizedBox(height: 12),

                // Terrain
                DropdownButtonFormField<String>(
                  value: terrain,
                  decoration: const InputDecoration(
                    labelText: 'Terrain',
                    border: OutlineInputBorder(),
                  ),
                  items: _terrainOptions
                      .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                      .toList(),
                  onChanged: (v) {
                    if (v == null) return;
                    _upsertCell(_baseCompanion()
                        .copyWith(terrainType: Value(v)));
                  },
                ),
                const SizedBox(height: 12),

                // Controlling civ
                civsAsync.when(
                  data: (civs) => DropdownButtonFormField<int?>(
                    value: civId,
                    decoration: const InputDecoration(
                      labelText: 'Civ contrôlante',
                      border: OutlineInputBorder(),
                    ),
                    items: [
                      const DropdownMenuItem<int?>(
                          value: null, child: Text('(aucune)')),
                      ...civs.map((c) => DropdownMenuItem(
                          value: c.civ.id,
                          child: Text(c.civ.name))),
                    ],
                    onChanged: (v) => _upsertCell(
                        _baseCompanion()
                            .copyWith(controllingCivId: Value(v))),
                  ),
                  loading: () => const LinearProgressIndicator(),
                  error: (_, __) => const SizedBox.shrink(),
                ),
                const SizedBox(height: 12),

                // Child map
                mapsAsync.when(
                  data: (maps) => DropdownButtonFormField<int?>(
                    value: childMapId,
                    decoration: const InputDecoration(
                      labelText: 'Carte enfant',
                      border: OutlineInputBorder(),
                    ),
                    items: [
                      const DropdownMenuItem<int?>(
                          value: null, child: Text('(aucune)')),
                      ...maps
                          // A map can't be its own child
                          .where((m) => m.id != widget.mapId)
                          .map((m) => DropdownMenuItem(
                              value: m.id, child: Text(m.name))),
                    ],
                    onChanged: (v) => _upsertCell(
                        _baseCompanion()
                            .copyWith(childMapId: Value(v))),
                  ),
                  loading: () => const LinearProgressIndicator(),
                  error: (_, __) => const SizedBox.shrink(),
                ),
                const SizedBox(height: 16),

                // Events section
                Row(
                  children: [
                    Text('Événements',
                        style: Theme.of(context).textTheme.labelLarge),
                    const Spacer(),
                    IconButton(
                      icon: const Icon(Icons.add, size: 18),
                      tooltip: 'Ajouter un événement',
                      onPressed: _addEvent,
                    ),
                  ],
                ),
                eventsAsync.when(
                  data: (events) => events.isEmpty
                      ? const Padding(
                          padding: EdgeInsets.only(top: 4),
                          child: Text('Aucun événement',
                              style: TextStyle(
                                  color: Colors.grey, fontSize: 12)),
                        )
                      : Column(
                          children: events
                              .map((e) => _EventTile(event: e))
                              .toList(),
                        ),
                  loading: () => const LinearProgressIndicator(),
                  error: (err, _) => Text('$err'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _EventTile extends StatelessWidget {
  final MapCellEventRow event;
  const _EventTile({required this.event});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Chip(
            label: Text(event.eventType,
                style: const TextStyle(fontSize: 10)),
            padding: EdgeInsets.zero,
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            visualDensity: VisualDensity.compact,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(event.description,
                style: const TextStyle(fontSize: 12)),
          ),
        ],
      ),
    );
  }
}
