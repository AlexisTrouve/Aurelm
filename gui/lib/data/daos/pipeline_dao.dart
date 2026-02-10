import 'package:drift/drift.dart';

import '../database.dart';
import '../tables/pipeline_runs.dart';

part 'pipeline_dao.g.dart';

@DriftAccessor(tables: [PipelineRuns])
class PipelineDao extends DatabaseAccessor<AurelmDatabase>
    with _$PipelineDaoMixin {
  PipelineDao(super.db);

  Stream<PipelineRunRow?> watchLastRun() {
    return (select(pipelineRuns)
          ..orderBy([(t) => OrderingTerm.desc(t.id)])
          ..limit(1))
        .watchSingleOrNull();
  }
}
