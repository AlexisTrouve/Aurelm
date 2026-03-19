import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/database.dart';
import '../../../providers/database_provider.dart';
import '../../../models/entity_with_details.dart';
import '../../../providers/entity_provider.dart';
import '../../../providers/map_provider.dart';

/// Left panel tab — pawn management.
/// Shows active pawns on map + entity search to add new ones.
class PawnsPanel extends ConsumerStatefulWidget {
  final int mapId;

  const PawnsPanel({super.key, required this.mapId});

  @override
  ConsumerState<PawnsPanel> createState() => _PawnsPanelState();
}

class _PawnsPanelState extends ConsumerState<PawnsPanel> {
  final _searchCtrl = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pawnsAsync = ref.watch(mapPawnsProvider(widget.mapId));
    final entitiesAsync = ref.watch(entityListProvider);
    final db = ref.read(databaseProvider);

    // Active pawn entity ids (to grey out in the "add" list)
    final activePawnEntityIds = pawnsAsync.valueOrNull
            ?.map((p) => p.entityId)
            .toSet() ??
        {};

    // Filtered entities for search
    final allEntities = entitiesAsync.valueOrNull ?? [];
    final filtered = _query.isEmpty
        ? <EntityWithDetails>[]
        : allEntities
            .where((e) =>
                e.entity.canonicalName
                    .toLowerCase()
                    .contains(_query.toLowerCase()) &&
                !activePawnEntityIds.contains(e.entity.id))
            .take(8)
            .toList();

    return Column(
      children: [
        // Active pawns
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 8, 4),
          child: Row(
            children: [
              const Text('Pions actifs',
                  style:
                      TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
              const Spacer(),
              Text(
                '${activePawnEntityIds.length}',
                style: const TextStyle(fontSize: 11, color: Colors.grey),
              ),
            ],
          ),
        ),
        pawnsAsync.when(
          data: (pawns) {
            if (pawns.isEmpty) {
              return const Padding(
                padding: EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                child: Text('Aucun pion sur cette carte.',
                    style: TextStyle(color: Colors.grey, fontSize: 11)),
              );
            }

            // Build entity lookup
            final entityMap = <int, EntityWithDetails>{};
            for (final e in allEntities) {
              entityMap[e.entity.id] = e;
            }

            return ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: pawns.length,
              itemBuilder: (_, i) {
                final pawn = pawns[i];
                final entity = entityMap[pawn.entityId];
                return ListTile(
                  dense: true,
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 0),
                  leading: CircleAvatar(
                    radius: 12,
                    backgroundColor: Colors.grey[800],
                    child: Text(
                      entity?.entity.canonicalName.isNotEmpty == true
                          ? entity!.entity.canonicalName[0].toUpperCase()
                          : '?',
                      style: const TextStyle(fontSize: 10),
                    ),
                  ),
                  title: Text(
                    entity?.entity.canonicalName ?? '?',
                    style: const TextStyle(fontSize: 12),
                    overflow: TextOverflow.ellipsis,
                  ),
                  subtitle: Text(
                    '(${pawn.q}, ${pawn.r})',
                    style: const TextStyle(fontSize: 10, color: Colors.grey),
                  ),
                  trailing: IconButton(
                    icon: const Icon(Icons.remove_circle_outline,
                        size: 15, color: Colors.red),
                    tooltip: 'Retirer',
                    onPressed: () => db?.mapDao.removePawn(pawn.id),
                  ),
                );
              },
            );
          },
          loading: () => const LinearProgressIndicator(),
          error: (e, _) => Text('$e'),
        ),

        const Divider(height: 1),

        // Search to add a new pawn
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: TextField(
            controller: _searchCtrl,
            decoration: const InputDecoration(
              hintText: 'Ajouter un pion...',
              prefixIcon: Icon(Icons.search, size: 16),
              isDense: true,
              border: OutlineInputBorder(),
              contentPadding:
                  EdgeInsets.symmetric(vertical: 8, horizontal: 8),
            ),
            style: const TextStyle(fontSize: 12),
            onChanged: (v) => setState(() => _query = v),
          ),
        ),

        // Search results
        if (filtered.isNotEmpty)
          Expanded(
            child: ListView.builder(
              itemCount: filtered.length,
              itemBuilder: (_, i) {
                final ewd = filtered[i];
                return ListTile(
                  dense: true,
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 0),
                  title: Text(ewd.entity.canonicalName,
                      style: const TextStyle(fontSize: 12),
                      overflow: TextOverflow.ellipsis),
                  subtitle: Text(ewd.entity.entityType,
                      style: const TextStyle(fontSize: 10)),
                  trailing: IconButton(
                    icon: const Icon(Icons.add_location_alt_outlined,
                        size: 15),
                    tooltip: 'Placer sur la case sélectionnée',
                    onPressed: () =>
                        _placePawnOnSelected(db, ewd, ref),
                  ),
                );
              },
            ),
          )
        else if (_query.isEmpty)
          const Expanded(child: SizedBox.shrink()),
      ],
    );
  }

  Future<void> _placePawnOnSelected(
    AurelmDatabase? db,
    EntityWithDetails ewd,
    WidgetRef ref,
  ) async {
    if (db == null) return;
    final selected = ref.read(selectedCellProvider);
    if (selected == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Sélectionne d\'abord une case sur la carte.'),
          duration: Duration(seconds: 2),
        ),
      );
      return;
    }
    await db.mapDao
        .placePawn(widget.mapId, selected.q, selected.r, ewd.entity.id);
    setState(() {
      _query = '';
      _searchCtrl.clear();
    });
  }
}
