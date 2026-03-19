import 'package:drift/drift.dart';

import '../database.dart';
import '../tables/maps.dart';
import '../tables/civilizations.dart';
import '../tables/entities.dart';
import '../../models/map_with_details.dart';

part 'map_dao.g.dart';

@DriftAccessor(tables: [MapMaps, MapCells, MapCellEvents, MapAssets, MapCellAssets, CivCivilizations, EntityEntities])
class MapDao extends DatabaseAccessor<AurelmDatabase> with _$MapDaoMixin {
  MapDao(super.db);

  // ---------------------------------------------------------------------------
  // Maps
  // ---------------------------------------------------------------------------

  /// Stream of all maps ordered by parent (roots first) then name.
  /// customSelect + customUpdate so Drift correctly invalidates the stream.
  Stream<List<MapRow>> watchAllMaps() {
    return customSelect(
      'SELECT * FROM map_maps ORDER BY parent_map_id NULLS FIRST, name',
      readsFrom: {mapMaps},
    ).watch().map((rows) => rows.map((r) => MapRow(
          id: r.read<int>('id'),
          name: r.read<String>('name'),
          imagePath: r.readNullable<String>('image_path'),
          gridType: r.read<String>('grid_type'),
          gridCols: r.read<int>('grid_cols'),
          gridRows: r.read<int>('grid_rows'),
          parentMapId: r.readNullable<int>('parent_map_id'),
          parentCellQ: r.readNullable<int>('parent_cell_q'),
          parentCellR: r.readNullable<int>('parent_cell_r'),
          createdAt: r.read<String>('created_at'),
        )).toList());
  }

  /// Stream of a single map by id.
  Stream<MapRow?> watchMap(int id) {
    return (select(mapMaps)..where((m) => m.id.equals(id)))
        .watchSingleOrNull();
  }

  // ---------------------------------------------------------------------------
  // Cells
  // ---------------------------------------------------------------------------

  /// Stream of all cells for a map, enriched with civ name, entity name, child map name.
  Stream<List<MapCellWithDetails>> watchCells(int mapId) {
    return customSelect(
      '''
      SELECT mc.map_id, mc.q, mc.r, mc.terrain_type, mc.label,
             mc.controlling_civ_id, mc.entity_id, mc.child_map_id, mc.metadata,
             c.name  AS civ_name,
             e.canonical_name AS entity_name,
             cm.name AS child_map_name
      FROM map_cells mc
      LEFT JOIN civ_civilizations c  ON c.id  = mc.controlling_civ_id
      LEFT JOIN entity_entities   e  ON e.id  = mc.entity_id
      LEFT JOIN map_maps          cm ON cm.id = mc.child_map_id
      WHERE mc.map_id = ?
      ORDER BY mc.r, mc.q
      ''',
      variables: [Variable.withInt(mapId)],
      readsFrom: {mapCells, civCivilizations, entityEntities, mapMaps},
    ).watch().map((rows) => rows.map((r) {
          final cell = MapCellRow(
            mapId: r.read<int>('map_id'),
            q: r.read<int>('q'),
            r: r.read<int>('r'),
            terrainType: r.read<String>('terrain_type'),
            label: r.readNullable<String>('label'),
            controllingCivId: r.readNullable<int>('controlling_civ_id'),
            entityId: r.readNullable<int>('entity_id'),
            childMapId: r.readNullable<int>('child_map_id'),
            metadata: r.readNullable<String>('metadata'),
          );
          return MapCellWithDetails(
            cell: cell,
            civName: r.readNullable<String>('civ_name'),
            entityName: r.readNullable<String>('entity_name'),
            childMapName: r.readNullable<String>('child_map_name'),
          );
        }).toList());
  }

  /// Get a single cell (non-reactive).
  Future<MapCellRow?> getCell(int mapId, int q, int r) {
    return (select(mapCells)
          ..where((c) =>
              c.mapId.equals(mapId) & c.q.equals(q) & c.r.equals(r)))
        .getSingleOrNull();
  }

  // ---------------------------------------------------------------------------
  // Cell events
  // ---------------------------------------------------------------------------

  /// Stream of events for a given cell, newest first.
  Stream<List<MapCellEventRow>> watchCellEvents(int mapId, int q, int r) {
    return (select(mapCellEvents)
          ..where((e) =>
              e.mapId.equals(mapId) & e.q.equals(q) & e.r.equals(r))
          ..orderBy([(e) => OrderingTerm.desc(e.createdAt)]))
        .watch();
  }

  // ---------------------------------------------------------------------------
  // Mutations
  // ---------------------------------------------------------------------------

  /// Insert or replace a map (upsert on name conflict).
  Future<int> upsertMap(MapMapsCompanion m) {
    return into(mapMaps).insertOnConflictUpdate(m);
  }

  /// Update image path and grid settings for an existing map.
  Future<void> updateMapMeta(
    int id, {
    String? imagePath,
    String? gridType,
    int? gridCols,
    int? gridRows,
  }) {
    return (update(mapMaps)..where((m) => m.id.equals(id))).write(
      MapMapsCompanion(
        imagePath: imagePath != null ? Value(imagePath) : const Value.absent(),
        gridType: gridType != null ? Value(gridType) : const Value.absent(),
        gridCols: gridCols != null ? Value(gridCols) : const Value.absent(),
        gridRows: gridRows != null ? Value(gridRows) : const Value.absent(),
      ),
    );
  }

  /// Upsert a cell (composite PK: map_id + q + r).
  Future<void> upsertCell(MapCellsCompanion c) {
    return into(mapCells).insertOnConflictUpdate(c);
  }

  /// Delete a map and cascade to cells + events.
  Future<void> deleteMap(int id) {
    return (delete(mapMaps)..where((m) => m.id.equals(id))).go();
  }

  /// Insert a new cell event.
  Future<int> insertCellEvent(MapCellEventsCompanion e) {
    final now = DateTime.now().toIso8601String();
    return into(mapCellEvents).insert(
      e.copyWith(createdAt: Value(now)),
    );
  }

  // ---------------------------------------------------------------------------
  // Assets
  // ---------------------------------------------------------------------------

  /// All assets ordered by name.
  Stream<List<MapAssetRow>> watchAllAssets() {
    return (select(mapAssets)..orderBy([(a) => OrderingTerm.asc(a.name)]))
        .watch();
  }

  /// Insert a new asset (WebP blob).
  Future<int> insertAsset(MapAssetsCompanion a) {
    final now = DateTime.now().toIso8601String();
    return into(mapAssets).insert(a.copyWith(createdAt: Value(now)));
  }

  /// Delete an asset — cascades to map_cell_assets.
  Future<void> deleteAsset(int assetId) {
    return (delete(mapAssets)..where((a) => a.id.equals(assetId))).go();
  }

  // ---------------------------------------------------------------------------
  // Cell ↔ asset placements
  // ---------------------------------------------------------------------------

  /// Stream of placements for a cell, ordered by z_order.
  Stream<List<MapCellAssetRow>> watchCellAssets(int mapId, int q, int r) {
    return (select(mapCellAssets)
          ..where((ca) =>
              ca.mapId.equals(mapId) & ca.q.equals(q) & ca.r.equals(r))
          ..orderBy([(ca) => OrderingTerm.asc(ca.zOrder)]))
        .watch();
  }

  /// Stream of ALL placements for a map (used by overlay painter).
  Stream<List<MapCellAssetRow>> watchMapCellAssets(int mapId) {
    return (select(mapCellAssets)
          ..where((ca) => ca.mapId.equals(mapId))
          ..orderBy([(ca) => OrderingTerm.asc(ca.zOrder)]))
        .watch();
  }

  /// Place an asset on a cell.
  /// Assigns the next z_order slot (max 6 → 7 icons per cell).
  Future<void> placeAsset(int mapId, int q, int r, int assetId) async {
    // Count existing placements for this cell
    final count = await (select(mapCellAssets)
          ..where((ca) =>
              ca.mapId.equals(mapId) & ca.q.equals(q) & ca.r.equals(r)))
        .get()
        .then((rows) => rows.length);

    if (count >= 7) return; // max 7 icons per cell

    final now = DateTime.now().toIso8601String();
    await into(mapCellAssets).insertOnConflictUpdate(MapCellAssetsCompanion(
      mapId: Value(mapId),
      q: Value(q),
      r: Value(r),
      assetId: Value(assetId),
      zOrder: Value(count), // next available slot
      createdAt: Value(now),
    ));
  }

  /// Remove an asset from a cell and compact z_order of remaining slots.
  Future<void> removeAsset(int mapId, int q, int r, int assetId) async {
    await (delete(mapCellAssets)
          ..where((ca) =>
              ca.mapId.equals(mapId) &
              ca.q.equals(q) &
              ca.r.equals(r) &
              ca.assetId.equals(assetId)))
        .go();

    // Recompact z_order to keep slots contiguous
    final remaining = await (select(mapCellAssets)
          ..where((ca) =>
              ca.mapId.equals(mapId) & ca.q.equals(q) & ca.r.equals(r))
          ..orderBy([(ca) => OrderingTerm.asc(ca.zOrder)]))
        .get();

    for (int i = 0; i < remaining.length; i++) {
      await (update(mapCellAssets)
            ..where((ca) => ca.id.equals(remaining[i].id)))
          .write(MapCellAssetsCompanion(zOrder: Value(i)));
    }
  }
}
