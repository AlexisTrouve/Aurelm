import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../models/graph_data.dart';
import '../../providers/graph_provider.dart';
import '../../providers/entity_provider.dart';
import '../../providers/database_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/empty_state.dart';
import 'widgets/ego_painter.dart';
import 'widgets/graph_legend.dart';

class GraphScreen extends ConsumerStatefulWidget {
  /// Optional: pre-select an entity on open (passed via GoRouter extra)
  final int? initialEntityId;

  const GraphScreen({super.key, this.initialEntityId});

  @override
  ConsumerState<GraphScreen> createState() => _GraphScreenState();
}

class _GraphScreenState extends ConsumerState<GraphScreen> {
  final TextEditingController _searchCtrl = TextEditingController();
  String _searchQuery = '';
  int? _hoveredNodeId;
  String? _selectedRelType;
  bool _showLegend = false;

  @override
  void initState() {
    super.initState();
    if (widget.initialEntityId != null) {
      // Pre-select entity if navigated from entity detail
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(graphSelectedEntityProvider.notifier).state = widget.initialEntityId;
      });
    }
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dbPath = ref.watch(dbPathProvider);
    if (dbPath == null) {
      return const Scaffold(
        body: EmptyState(icon: Icons.storage, message: 'No database configured'),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Graphe des relations'),
        actions: [
          // Depth toggle
          _DepthToggle(),
          // Relation type filter
          _RelTypeFilter(),
          // Legend toggle
          IconButton(
            icon: const Icon(Icons.legend_toggle),
            tooltip: 'Légende',
            onPressed: () => setState(() => _showLegend = !_showLegend),
          ),
        ],
      ),
      body: Row(
        children: [
          // Left panel — entity list
          SizedBox(
            width: 260,
            child: _EntityListPanel(
              searchQuery: _searchQuery,
              searchCtrl: _searchCtrl,
              onQueryChanged: (q) => setState(() => _searchQuery = q),
            ),
          ),
          const VerticalDivider(width: 1),
          // Right panel — ego graph canvas
          Expanded(child: _EgoGraphPanel(showLegend: _showLegend)),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Left panel — searchable entity list
// ---------------------------------------------------------------------------

class _EntityListPanel extends ConsumerWidget {
  final String searchQuery;
  final TextEditingController searchCtrl;
  final ValueChanged<String> onQueryChanged;

  const _EntityListPanel({
    required this.searchQuery,
    required this.searchCtrl,
    required this.onQueryChanged,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final entitiesAsync = ref.watch(entityListProvider);
    final selectedId = ref.watch(graphSelectedEntityProvider);

    return Column(
      children: [
        // Search field
        Padding(
          padding: const EdgeInsets.all(8),
          child: TextField(
            controller: searchCtrl,
            decoration: InputDecoration(
              hintText: 'Chercher une entité…',
              prefixIcon: const Icon(Icons.search, size: 18),
              isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              suffixIcon: searchQuery.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear, size: 16),
                      onPressed: () {
                        searchCtrl.clear();
                        onQueryChanged('');
                      },
                    )
                  : null,
            ),
            onChanged: onQueryChanged,
          ),
        ),
        // Entity list
        Expanded(
          child: entitiesAsync.when(
            loading: () => const LoadingIndicator(),
            error: (e, _) => const SizedBox.shrink(),
            data: (entities) {
              final filtered = searchQuery.isEmpty
                  ? entities
                  : entities
                      .where((e) => e.entity.canonicalName
                          .toLowerCase()
                          .contains(searchQuery.toLowerCase()))
                      .toList();

              if (filtered.isEmpty) {
                return const Center(
                  child: Text('Aucune entité', style: TextStyle(fontSize: 12)),
                );
              }

              return ListView.builder(
                itemCount: filtered.length,
                itemBuilder: (ctx, i) {
                  final e = filtered[i].entity;
                  final color = AppColors.entityColor(e.entityType);
                  final isSelected = e.id == selectedId;

                  return ListTile(
                    dense: true,
                    selected: isSelected,
                    selectedTileColor: color.withValues(alpha: 0.1),
                    leading: Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(shape: BoxShape.circle, color: color),
                    ),
                    title: Text(
                      e.canonicalName,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                      ),
                    ),
                    subtitle: Text(
                      e.entityType,
                      style: const TextStyle(fontSize: 10),
                    ),
                    onTap: () {
                      ref.read(graphSelectedEntityProvider.notifier).state = e.id;
                    },
                  );
                },
              );
            },
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Right panel — ego graph canvas with InteractiveViewer + CustomPaint
// ---------------------------------------------------------------------------

class _EgoGraphPanel extends ConsumerStatefulWidget {
  final bool showLegend;
  const _EgoGraphPanel({required this.showLegend});

  @override
  ConsumerState<_EgoGraphPanel> createState() => _EgoGraphPanelState();
}

class _EgoGraphPanelState extends ConsumerState<_EgoGraphPanel> {
  int? _hoveredId;

  @override
  Widget build(BuildContext context) {
    final selectedId = ref.watch(graphSelectedEntityProvider);
    final graphAsync = ref.watch(egoGraphDataProvider);

    if (selectedId == null) {
      return const EmptyState(
        icon: Icons.hub_outlined,
        message: 'Sélectionne une entité',
        subtitle: 'Choisis une entité dans la liste pour explorer ses relations',
      );
    }

    return graphAsync.when(
      loading: () => const LoadingIndicator(message: 'Chargement du graphe…'),
      error: (e, stack) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: SelectableText(
          'ERREUR GRAPH:\n$e\n\n$stack',
          style: const TextStyle(fontSize: 11, color: Colors.red, fontFamily: 'monospace'),
        ),
      ),
      data: (graphData) {
        if (graphData.nodes.isEmpty) {
          return const EmptyState(
            icon: Icons.hub,
            message: 'Aucune relation',
            subtitle: 'Cette entité n\'a pas encore de relations enregistrées',
          );
        }

        // LayoutBuilder wraps everything so canvasSize and layout are computed
        // once per build and passed to all handlers — no instance-variable side effects.
        return LayoutBuilder(builder: (ctx, constraints) {
          final canvasSize = Size(
            constraints.maxWidth.isFinite ? constraints.maxWidth : 1200,
            constraints.maxHeight.isFinite ? constraints.maxHeight : 800,
          );
          final layout = EgoGraphLayout.compute(canvasSize, graphData);

          return Stack(
            children: [
              InteractiveViewer(
                constrained: true,
                boundaryMargin: const EdgeInsets.all(80),
                minScale: 0.3,
                maxScale: 4.0,
                child: GestureDetector(
                  onTapUp: (details) => _handleTap(details.localPosition, graphData, layout),
                  child: MouseRegion(
                    onHover: (event) => _handleHover(event.localPosition, graphData, layout),
                    onExit: (_) { if (mounted) setState(() => _hoveredId = null); },
                    child: SizedBox.expand(
                      child: CustomPaint(
                        painter: EgoPainter(
                          data: graphData,
                          layout: layout,
                          hoveredId: _hoveredId,
                          colors: Theme.of(context).colorScheme,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              // Legend overlay
              if (widget.showLegend)
                const Positioned(right: 16, bottom: 16, child: GraphLegend()),
              // Hovered node tooltip
              if (_hoveredId != null)
                _buildTooltip(context, graphData, layout, canvasSize),
            ],
          );
        });
      },
    );
  }

  void _handleTap(Offset pos, GraphData graphData, EgoGraphLayout layout) {
    final hit = _hitTest(pos, graphData, layout);
    if (hit != null && hit != graphData.centerId) {
      ref.read(graphSelectedEntityProvider.notifier).state = hit;
    } else if (hit != null) {
      context.push('/entities/$hit');
    }
  }

  void _handleHover(Offset pos, GraphData graphData, EgoGraphLayout layout) {
    if (!mounted) return;
    final hit = _hitTest(pos, graphData, layout);
    if (hit != _hoveredId) {
      setState(() => _hoveredId = hit);
    }
  }

  int? _hitTest(Offset pos, GraphData graphData, EgoGraphLayout layout) {
    for (final node in graphData.nodes) {
      final nodePos = layout.positions[node.id];
      if (nodePos == null) continue;
      final r = EgoGraphLayout.radiusForDepth(node.depth);
      if ((pos - nodePos).distance <= r + 4) return node.id;
    }
    return null;
  }

  Widget _buildTooltip(BuildContext context, GraphData graphData, EgoGraphLayout layout, Size canvasSize) {
    final node = graphData.nodes.firstWhere(
      (n) => n.id == _hoveredId,
      orElse: () => graphData.nodes.first,
    );
    if (node.id != _hoveredId) return const SizedBox.shrink();

    final pos = layout.positions[node.id];
    if (pos == null) return const SizedBox.shrink();

    return Positioned(
      left: (pos.dx + 30).clamp(0, canvasSize.width - 160),
      top: (pos.dy - 40).clamp(0, canvasSize.height - 80),
      child: IgnorePointer(
        child: Material(
          elevation: 4,
          borderRadius: BorderRadius.circular(8),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(node.name,
                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
                Text('${node.entityType} · ${node.mentionCount} mentions',
                    style: TextStyle(
                        fontSize: 10,
                        color: Theme.of(context).colorScheme.onSurfaceVariant)),
                if (node.depth > 0)
                  Text('Clic → recentrer',
                      style: TextStyle(
                          fontSize: 9,
                          color: Theme.of(context).colorScheme.primary,
                          fontStyle: FontStyle.italic)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Depth toggle (1 / 2)
// ---------------------------------------------------------------------------

class _DepthToggle extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final depth = ref.watch(graphDepthProvider);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
      child: SegmentedButton<int>(
        segments: const [
          ButtonSegment(value: 1, label: Text('Profondeur 1')),
          ButtonSegment(value: 2, label: Text('Profondeur 2')),
        ],
        selected: {depth},
        onSelectionChanged: (s) =>
            ref.read(graphDepthProvider.notifier).state = s.first,
        style: ButtonStyle(
          visualDensity: VisualDensity.compact,
          textStyle: WidgetStateProperty.all(const TextStyle(fontSize: 11)),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Relation type filter chips
// ---------------------------------------------------------------------------

class _RelTypeFilter extends ConsumerWidget {
  static const _types = [
    'allied_with', 'enemy_of', 'trades_with', 'worships',
    'controls', 'member_of', 'part_of', 'produces', 'located_in',
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selected = ref.watch(graphRelationTypeFilterProvider);

    return PopupMenuButton<String?>(
      tooltip: 'Filtrer par type de relation',
      icon: Badge(
        isLabelVisible: selected != null,
        child: const Icon(Icons.filter_list),
      ),
      onSelected: (val) =>
          ref.read(graphRelationTypeFilterProvider.notifier).state = val,
      itemBuilder: (_) => [
        const PopupMenuItem(value: null, child: Text('Toutes les relations')),
        ..._types.map((t) => PopupMenuItem(
              value: t,
              child: Text(t.replaceAll('_', ' ')),
            )),
      ],
    );
  }
}
