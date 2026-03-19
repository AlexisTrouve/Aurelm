// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'map_dao.dart';

// ignore_for_file: type=lint
mixin _$MapDaoMixin on DatabaseAccessor<AurelmDatabase> {
  $MapMapsTable get mapMaps => attachedDatabase.mapMaps;
  $MapCellsTable get mapCells => attachedDatabase.mapCells;
  $MapCellEventsTable get mapCellEvents => attachedDatabase.mapCellEvents;
  $MapAssetsTable get mapAssets => attachedDatabase.mapAssets;
  $MapCellAssetsTable get mapCellAssets => attachedDatabase.mapCellAssets;
  $CivCivilizationsTable get civCivilizations =>
      attachedDatabase.civCivilizations;
  $EntityEntitiesTable get entityEntities => attachedDatabase.entityEntities;
  MapDaoManager get managers => MapDaoManager(this);
}

class MapDaoManager {
  final _$MapDaoMixin _db;
  MapDaoManager(this._db);
  $$MapMapsTableTableManager get mapMaps =>
      $$MapMapsTableTableManager(_db.attachedDatabase, _db.mapMaps);
  $$MapCellsTableTableManager get mapCells =>
      $$MapCellsTableTableManager(_db.attachedDatabase, _db.mapCells);
  $$MapCellEventsTableTableManager get mapCellEvents =>
      $$MapCellEventsTableTableManager(_db.attachedDatabase, _db.mapCellEvents);
  $$MapAssetsTableTableManager get mapAssets =>
      $$MapAssetsTableTableManager(_db.attachedDatabase, _db.mapAssets);
  $$MapCellAssetsTableTableManager get mapCellAssets =>
      $$MapCellAssetsTableTableManager(_db.attachedDatabase, _db.mapCellAssets);
  $$CivCivilizationsTableTableManager get civCivilizations =>
      $$CivCivilizationsTableTableManager(
          _db.attachedDatabase, _db.civCivilizations);
  $$EntityEntitiesTableTableManager get entityEntities =>
      $$EntityEntitiesTableTableManager(
          _db.attachedDatabase, _db.entityEntities);
}
