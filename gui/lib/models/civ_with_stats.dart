import '../data/database.dart';

class CivWithStats {
  final CivRow civ;
  final int turnCount;
  final int entityCount;

  const CivWithStats({
    required this.civ,
    required this.turnCount,
    required this.entityCount,
  });
}
