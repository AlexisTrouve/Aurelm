import 'package:drift/drift.dart';

@DataClassName('RelationRow')
class EntityRelations extends Table {
  @override
  String get tableName => 'entity_relations';

  IntColumn get id => integer().autoIncrement()();
  IntColumn get sourceEntityId => integer().named('source_entity_id')();
  IntColumn get targetEntityId => integer().named('target_entity_id')();
  TextColumn get relationType => text().named('relation_type')();
  TextColumn get description => text().nullable()();
  IntColumn get turnId => integer().named('turn_id').nullable()();
  IntColumn get isActive =>
      integer().named('is_active').withDefault(const Constant(1))();
  TextColumn get createdAt => text().named('created_at')();
}
