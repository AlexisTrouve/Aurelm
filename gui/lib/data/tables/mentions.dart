import 'package:drift/drift.dart';

@DataClassName('MentionRow')
class EntityMentions extends Table {
  @override
  String get tableName => 'entity_mentions';

  IntColumn get id => integer().autoIncrement()();
  IntColumn get entityId => integer().named('entity_id')();
  IntColumn get turnId => integer().named('turn_id')();
  IntColumn get segmentId => integer().named('segment_id').nullable()();
  TextColumn get mentionText => text().named('mention_text')();
  TextColumn get context => text().nullable()();
}
