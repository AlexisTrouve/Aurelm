import '../data/database.dart';

class TurnWithEntities {
  final TurnRow turn;
  final String civName;
  final int entityCount;      // total = gmEntityCount + pjEntityCount
  final int gmEntityCount;    // mentions avec source='gm'
  final int pjEntityCount;    // mentions avec source='pj'
  final List<String> segmentTypes;
  final bool hasPjContent;    // true si au moins un segment source='pj' existe

  const TurnWithEntities({
    required this.turn,
    required this.civName,
    required this.entityCount,
    required this.gmEntityCount,
    required this.pjEntityCount,
    required this.segmentTypes,
    required this.hasPjContent,
  });
}
