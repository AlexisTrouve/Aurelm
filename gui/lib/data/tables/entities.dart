import 'package:drift/drift.dart';

@DataClassName('EntityRow')
class EntityEntities extends Table {
  @override
  String get tableName => 'entity_entities';

  IntColumn get id => integer().autoIncrement()();
  TextColumn get canonicalName => text().named('canonical_name')();
  TextColumn get entityType => text().named('entity_type')();
  IntColumn get civId => integer().named('civ_id').nullable()();
  TextColumn get description => text().nullable()();
  IntColumn get firstSeenTurn =>
      integer().named('first_seen_turn').nullable()();
  IntColumn get lastSeenTurn => integer().named('last_seen_turn').nullable()();
  IntColumn get isActive =>
      integer().named('is_active').withDefault(const Constant(1))();
  TextColumn get createdAt => text().named('created_at')();
  TextColumn get updatedAt => text().named('updated_at')();
}

@DataClassName('AliasRow')
class EntityAliases extends Table {
  @override
  String get tableName => 'entity_aliases';

  IntColumn get id => integer().autoIncrement()();
  IntColumn get entityId => integer().named('entity_id')();
  TextColumn get alias => text()();
}
