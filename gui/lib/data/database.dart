import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';

import 'tables/civilizations.dart';
import 'tables/turns.dart';
import 'tables/entities.dart';
import 'tables/mentions.dart';
import 'tables/relations.dart';
import 'tables/pipeline_runs.dart';
import 'tables/subjects.dart';

import 'daos/civilization_dao.dart';
import 'daos/turn_dao.dart';
import 'daos/entity_dao.dart';
import 'daos/relation_dao.dart';
import 'daos/pipeline_dao.dart';
import 'daos/subject_dao.dart';

part 'database.g.dart';

@DriftDatabase(
  tables: [
    CivCivilizations,
    TurnTurns,
    TurnSegments,
    EntityEntities,
    EntityAliases,
    EntityMentions,
    EntityRelations,
    PipelineRuns,
    // Subject tracking tables (migration 006)
    SubjectSubjects,
    SubjectOptions,
    SubjectResolutions,
  ],
  daos: [
    CivilizationDao,
    TurnDao,
    EntityDao,
    RelationDao,
    PipelineDao,
    SubjectDao,
  ],
)
class AurelmDatabase extends _$AurelmDatabase {
  AurelmDatabase(super.e);

  @override
  int get schemaVersion => 2;

  static AurelmDatabase open(String dbPath) {
    return AurelmDatabase(_openConnection(dbPath));
  }
}

LazyDatabase _openConnection(String dbPath) {
  return LazyDatabase(() async {
    final file = File(dbPath);
    return NativeDatabase.createInBackground(file, setup: (db) {
      db.execute('PRAGMA foreign_keys = ON');
    });
  });
}
