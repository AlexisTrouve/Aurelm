import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/database.dart';
import '../models/map_with_details.dart';
import 'database_provider.dart';

/// Currently selected map id in the left panel selector.
final selectedMapIdProvider = StateProvider<int?>((ref) => null);

/// Currently selected cell coordinates on the canvas.
final selectedCellProvider =
    StateProvider<({int q, int r})?>((_) => null);

/// Stream of all maps, ordered by hierarchy.
final allMapsProvider = StreamProvider<List<MapRow>>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.mapDao.watchAllMaps();
});

/// Stream of enriched cells for a given map id.
final mapCellsProvider =
    StreamProvider.family<List<MapCellWithDetails>, int>((ref, mapId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.mapDao.watchCells(mapId);
});

/// Stream of events for a specific cell, keyed by (mapId, q, r).
final cellEventsProvider = StreamProvider.family<List<MapCellEventRow>,
    ({int mapId, int q, int r})>((ref, key) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.mapDao.watchCellEvents(key.mapId, key.q, key.r);
});

/// Stream of ALL assets in the library.
final allAssetsProvider = StreamProvider<List<MapAssetRow>>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.mapDao.watchAllAssets();
});

/// Stream of asset placements for one specific cell.
final cellAssetsProvider = StreamProvider.family<List<MapCellAssetRow>,
    ({int mapId, int q, int r})>((ref, key) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.mapDao.watchCellAssets(key.mapId, key.q, key.r);
});

/// Stream of all pawns for a map.
final mapPawnsProvider =
    StreamProvider.family<List<MapPawnRow>, int>((ref, mapId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.mapDao.watchMapPawns(mapId);
});

/// Stream of ALL cell-asset placements for a map.
final mapCellAssetsProvider =
    StreamProvider.family<List<MapCellAssetRow>, int>((ref, mapId) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.mapDao.watchMapCellAssets(mapId);
});
