import 'package:flutter_test/flutter_test.dart';

import 'package:aurelm_gui/models/graph_data.dart';

void main() {
  group('GraphData', () {
    test('empty constant has no nodes or edges', () {
      expect(GraphData.empty.nodes, isEmpty);
      expect(GraphData.empty.edges, isEmpty);
    });

    test('GraphNode stores all fields', () {
      const node = GraphNode(
        id: 1,
        name: 'Argile Vivante',
        entityType: 'technology',
        mentionCount: 15,
        civId: 1,
      );
      expect(node.id, 1);
      expect(node.name, 'Argile Vivante');
      expect(node.entityType, 'technology');
      expect(node.mentionCount, 15);
      expect(node.civId, 1);
    });

    test('GraphEdge stores all fields', () {
      const edge = GraphEdge(
        sourceId: 1,
        targetId: 2,
        relationType: 'created_by',
        description: 'Invented by the caste',
      );
      expect(edge.sourceId, 1);
      expect(edge.targetId, 2);
      expect(edge.relationType, 'created_by');
      expect(edge.description, 'Invented by the caste');
    });
  });
}
