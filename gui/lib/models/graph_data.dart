class GraphNode {
  final int id;
  final String name;
  final String entityType;
  final int mentionCount;
  final int? civId;

  const GraphNode({
    required this.id,
    required this.name,
    required this.entityType,
    required this.mentionCount,
    this.civId,
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

  const GraphData({required this.nodes, required this.edges});

  static const empty = GraphData(nodes: [], edges: []);
}
