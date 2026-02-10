import 'package:drift/drift.dart';

@DataClassName('PipelineRunRow')
class PipelineRuns extends Table {
  @override
  String get tableName => 'pipeline_runs';

  IntColumn get id => integer().autoIncrement()();
  TextColumn get startedAt => text().named('started_at')();
  TextColumn get completedAt => text().named('completed_at').nullable()();
  TextColumn get status =>
      text().withDefault(const Constant('running'))();
  IntColumn get messagesProcessed =>
      integer().named('messages_processed').nullable()();
  IntColumn get turnsCreated =>
      integer().named('turns_created').nullable()();
  IntColumn get entitiesExtracted =>
      integer().named('entities_extracted').nullable()();
  TextColumn get errorMessage => text().named('error_message').nullable()();
}
