// SubjectRow, SubjectOptionRow, SubjectResolutionRow are Drift-generated data classes.
// They're exported via database.dart which includes the generated database.g.dart.
import '../data/database.dart';

/// Enriched subject model for display — includes options, best resolution,
/// and denormalized fields from joined tables.
class SubjectWithDetails {
  final SubjectRow subject;

  /// Turn ID and number from source_turn (joined from turn_turns)
  final int sourceTurnId;
  final int sourceTurnNumber;

  /// Civilization name (joined from civ_civilizations)
  final String civName;

  /// All options defined for this subject (GM choices)
  final List<SubjectOptionRow> options;

  /// Best resolution attempt (highest confidence), null if none yet
  final SubjectResolutionRow? bestResolution;

  /// Turn number when the best resolution was detected
  final int? bestResolutionTurnNumber;

  /// Total number of resolution attempts (for "N attempts" display)
  final int resolutionCount;

  const SubjectWithDetails({
    required this.subject,
    required this.sourceTurnId,
    required this.sourceTurnNumber,
    required this.civName,
    required this.options,
    this.bestResolution,
    this.bestResolutionTurnNumber,
    this.resolutionCount = 0,
  });
}

/// Full subject detail — includes all resolutions for the detail page.
class SubjectDetail extends SubjectWithDetails {
  final List<ResolutionWithTurn> allResolutions;

  const SubjectDetail({
    required super.subject,
    required super.sourceTurnId,
    required super.sourceTurnNumber,
    required super.civName,
    required super.options,
    super.bestResolution,
    super.bestResolutionTurnNumber,
    super.resolutionCount,
    required this.allResolutions,
  });
}

/// Resolution enriched with the turn number when it was detected.
class ResolutionWithTurn {
  final SubjectResolutionRow resolution;
  final int turnId;
  final int turnNumber;

  const ResolutionWithTurn({
    required this.resolution,
    required this.turnId,
    required this.turnNumber,
  });
}
