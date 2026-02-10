import '../data/database.dart';

class TurnWithEntities {
  final TurnRow turn;
  final String civName;
  final int entityCount;
  final List<String> segmentTypes;

  const TurnWithEntities({
    required this.turn,
    required this.civName,
    required this.entityCount,
    required this.segmentTypes,
  });
}
