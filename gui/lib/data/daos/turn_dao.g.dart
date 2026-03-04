// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'turn_dao.dart';

// ignore_for_file: type=lint
mixin _$TurnDaoMixin on DatabaseAccessor<AurelmDatabase> {
  $TurnTurnsTable get turnTurns => attachedDatabase.turnTurns;
  $TurnSegmentsTable get turnSegments => attachedDatabase.turnSegments;
  $CivCivilizationsTable get civCivilizations =>
      attachedDatabase.civCivilizations;
  $EntityMentionsTable get entityMentions => attachedDatabase.entityMentions;
  $EntityEntitiesTable get entityEntities => attachedDatabase.entityEntities;
  TurnDaoManager get managers => TurnDaoManager(this);
}

class TurnDaoManager {
  final _$TurnDaoMixin _db;
  TurnDaoManager(this._db);
  $$TurnTurnsTableTableManager get turnTurns =>
      $$TurnTurnsTableTableManager(_db.attachedDatabase, _db.turnTurns);
  $$TurnSegmentsTableTableManager get turnSegments =>
      $$TurnSegmentsTableTableManager(_db.attachedDatabase, _db.turnSegments);
  $$CivCivilizationsTableTableManager get civCivilizations =>
      $$CivCivilizationsTableTableManager(
          _db.attachedDatabase, _db.civCivilizations);
  $$EntityMentionsTableTableManager get entityMentions =>
      $$EntityMentionsTableTableManager(
          _db.attachedDatabase, _db.entityMentions);
  $$EntityEntitiesTableTableManager get entityEntities =>
      $$EntityEntitiesTableTableManager(
          _db.attachedDatabase, _db.entityEntities);
}
