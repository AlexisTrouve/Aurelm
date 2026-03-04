// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'relation_dao.dart';

// ignore_for_file: type=lint
mixin _$RelationDaoMixin on DatabaseAccessor<AurelmDatabase> {
  $EntityRelationsTable get entityRelations => attachedDatabase.entityRelations;
  $EntityEntitiesTable get entityEntities => attachedDatabase.entityEntities;
  $EntityMentionsTable get entityMentions => attachedDatabase.entityMentions;
  RelationDaoManager get managers => RelationDaoManager(this);
}

class RelationDaoManager {
  final _$RelationDaoMixin _db;
  RelationDaoManager(this._db);
  $$EntityRelationsTableTableManager get entityRelations =>
      $$EntityRelationsTableTableManager(
          _db.attachedDatabase, _db.entityRelations);
  $$EntityEntitiesTableTableManager get entityEntities =>
      $$EntityEntitiesTableTableManager(
          _db.attachedDatabase, _db.entityEntities);
  $$EntityMentionsTableTableManager get entityMentions =>
      $$EntityMentionsTableTableManager(
          _db.attachedDatabase, _db.entityMentions);
}
