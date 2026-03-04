// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'pipeline_dao.dart';

// ignore_for_file: type=lint
mixin _$PipelineDaoMixin on DatabaseAccessor<AurelmDatabase> {
  $PipelineRunsTable get pipelineRuns => attachedDatabase.pipelineRuns;
  PipelineDaoManager get managers => PipelineDaoManager(this);
}

class PipelineDaoManager {
  final _$PipelineDaoMixin _db;
  PipelineDaoManager(this._db);
  $$PipelineRunsTableTableManager get pipelineRuns =>
      $$PipelineRunsTableTableManager(_db.attachedDatabase, _db.pipelineRuns);
}
