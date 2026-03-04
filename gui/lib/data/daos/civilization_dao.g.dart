// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'civilization_dao.dart';

// ignore_for_file: type=lint
mixin _$CivilizationDaoMixin on DatabaseAccessor<AurelmDatabase> {
  $CivCivilizationsTable get civCivilizations =>
      attachedDatabase.civCivilizations;
  $TurnTurnsTable get turnTurns => attachedDatabase.turnTurns;
  $EntityEntitiesTable get entityEntities => attachedDatabase.entityEntities;
  CivilizationDaoManager get managers => CivilizationDaoManager(this);
}

class CivilizationDaoManager {
  final _$CivilizationDaoMixin _db;
  CivilizationDaoManager(this._db);
  $$CivCivilizationsTableTableManager get civCivilizations =>
      $$CivCivilizationsTableTableManager(
          _db.attachedDatabase, _db.civCivilizations);
  $$TurnTurnsTableTableManager get turnTurns =>
      $$TurnTurnsTableTableManager(_db.attachedDatabase, _db.turnTurns);
  $$EntityEntitiesTableTableManager get entityEntities =>
      $$EntityEntitiesTableTableManager(
          _db.attachedDatabase, _db.entityEntities);
}
