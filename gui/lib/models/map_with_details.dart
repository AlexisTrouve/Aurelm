import '../data/database.dart';

/// A map cell enriched with join data from civs, entities, and child maps.
class MapCellWithDetails {
  final MapCellRow cell;

  /// Name of the controlling civilization, or null.
  final String? civName;

  /// Canonical name of the linked entity, or null.
  final String? entityName;

  /// Name of the child map this cell drills into, or null.
  final String? childMapName;

  const MapCellWithDetails({
    required this.cell,
    this.civName,
    this.entityName,
    this.childMapName,
  });
}
