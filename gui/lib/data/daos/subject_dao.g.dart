// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'subject_dao.dart';

// ignore_for_file: type=lint
mixin _$SubjectDaoMixin on DatabaseAccessor<AurelmDatabase> {
  $SubjectSubjectsTable get subjectSubjects => attachedDatabase.subjectSubjects;
  $SubjectOptionsTable get subjectOptions => attachedDatabase.subjectOptions;
  $SubjectResolutionsTable get subjectResolutions =>
      attachedDatabase.subjectResolutions;
  $TurnTurnsTable get turnTurns => attachedDatabase.turnTurns;
  $CivCivilizationsTable get civCivilizations =>
      attachedDatabase.civCivilizations;
  SubjectDaoManager get managers => SubjectDaoManager(this);
}

class SubjectDaoManager {
  final _$SubjectDaoMixin _db;
  SubjectDaoManager(this._db);
  $$SubjectSubjectsTableTableManager get subjectSubjects =>
      $$SubjectSubjectsTableTableManager(
          _db.attachedDatabase, _db.subjectSubjects);
  $$SubjectOptionsTableTableManager get subjectOptions =>
      $$SubjectOptionsTableTableManager(
          _db.attachedDatabase, _db.subjectOptions);
  $$SubjectResolutionsTableTableManager get subjectResolutions =>
      $$SubjectResolutionsTableTableManager(
          _db.attachedDatabase, _db.subjectResolutions);
  $$TurnTurnsTableTableManager get turnTurns =>
      $$TurnTurnsTableTableManager(_db.attachedDatabase, _db.turnTurns);
  $$CivCivilizationsTableTableManager get civCivilizations =>
      $$CivCivilizationsTableTableManager(
          _db.attachedDatabase, _db.civCivilizations);
}
