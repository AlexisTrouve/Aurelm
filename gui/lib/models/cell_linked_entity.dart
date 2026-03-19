/// Entity linked to a map cell, enriched with name and type from entity_entities.
class CellLinkedEntity {
  final int cellEntityId; // map_cell_entities.id
  final int entityId;
  final String entityName;
  final String entityType;

  const CellLinkedEntity({
    required this.cellEntityId,
    required this.entityId,
    required this.entityName,
    required this.entityType,
  });
}
