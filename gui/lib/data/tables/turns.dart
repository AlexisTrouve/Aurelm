import 'package:drift/drift.dart';

@DataClassName('TurnRow')
class TurnTurns extends Table {
  @override
  String get tableName => 'turn_turns';

  IntColumn get id => integer().autoIncrement()();
  IntColumn get civId => integer().named('civ_id')();
  IntColumn get turnNumber => integer().named('turn_number')();
  TextColumn get title => text().nullable()();
  TextColumn get summary => text().nullable()();
  TextColumn get rawMessageIds => text().named('raw_message_ids')();
  TextColumn get turnType =>
      text().named('turn_type').withDefault(const Constant('standard'))();
  TextColumn get gameDateStart => text().named('game_date_start').nullable()();
  TextColumn get gameDateEnd => text().named('game_date_end').nullable()();
  TextColumn get createdAt => text().named('created_at')();
  TextColumn get processedAt => text().named('processed_at').nullable()();
}

@DataClassName('SegmentRow')
class TurnSegments extends Table {
  @override
  String get tableName => 'turn_segments';

  IntColumn get id => integer().autoIncrement()();
  IntColumn get turnId => integer().named('turn_id')();
  IntColumn get segmentOrder => integer().named('segment_order')();
  TextColumn get segmentType => text().named('segment_type')();
  TextColumn get content => text()();
}
