import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:graphview/GraphView.dart';

import '../../core/theme/app_colors.dart';
import '../../models/graph_data.dart';
import '../../providers/graph_provider.dart';
import '../../providers/database_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/empty_state.dart';
import 'widgets/graph_node_widget.dart';
import 'widgets/graph_controls.dart';
import 'widgets/graph_legend.dart';

class GraphScreen extends ConsumerStatefulWidget {
  const GraphScreen({super.key});

  @override
  ConsumerState<GraphScreen> createState() => _GraphScreenState();
}

class _GraphScreenState extends ConsumerState<GraphScreen> {
  final _transformController = TransformationController();
  bool _showLegend = true;

  @override
  void dispose() {
    _transformController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dbPath = ref.watch(dbPathProvider);
    if (dbPath == null) {
      return const Scaffold(
        body: EmptyState(
          icon: Icons.storage,
          message: 'No database configured',
        ),
      );
    }

    final graphAsync = ref.watch(graphDataProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Entity Graph'),
        actions: [
          IconButton(
            icon: Icon(_showLegend ? Icons.legend_toggle : Icons.legend_toggle_outlined),
            tooltip: 'Toggle legend',
            onPressed: () => setState(() => _showLegend = !_showLegend),
          ),
        ],
      ),
      body: Column(
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(24, 8, 24, 8),
            child: GraphControls(),
          ),
          const Divider(),
          Expanded(
            child: graphAsync.when(
              loading: () => const LoadingIndicator(message: 'Building graph...'),
              error: (e, _) => ErrorView(message: e.toString()),
              data: (graphData) {
                if (graphData.nodes.isEmpty) {
                  return const EmptyState(
                    icon: Icons.hub,
                    message: 'No entities to display',
                    subtitle: 'Try selecting a different civilization or running the pipeline',
                  );
                }
                return Stack(
                  children: [
                    _buildGraph(graphData),
                    if (_showLegend)
                      const Positioned(
                        right: 16,
                        bottom: 16,
                        child: GraphLegend(),
                      ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGraph(GraphData graphData) {
    final graph = Graph()..isTree = false;
    final nodeMap = <int, Node>{};

    for (final node in graphData.nodes) {
      final n = Node.Id(node.id);
      nodeMap[node.id] = n;
      graph.addNode(n);
    }

    for (final edge in graphData.edges) {
      final source = nodeMap[edge.sourceId];
      final target = nodeMap[edge.targetId];
      if (source != null && target != null) {
        graph.addEdge(source, target);
      }
    }

    final algorithm = FruchtermanReingoldAlgorithm(
      iterations: 100,
      attractionRate: 0.5,
      repulsionRate: 1.0,
    );

    final nodeDataMap = {for (final n in graphData.nodes) n.id: n};

    return InteractiveViewer(
      constrained: false,
      boundaryMargin: const EdgeInsets.all(200),
      minScale: 0.1,
      maxScale: 3.0,
      transformationController: _transformController,
      child: GraphView(
        graph: graph,
        algorithm: algorithm,
        paint: Paint()
          ..color = Theme.of(context).colorScheme.outlineVariant
          ..strokeWidth = 1.0
          ..style = PaintingStyle.stroke,
        builder: (Node node) {
          final id = node.key!.value as int;
          final nodeData = nodeDataMap[id];
          if (nodeData == null) return const SizedBox.shrink();

          return GraphNodeWidget(
            node: nodeData,
            onTap: () {
              // Navigate to entity detail -- could use GoRouter here
            },
          );
        },
      ),
    );
  }
}
