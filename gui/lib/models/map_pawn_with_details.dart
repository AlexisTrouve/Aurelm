import '../data/database.dart';

/// A pawn enriched with entity name, type, and optional asset bytes.
class MapPawnWithDetails {
  final MapPawnRow pawn;
  final String entityName;
  final String entityType;

  /// Asset bytes if the pawn has a custom icon, otherwise null.
  final List<int>? assetBytes;

  const MapPawnWithDetails({
    required this.pawn,
    required this.entityName,
    required this.entityType,
    this.assetBytes,
  });

  /// First letter of the entity name, used as fallback icon.
  String get initial =>
      entityName.isNotEmpty ? entityName[0].toUpperCase() : '?';
}
