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
  TextColumn get detailedSummary => text().named('detailed_summary').nullable()();
  TextColumn get rawMessageIds => text().named('raw_message_ids')();
  TextColumn get turnType =>
      text().named('turn_type').withDefault(const Constant('standard'))();
  TextColumn get gameDateStart => text().named('game_date_start').nullable()();
  TextColumn get gameDateEnd => text().named('game_date_end').nullable()();
  TextColumn get createdAt => text().named('created_at')();
  TextColumn get processedAt => text().named('processed_at').nullable()();
  // Analysis tags — JSON arrays stored as text
  TextColumn get thematicTags => text().named('thematic_tags').nullable()();
  TextColumn get technologies => text().nullable()();
  TextColumn get resources => text().nullable()();
  TextColumn get beliefs => text().nullable()();
  TextColumn get geography => text().nullable()();
  TextColumn get keyEvents => text().named('key_events').nullable()();
  TextColumn get choicesMade => text().named('choices_made').nullable()();
  TextColumn get choicesProposed => text().named('choices_proposed').nullable()();
  // Tech/fantasy analysis
  TextColumn get techEra => text().named('tech_era').nullable()();
  TextColumn get fantasyLevel => text().named('fantasy_level').nullable()();
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
  // 'gm' = GM narrative, 'pj' = player response (migration 007)
  TextColumn get source =>
      text().withDefault(const Constant('gm'))();
}
