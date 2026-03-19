// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'map_dao.dart';

// ignore_for_file: type=lint
mixin _$MapDaoMixin on DatabaseAccessor<AurelmDatabase> {
  $MapMapsTable get mapMaps => attachedDatabase.mapMaps;
  $MapCellsTable get mapCells => attachedDatabase.mapCells;
  $MapCellEventsTable get mapCellEvents => attachedDatabase.mapCellEvents;
  $MapAssetsTable get mapAssets => attachedDatabase.mapAssets;
  $MapCellAssetsTable get mapCellAssets => attachedDatabase.mapCellAssets;
  $MapEntityPawnsTable get mapEntityPawns => attachedDatabase.mapEntityPawns;
  $MapCellEntitiesTable get mapCellEntities => attachedDatabase.mapCellEntities;
  $MapCellSubjectsTable get mapCellSubjects => attachedDatabase.mapCellSubjects;
  $CivCivilizationsTable get civCivilizations =>
      attachedDatabase.civCivilizations;
  $EntityEntitiesTable get entityEntities => attachedDatabase.entityEntities;
  $SubjectSubjectsTable get subjectSubjects => attachedDatabase.subjectSubjects;
  $NotesTable get notes => attachedDatabase.notes;
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
  $$MapEntityPawnsTableTableManager get mapEntityPawns =>
      $$MapEntityPawnsTableTableManager(
          _db.attachedDatabase, _db.mapEntityPawns);
  $$MapCellEntitiesTableTableManager get mapCellEntities =>
      $$MapCellEntitiesTableTableManager(
          _db.attachedDatabase, _db.mapCellEntities);
  $$MapCellSubjectsTableTableManager get mapCellSubjects =>
      $$MapCellSubjectsTableTableManager(
          _db.attachedDatabase, _db.mapCellSubjects);
  $$CivCivilizationsTableTableManager get civCivilizations =>
      $$CivCivilizationsTableTableManager(
          _db.attachedDatabase, _db.civCivilizations);
  $$EntityEntitiesTableTableManager get entityEntities =>
      $$EntityEntitiesTableTableManager(
          _db.attachedDatabase, _db.entityEntities);
  $$SubjectSubjectsTableTableManager get subjectSubjects =>
      $$SubjectSubjectsTableTableManager(
          _db.attachedDatabase, _db.subjectSubjects);
  $$NotesTableTableManager get notes =>
      $$NotesTableTableManager(_db.attachedDatabase, _db.notes);
}
