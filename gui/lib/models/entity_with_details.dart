import '../data/database.dart';

class EntityWithDetails {
  final EntityRow entity;
  final List<String> aliases;
  final int mentionCount;

  const EntityWithDetails({
    required this.entity,
    required this.aliases,
    required this.mentionCount,
  });
}
