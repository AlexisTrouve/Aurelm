import 'package:drift/drift.dart' show Value;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../data/database.dart';
import '../../../models/map_with_details.dart';
import '../../../models/cell_linked_entity.dart';
import '../../../models/cell_linked_subject.dart';
import '../../../models/entity_with_details.dart';
import '../../../models/subject_with_details.dart';
import '../../../providers/map_provider.dart';
import '../../../providers/database_provider.dart';
import '../../../providers/civilization_provider.dart';
import '../../../providers/entity_provider.dart';
import '../../../providers/subject_provider.dart';

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

                // Icons section
                _CellIconsSection(
                  mapId: widget.mapId,
                  q: widget.coord.q,
                  r: widget.coord.r,
                ),
                const SizedBox(height: 16),

                // Linked entities
                _CellEntitiesSection(
                  mapId: widget.mapId,
                  q: widget.coord.q,
                  r: widget.coord.r,
                ),
                const SizedBox(height: 16),

                // Linked subjects
                _CellSubjectsSection(
                  mapId: widget.mapId,
                  q: widget.coord.q,
                  r: widget.coord.r,
                ),
                const SizedBox(height: 16),

                // Cell notes
                _CellNotesSection(
                  mapId: widget.mapId,
                  q: widget.coord.q,
                  r: widget.coord.r,
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

// ---------------------------------------------------------------------------
// Icons section — shows assets on this cell with remove button
// ---------------------------------------------------------------------------

class _CellIconsSection extends ConsumerWidget {
  final int mapId;
  final int q;
  final int r;
  const _CellIconsSection(
      {required this.mapId, required this.q, required this.r});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cellAssetsAsync = ref.watch(
      cellAssetsProvider((mapId: mapId, q: q, r: r)),
    );
    final allAssetsAsync = ref.watch(allAssetsProvider);

    return cellAssetsAsync.when(
      data: (placements) {
        if (placements.isEmpty) return const SizedBox.shrink();

        // Build asset lookup id → row
        final assetMap = <int, MapAssetRow>{};
        if (allAssetsAsync.valueOrNull != null) {
          for (final a in allAssetsAsync.valueOrNull!) {
            assetMap[a.id] = a;
          }
        }

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Icônes (${placements.length}/7)',
                style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: placements.map((p) {
                final asset = assetMap[p.assetId];
                return Stack(
                  clipBehavior: Clip.none,
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        border: Border.all(color: Colors.white24),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: asset == null
                          ? const Icon(Icons.broken_image, size: 20)
                          : ClipRRect(
                              borderRadius: BorderRadius.circular(5),
                              child: Image.memory(asset.data,
                                  fit: BoxFit.contain,
                                  gaplessPlayback: true),
                            ),
                    ),
                    // Remove button — top-right corner
                    Positioned(
                      top: -6,
                      right: -6,
                      child: GestureDetector(
                        onTap: () async {
                          final db = ref.read(databaseProvider);
                          await db?.mapDao.removeAsset(mapId, q, r, p.assetId);
                        },
                        child: Container(
                          width: 16,
                          height: 16,
                          decoration: const BoxDecoration(
                            color: Colors.red,
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.close,
                              size: 10, color: Colors.white),
                        ),
                      ),
                    ),
                  ],
                );
              }).toList(),
            ),
          ],
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
    );
  }
}

// ---------------------------------------------------------------------------
// Linked entities section
// ---------------------------------------------------------------------------

class _CellEntitiesSection extends ConsumerStatefulWidget {
  final int mapId;
  final int q;
  final int r;
  const _CellEntitiesSection(
      {required this.mapId, required this.q, required this.r});

  @override
  ConsumerState<_CellEntitiesSection> createState() =>
      _CellEntitiesSectionState();
}

class _CellEntitiesSectionState extends ConsumerState<_CellEntitiesSection> {
  final _searchCtrl = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final linkedAsync = ref.watch(
        cellLinkedEntitiesProvider((mapId: widget.mapId, q: widget.q, r: widget.r)));
    final allEntitiesAsync = ref.watch(entityListProvider);

    final linked = linkedAsync.valueOrNull ?? [];
    final linkedIds = linked.map((e) => e.entityId).toSet();

    // Filter for search suggestions — exclude already linked
    final allEntities = allEntitiesAsync.valueOrNull ?? [];
    final suggestions = _query.isEmpty
        ? <EntityWithDetails>[]
        : allEntities
            .where((e) =>
                e.entity.canonicalName
                    .toLowerCase()
                    .contains(_query.toLowerCase()) &&
                !linkedIds.contains(e.entity.id))
            .take(6)
            .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Entités', style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 6),
        // Chips of linked entities
        if (linked.isNotEmpty)
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: linked
                .map((e) => _LinkedChip(
                      label: e.entityName,
                      color: _entityTypeColor(e.entityType),
                      onDelete: () {
                        final db = ref.read(databaseProvider);
                        db?.mapDao.removeCellEntity(
                            widget.mapId, widget.q, widget.r, e.entityId);
                      },
                      onTap: () =>
                          context.push('/entities/${e.entityId}'),
                    ))
                .toList(),
          ),
        const SizedBox(height: 6),
        // Search field to add
        TextField(
          controller: _searchCtrl,
          decoration: const InputDecoration(
            hintText: 'Lier une entité...',
            prefixIcon: Icon(Icons.search, size: 14),
            isDense: true,
            border: OutlineInputBorder(),
            contentPadding: EdgeInsets.symmetric(vertical: 6, horizontal: 8),
          ),
          style: const TextStyle(fontSize: 12),
          onChanged: (v) => setState(() => _query = v),
        ),
        if (suggestions.isNotEmpty)
          Material(
            elevation: 2,
            child: ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: suggestions.length,
              itemBuilder: (_, i) {
                final ewd = suggestions[i];
                return ListTile(
                  dense: true,
                  title: Text(ewd.entity.canonicalName,
                      style: const TextStyle(fontSize: 12)),
                  subtitle: Text(ewd.entity.entityType,
                      style: const TextStyle(fontSize: 10)),
                  onTap: () async {
                    final db = ref.read(databaseProvider);
                    await db?.mapDao.addCellEntity(
                        widget.mapId, widget.q, widget.r, ewd.entity.id);
                    setState(() {
                      _query = '';
                      _searchCtrl.clear();
                    });
                  },
                );
              },
            ),
          ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Linked subjects section
// ---------------------------------------------------------------------------

class _CellSubjectsSection extends ConsumerStatefulWidget {
  final int mapId;
  final int q;
  final int r;
  const _CellSubjectsSection(
      {required this.mapId, required this.q, required this.r});

  @override
  ConsumerState<_CellSubjectsSection> createState() =>
      _CellSubjectsSectionState();
}

class _CellSubjectsSectionState extends ConsumerState<_CellSubjectsSection> {
  final _searchCtrl = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final linkedAsync = ref.watch(
        cellLinkedSubjectsProvider((mapId: widget.mapId, q: widget.q, r: widget.r)));
    final allSubjectsAsync = ref.watch(subjectListProvider);

    final linked = linkedAsync.valueOrNull ?? [];
    final linkedIds = linked.map((s) => s.subjectId).toSet();

    final allSubjects = allSubjectsAsync.valueOrNull ?? [];
    final suggestions = _query.isEmpty
        ? <SubjectWithDetails>[]
        : allSubjects
            .where((s) =>
                s.subject.title
                    .toLowerCase()
                    .contains(_query.toLowerCase()) &&
                !linkedIds.contains(s.subject.id))
            .take(6)
            .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Sujets', style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 6),
        if (linked.isNotEmpty)
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: linked
                .map((s) => _LinkedChip(
                      label: s.title,
                      color: _subjectStatusColor(s.status),
                      onDelete: () {
                        final db = ref.read(databaseProvider);
                        db?.mapDao.removeCellSubject(
                            widget.mapId, widget.q, widget.r, s.subjectId);
                      },
                      onTap: () =>
                          context.push('/subjects/${s.subjectId}'),
                    ))
                .toList(),
          ),
        const SizedBox(height: 6),
        TextField(
          controller: _searchCtrl,
          decoration: const InputDecoration(
            hintText: 'Lier un sujet...',
            prefixIcon: Icon(Icons.search, size: 14),
            isDense: true,
            border: OutlineInputBorder(),
            contentPadding: EdgeInsets.symmetric(vertical: 6, horizontal: 8),
          ),
          style: const TextStyle(fontSize: 12),
          onChanged: (v) => setState(() => _query = v),
        ),
        if (suggestions.isNotEmpty)
          Material(
            elevation: 2,
            child: ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: suggestions.length,
              itemBuilder: (_, i) {
                final swd = suggestions[i];
                return ListTile(
                  dense: true,
                  title: Text(swd.subject.title,
                      style: const TextStyle(fontSize: 12),
                      overflow: TextOverflow.ellipsis),
                  subtitle: Text(
                      '${swd.civName} · ${swd.subject.status}',
                      style: const TextStyle(fontSize: 10)),
                  onTap: () async {
                    final db = ref.read(databaseProvider);
                    await db?.mapDao.addCellSubject(
                        widget.mapId, widget.q, widget.r, swd.subject.id);
                    setState(() {
                      _query = '';
                      _searchCtrl.clear();
                    });
                  },
                );
              },
            ),
          ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Cell notes section
// ---------------------------------------------------------------------------

class _CellNotesSection extends ConsumerWidget {
  final int mapId;
  final int q;
  final int r;
  const _CellNotesSection(
      {required this.mapId, required this.q, required this.r});

  Future<void> _addNote(BuildContext context, WidgetRef ref) async {
    final db = ref.read(databaseProvider);
    if (db == null) return;

    String title = '';
    String content = '';

    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Ajouter une note'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              decoration: const InputDecoration(
                  labelText: 'Titre', border: OutlineInputBorder()),
              onChanged: (v) => title = v,
            ),
            const SizedBox(height: 10),
            TextField(
              decoration: const InputDecoration(
                  labelText: 'Contenu', border: OutlineInputBorder()),
              maxLines: 4,
              onChanged: (v) => content = v,
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
              if (content.trim().isEmpty) return;
              await db.mapDao.addCellNote(mapId, q, r,
                  title: title.trim(), content: content.trim());
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('Ajouter'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notesAsync =
        ref.watch(cellNotesProvider((mapId: mapId, q: q, r: r)));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text('Notes', style: Theme.of(context).textTheme.labelLarge),
            const Spacer(),
            IconButton(
              icon: const Icon(Icons.add, size: 18),
              tooltip: 'Ajouter une note',
              onPressed: () => _addNote(context, ref),
            ),
          ],
        ),
        notesAsync.when(
          data: (notesList) {
            if (notesList.isEmpty) {
              return const Padding(
                padding: EdgeInsets.only(top: 4),
                child: Text('Aucune note',
                    style: TextStyle(color: Colors.grey, fontSize: 12)),
              );
            }
            return Column(
              children: notesList
                  .map((n) => _NoteTile(
                        note: n,
                        onDelete: () {
                          final db = ref.read(databaseProvider);
                          db?.mapDao.deleteCellNote(n.id);
                        },
                      ))
                  .toList(),
            );
          },
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/// Reusable chip for linked entities / subjects.
class _LinkedChip extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onDelete;
  final VoidCallback onTap;

  const _LinkedChip({
    required this.label,
    required this.color,
    required this.onDelete,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Chip(
        avatar: CircleAvatar(backgroundColor: color, radius: 5),
        label: Text(label, style: const TextStyle(fontSize: 11)),
        deleteIcon: const Icon(Icons.close, size: 12),
        onDeleted: onDelete,
        padding: EdgeInsets.zero,
        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        visualDensity: VisualDensity.compact,
      ),
    );
  }
}

class _NoteTile extends StatelessWidget {
  final NoteRow note;
  final VoidCallback onDelete;
  const _NoteTile({required this.note, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (note.title.isNotEmpty)
                  Text(note.title,
                      style: const TextStyle(
                          fontSize: 12, fontWeight: FontWeight.bold)),
                Text(note.content,
                    style: const TextStyle(fontSize: 11, color: Colors.grey),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline, size: 14, color: Colors.red),
            tooltip: 'Supprimer',
            onPressed: onDelete,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
          ),
        ],
      ),
    );
  }
}

/// Entity type → accent color (for the chip avatar dot).
Color _entityTypeColor(String type) {
  const palette = {
    'person': Color(0xFFE57373),
    'civilization': Color(0xFF64B5F6),
    'institution': Color(0xFFFFD54F),
    'place': Color(0xFF81C784),
    'technology': Color(0xFF4DD0E1),
    'resource': Color(0xFFA1887F),
    'creature': Color(0xFFCE93D8),
    'event': Color(0xFFFF8A65),
    'caste': Color(0xFFB0BEC5),
    'belief': Color(0xFFF48FB1),
  };
  return palette[type] ?? const Color(0xFF90A4AE);
}

/// Subject status → color.
Color _subjectStatusColor(String status) {
  switch (status) {
    case 'open':
      return Colors.orange;
    case 'resolved':
      return Colors.green;
    case 'abandoned':
      return Colors.red;
    default:
      return Colors.grey;
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
