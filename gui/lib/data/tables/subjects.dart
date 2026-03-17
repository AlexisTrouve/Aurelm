import 'package:drift/drift.dart';

/// Drift table for subject_subjects — open/resolved threads between MJ and PJ.
@DataClassName('SubjectRow')
class SubjectSubjects extends Table {
  @override
  String get tableName => 'subject_subjects';

  IntColumn get id => integer().autoIncrement()();
  IntColumn get civId => integer().named('civ_id')();
  /// Nullable: NULL for GM-created subjects not tied to a specific pipeline turn.
  IntColumn get sourceTurnId => integer().named('source_turn_id').nullable()();

  /// 'mj_to_pj' = GM poses a choice; 'pj_to_mj' = player takes an initiative
  TextColumn get direction => text()();

  TextColumn get title => text()();
  TextColumn get description => text().nullable()();

  /// Verbatim phrase from the source turn text — used for auto-highlight on navigation.
  TextColumn get sourceQuote => text().named('source_quote').nullable()();

  /// 'choice' | 'question' | 'initiative' | 'request'
  TextColumn get category => text()();

  /// 'open' | 'resolved' | 'superseded' | 'abandoned'
  TextColumn get status =>
      text().withDefault(const Constant('open'))();

  /// JSON array of domain tags auto-assigned by the pipeline, e.g. ["militaire","politique"]
  TextColumn get tags => text().withDefault(const Constant('[]'))();

  TextColumn get createdAt => text().named('created_at')();
  TextColumn get updatedAt => text().named('updated_at')();
}

/// Options proposed by the GM for mj_to_pj subjects (e.g. the numbered choices).
@DataClassName('SubjectOptionRow')
class SubjectOptions extends Table {
  @override
  String get tableName => 'subject_options';

  IntColumn get id => integer().autoIncrement()();
  IntColumn get subjectId => integer().named('subject_id')();
  IntColumn get optionNumber => integer().named('option_number')();
  TextColumn get label => text()();
  TextColumn get description => text().nullable()();

  /// 1 = free-form "libre" option
  BoolColumn get isLibre =>
      boolean().named('is_libre').withDefault(const Constant(false))();
}

/// Each attempt by the pipeline to match/resolve a subject against PJ/MJ text.
/// All attempts stored (even below confidence threshold) for transparency.
@DataClassName('SubjectResolutionRow')
class SubjectResolutions extends Table {
  @override
  String get tableName => 'subject_resolutions';

  IntColumn get id => integer().autoIncrement()();
  IntColumn get subjectId => integer().named('subject_id')();
  IntColumn get resolvedByTurnId => integer().named('resolved_by_turn_id')();
  IntColumn get chosenOptionId =>
      integer().named('chosen_option_id').nullable()();
  TextColumn get resolutionText => text().named('resolution_text')();

  /// Verbatim phrase from the player/GM text — used for auto-highlight on navigation.
  TextColumn get sourceQuote => text().named('source_quote').nullable()();

  /// 1 = player chose the free-form "libre" option
  BoolColumn get isLibre =>
      boolean().named('is_libre').withDefault(const Constant(false))();

  /// 0.0 – 1.0 confidence score from the LLM
  RealColumn get confidence =>
      real().withDefault(const Constant(0.0))();

  TextColumn get createdAt => text().named('created_at')();
}
