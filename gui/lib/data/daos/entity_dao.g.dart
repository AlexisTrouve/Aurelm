// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'entity_dao.dart';

// ignore_for_file: type=lint
mixin _$EntityDaoMixin on DatabaseAccessor<AurelmDatabase> {
  $EntityEntitiesTable get entityEntities => attachedDatabase.entityEntities;
  $EntityAliasesTable get entityAliases => attachedDatabase.entityAliases;
  $EntityMentionsTable get entityMentions => attachedDatabase.entityMentions;
  $CivCivilizationsTable get civCivilizations =>
      attachedDatabase.civCivilizations;
  $TurnTurnsTable get turnTurns => attachedDatabase.turnTurns;
  EntityDaoManager get managers => EntityDaoManager(this);
}

class EntityDaoManager {
  final _$EntityDaoMixin _db;
  EntityDaoManager(this._db);
  $$EntityEntitiesTableTableManager get entityEntities =>
      $$EntityEntitiesTableTableManager(
          _db.attachedDatabase, _db.entityEntities);
  $$EntityAliasesTableTableManager get entityAliases =>
      $$EntityAliasesTableTableManager(_db.attachedDatabase, _db.entityAliases);
  $$EntityMentionsTableTableManager get entityMentions =>
      $$EntityMentionsTableTableManager(
          _db.attachedDatabase, _db.entityMentions);
  $$CivCivilizationsTableTableManager get civCivilizations =>
      $$CivCivilizationsTableTableManager(
          _db.attachedDatabase, _db.civCivilizations);
  $$TurnTurnsTableTableManager get turnTurns =>
      $$TurnTurnsTableTableManager(_db.attachedDatabase, _db.turnTurns);
}
