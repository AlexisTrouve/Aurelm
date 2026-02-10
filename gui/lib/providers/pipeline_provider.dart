import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/database.dart';
import 'database_provider.dart';

final lastPipelineRunProvider = StreamProvider<PipelineRunRow?>((ref) {
  final db = ref.watch(databaseProvider);
  if (db == null) return const Stream.empty();
  return db.pipelineDao.watchLastRun();
});
