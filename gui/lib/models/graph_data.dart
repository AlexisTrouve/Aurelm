class GraphNode {
  final int id;
  final String name;
  final String entityType;
  final int mentionCount;
  final int? civId;
  /// Distance from ego center: 0 = center, 1 = direct neighbor, 2 = extended
  final int depth;

  const GraphNode({
    required this.id,
    required this.name,
    required this.entityType,
    required this.mentionCount,
    this.civId,
    this.depth = 1,
  });
}

class GraphEdge {
  final int sourceId;
  final int targetId;
  final String relationType;
  final String? description;

  const GraphEdge({
    required this.sourceId,
    required this.targetId,
    required this.relationType,
    this.description,
  });
}

class GraphData {
  final List<GraphNode> nodes;
  final List<GraphEdge> edges;
  /// ID of the ego center node (null in non-ego contexts)
  final int? centerId;

  const GraphData({required this.nodes, required this.edges, this.centerId});

  static const empty = GraphData(nodes: [], edges: []);
}
