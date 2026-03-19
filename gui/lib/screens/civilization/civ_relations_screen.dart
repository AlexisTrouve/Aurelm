import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../data/repositories/civ_relations_repository.dart';
import '../../providers/civilization_provider.dart';
import '../../providers/database_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/section_header.dart';

/// Full-screen inter-civ relation map.
///
/// Top half: CustomPainter graph — civ nodes arranged in a circle,
/// directed edges colored by opinion. Tap an edge to highlight the
/// corresponding relation card below.
///
/// Bottom half: scrollable list of relation cards with description + treaties.
class CivRelationsScreen extends ConsumerStatefulWidget {
  /// When set, the graph highlights this civ and the list scrolls to its relations.
  final int? focusCivId;

  const CivRelationsScreen({super.key, this.focusCivId});

  @override
  ConsumerState<CivRelationsScreen> createState() => _CivRelationsScreenState();
}

class _CivRelationsScreenState extends ConsumerState<CivRelationsScreen> {
  int? _highlightedRelationId;
  final _scrollCtrl = ScrollController();
  // Key per relation card for scroll-to on tap
  final _cardKeys = <int, GlobalKey>{};

  @override
  void dispose() {
    _scrollCtrl.dispose();
    super.dispose();
  }

  void _onEdgeTap(int relationId) {
    // Navigate directly to the relation detail screen
    context.push('/civs/relations/$relationId');
  }

  @override
  Widget build(BuildContext context) {
    final relationsAsync = ref.watch(allCivRelationsProvider);
    final civsAsync = ref.watch(civListProvider);

    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 44,
        title: const Text('Relations inter-civilisations'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.canPop() ? context.pop() : context.go('/'),
        ),
      ),
      body: relationsAsync.when(
        loading: () => const LoadingIndicator(),
        error: (e, _) => ErrorView(message: e.toString()),
        data: (relations) {
          final civs = civsAsync.valueOrNull ?? [];
          if (relations.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.hub_outlined, size: 48,
                      color: Theme.of(context).colorScheme.onSurfaceVariant),
                  const SizedBox(height: 12),
                  Text('Aucune relation détectée',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text('Lancez le pipeline pour extraire les relations.',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context)
                                .colorScheme
                                .onSurfaceVariant,
                          )),
                ],
              ),
            );
          }

          // Ensure card keys exist for all relations
          for (final r in relations) {
            _cardKeys.putIfAbsent(r.id, () => GlobalKey());
          }

          // Collect all unique civ ids from relations
          final civIds = <int>{};
          for (final r in relations) {
            civIds.add(r.sourceCivId);
            civIds.add(r.targetCivId);
          }
          // Build name map from civs list; fallback to relation names
          final civNames = <int, String>{
            for (final c in civs) c.civ.id: c.civ.name,
          };
          for (final r in relations) {
            civNames.putIfAbsent(r.sourceCivId, () => r.sourceCivName);
            civNames.putIfAbsent(r.targetCivId, () => r.targetCivName);
          }

          return Column(
            children: [
              // Graph — fixed height panel
              SizedBox(
                height: 300,
                child: _RelationsGraph(
                  civIds: civIds.toList(),
                  civNames: civNames,
                  relations: relations,
                  highlightedId: _highlightedRelationId,
                  focusCivId: widget.focusCivId,
                  onEdgeTap: _onEdgeTap,
                ),
              ),

              const Divider(height: 1),

              // Relation cards — scrollable
              Expanded(
                child: ListView.separated(
                  controller: _scrollCtrl,
                  padding: const EdgeInsets.all(16),
                  itemCount: relations.length + 1, // +1 for header
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, i) {
                    if (i == 0) {
                      return const SectionHeader(title: 'Détail des relations');
                    }
                    final r = relations[i - 1];
                    // Highlight relations involving the focused civ
                    final isFocused = widget.focusCivId != null &&
                        (r.sourceCivId == widget.focusCivId ||
                            r.targetCivId == widget.focusCivId);
                    return _RelationCard(
                      key: _cardKeys[r.id],
                      relation: r,
                      highlighted: r.id == _highlightedRelationId || isFocused,
                      onTap: () => context.push('/civs/relations/${r.id}'),
                    );
                  },
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Graph widget — CustomPainter nodes + directed edges
// ---------------------------------------------------------------------------

class _RelationsGraph extends StatefulWidget {
  final List<int> civIds;
  final Map<int, String> civNames;
  final List<CivRelation> relations;
  final int? highlightedId;
  final int? focusCivId;
  final void Function(int relationId) onEdgeTap;

  const _RelationsGraph({
    required this.civIds,
    required this.civNames,
    required this.relations,
    required this.highlightedId,
    required this.focusCivId,
    required this.onEdgeTap,
  });

  @override
  State<_RelationsGraph> createState() => _RelationsGraphState();
}

class _RelationsGraphState extends State<_RelationsGraph> {
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return LayoutBuilder(
      builder: (context, constraints) {
        final size = Size(constraints.maxWidth, constraints.maxHeight);

        // Position civs in a circle
        final positions = _circlePositions(size, widget.civIds);

        return GestureDetector(
          onTapUp: (details) => _handleTap(details.localPosition, positions, size),
          child: CustomPaint(
            size: size,
            painter: _GraphPainter(
              civIds: widget.civIds,
              civNames: widget.civNames,
              positions: positions,
              relations: widget.relations,
              highlightedId: widget.highlightedId,
              focusCivId: widget.focusCivId,
              isDark: Theme.of(context).brightness == Brightness.dark,
              primaryColor: cs.primary,
              surfaceColor: cs.surfaceContainerHighest,
              onSurfaceColor: cs.onSurface,
            ),
          ),
        );
      },
    );
  }

  /// Place civs evenly around a circle, with a margin from edges.
  Map<int, Offset> _circlePositions(Size size, List<int> civIds) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = min(cx, cy) * 0.62;
    final n = civIds.length;
    final result = <int, Offset>{};
    for (var i = 0; i < n; i++) {
      // Start at top (-π/2) and go clockwise
      final angle = -pi / 2 + 2 * pi * i / n;
      result[civIds[i]] = Offset(cx + r * cos(angle), cy + r * sin(angle));
    }
    return result;
  }

  void _handleTap(
      Offset tap, Map<int, Offset> positions, Size size) {
    // Check if tap is near any edge midpoint
    for (final r in widget.relations) {
      final src = positions[r.sourceCivId];
      final tgt = positions[r.targetCivId];
      if (src == null || tgt == null) continue;
      final mid = Offset((src.dx + tgt.dx) / 2, (src.dy + tgt.dy) / 2);
      if ((tap - mid).distance < 24) {
        widget.onEdgeTap(r.id);
        return;
      }
    }
  }
}

// ---------------------------------------------------------------------------
// CustomPainter — draws edges + nodes
// ---------------------------------------------------------------------------

class _GraphPainter extends CustomPainter {
  final List<int> civIds;
  final Map<int, String> civNames;
  final Map<int, Offset> positions;
  final List<CivRelation> relations;
  final int? highlightedId;
  final int? focusCivId;
  final bool isDark;
  final Color primaryColor;
  final Color surfaceColor;
  final Color onSurfaceColor;

  static const _nodeRadius = 40.0;
  static const _arrowSize = 8.0;

  static const _opinionColors = <String, Color>{
    'allied':     Color(0xFF4CAF50),
    'friendly':   Color(0xFF8BC34A),
    'neutral':    Color(0xFF9E9E9E),
    'suspicious': Color(0xFFFF9800),
    'hostile':    Color(0xFFF44336),
    'unknown':    Color(0xFF757575),
  };

  static const _opinionLabels = <String, String>{
    'allied':     'Allié',
    'friendly':   'Favorable',
    'neutral':    'Neutre',
    'suspicious': 'Méfiant',
    'hostile':    'Hostile',
    'unknown':    'Inconnu',
  };

  _GraphPainter({
    required this.civIds,
    required this.civNames,
    required this.positions,
    required this.relations,
    required this.highlightedId,
    required this.focusCivId,
    required this.isDark,
    required this.primaryColor,
    required this.surfaceColor,
    required this.onSurfaceColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    _drawEdges(canvas);
    _drawNodes(canvas);
  }

  void _drawEdges(Canvas canvas) {
    for (final r in relations) {
      final src = positions[r.sourceCivId];
      final tgt = positions[r.targetCivId];
      if (src == null || tgt == null) continue;

      final color = _opinionColors[r.opinion] ?? _opinionColors['unknown']!;
      final isHighlighted = r.id == highlightedId;
      final strokeWidth = isHighlighted ? 3.0 : 2.0;
      final alpha = isHighlighted ? 1.0 : 0.7;

      final paint = Paint()
        ..color = color.withValues(alpha: alpha)
        ..strokeWidth = strokeWidth
        ..style = PaintingStyle.stroke;

      // Direction vector from src to tgt
      final dir = (tgt - src);
      final len = dir.distance;
      if (len < 1) continue;
      final unit = dir / len;

      // Start and end points at node borders
      final start = src + unit * _nodeRadius;
      final end = tgt - unit * _nodeRadius;

      // Draw line
      canvas.drawLine(start, end, paint);

      // Arrowhead at end
      _drawArrow(canvas, end, unit, color.withValues(alpha: alpha), strokeWidth);

      // Opinion label at midpoint
      final mid = Offset((start.dx + end.dx) / 2, (start.dy + end.dy) / 2);
      _drawLabel(
        canvas,
        _opinionLabels[r.opinion] ?? r.opinion,
        mid,
        color,
        isHighlighted,
      );
    }
  }

  void _drawArrow(Canvas canvas, Offset tip, Offset dir, Color color, double sw) {
    final perp = Offset(-dir.dy, dir.dx);
    final p1 = tip - dir * _arrowSize + perp * (_arrowSize * 0.5);
    final p2 = tip - dir * _arrowSize - perp * (_arrowSize * 0.5);

    final path = Path()
      ..moveTo(tip.dx, tip.dy)
      ..lineTo(p1.dx, p1.dy)
      ..lineTo(p2.dx, p2.dy)
      ..close();

    canvas.drawPath(path, Paint()..color = color..style = PaintingStyle.fill);
  }

  void _drawLabel(Canvas canvas, String text, Offset center, Color color, bool bold) {
    final tp = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
          fontSize: 11,
          fontWeight: bold ? FontWeight.w700 : FontWeight.w500,
          color: color,
          shadows: [
            Shadow(
              color: isDark ? Colors.black87 : Colors.white,
              blurRadius: 4,
            ),
          ],
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(
      canvas,
      center - Offset(tp.width / 2, tp.height / 2),
    );
  }

  void _drawNodes(Canvas canvas) {
    for (final civId in civIds) {
      final pos = positions[civId];
      if (pos == null) continue;
      final name = civNames[civId] ?? '?';
      final isFocused = civId == focusCivId;

      // Node circle
      final bgPaint = Paint()
        ..color = isFocused
            ? primaryColor.withValues(alpha: 0.18)
            : surfaceColor
        ..style = PaintingStyle.fill;
      final borderPaint = Paint()
        ..color = isFocused ? primaryColor : primaryColor.withValues(alpha: 0.6)
        ..strokeWidth = isFocused ? 3.0 : 2.0
        ..style = PaintingStyle.stroke;

      canvas.drawCircle(pos, _nodeRadius, bgPaint);
      canvas.drawCircle(pos, _nodeRadius, borderPaint);

      // Civ name inside node (2 lines if long)
      final tp = TextPainter(
        text: TextSpan(
          text: name,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: onSurfaceColor,
          ),
        ),
        textDirection: TextDirection.ltr,
        textAlign: TextAlign.center,
        maxLines: 2,
        ellipsis: '…',
      )..layout(maxWidth: _nodeRadius * 1.7);
      tp.paint(
        canvas,
        pos - Offset(tp.width / 2, tp.height / 2),
      );
    }
  }

  @override
  bool shouldRepaint(_GraphPainter old) =>
      old.highlightedId != highlightedId ||
      old.relations != relations ||
      old.civIds != civIds;
}

// ---------------------------------------------------------------------------
// GM lock button — shared between relations and alias screens
// ---------------------------------------------------------------------------

/// Amber lock icon that toggles gm_lock on a relation or alias row.
/// When locked, the pipeline will not overwrite this entry.
class _GmLockButton extends StatelessWidget {
  final bool locked;
  final VoidCallback onToggle;

  const _GmLockButton({required this.locked, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: locked ? 'Verrouillé (pipeline ignorera)' : 'Verrouiller contre le pipeline',
      child: InkWell(
        onTap: onToggle,
        borderRadius: BorderRadius.circular(4),
        child: Padding(
          padding: const EdgeInsets.all(3),
          child: Icon(
            locked ? Icons.lock : Icons.lock_open,
            size: 14,
            color: locked ? Colors.amber : Colors.grey,
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Relation detail card
// ---------------------------------------------------------------------------

class _RelationCard extends ConsumerWidget {
  final CivRelation relation;
  final bool highlighted;
  final VoidCallback onTap;

  const _RelationCard({
    super.key,
    required this.relation,
    required this.highlighted,
    required this.onTap,
  });

  static const _opinionColors = <String, Color>{
    'allied':     Color(0xFF4CAF50),
    'friendly':   Color(0xFF8BC34A),
    'neutral':    Color(0xFF9E9E9E),
    'suspicious': Color(0xFFFF9800),
    'hostile':    Color(0xFFF44336),
    'unknown':    Color(0xFF757575),
  };

  static const _opinionLabels = <String, String>{
    'allied':     'Allié',
    'friendly':   'Favorable',
    'neutral':    'Neutre',
    'suspicious': 'Méfiant',
    'hostile':    'Hostile',
    'unknown':    'Inconnu',
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final color = _opinionColors[relation.opinion] ?? _opinionColors['unknown']!;
    final label = _opinionLabels[relation.opinion] ?? relation.opinion;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: highlighted ? color : cs.outlineVariant,
          width: highlighted ? 2 : 1,
        ),
        color: highlighted
            ? color.withValues(alpha: 0.06)
            : cs.surfaceContainerLowest,
        boxShadow: highlighted
            ? [BoxShadow(color: color.withValues(alpha: 0.15), blurRadius: 8)]
            : null,
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header: source → target + opinion chip
              Row(
                children: [
                  // Navigate to source civ on tap
                  InkWell(
                    onTap: () => context.push('/civs/${relation.sourceCivId}'),
                    child: Text(
                      relation.sourceCivName,
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: cs.primary,
                        decoration: TextDecoration.underline,
                        decorationColor: cs.primary.withValues(alpha: 0.4),
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6),
                    child: Icon(Icons.arrow_forward,
                        size: 14, color: cs.onSurfaceVariant),
                  ),
                  InkWell(
                    onTap: () => context.push('/civs/${relation.targetCivId}'),
                    child: Text(
                      relation.targetCivName,
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: cs.primary,
                        decoration: TextDecoration.underline,
                        decorationColor: cs.primary.withValues(alpha: 0.4),
                      ),
                    ),
                  ),
                  const Spacer(),
                  // GM lock button — prevents pipeline from overwriting this relation
                  _GmLockButton(
                    locked: relation.gmLock,
                    onToggle: () {
                      final db = ref.read(databaseProvider);
                      if (db != null) CivRelationsRepository(db).toggleLock(relation.id);
                    },
                  ),
                  const SizedBox(width: 6),
                  // Opinion chip
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: color.withValues(alpha: 0.4)),
                    ),
                    child: Text(
                      label,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: color,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),

              // LLM description
              if (relation.description != null &&
                  relation.description!.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text(
                  relation.description!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: cs.onSurface,
                    height: 1.6,
                  ),
                ),
              ],

              // Treaties
              if (relation.treaties.isNotEmpty) ...[
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: relation.treaties
                      .map((t) => Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: cs.surfaceContainerHighest,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.handshake_outlined,
                                    size: 11,
                                    color: cs.onSurfaceVariant),
                                const SizedBox(width: 4),
                                Text(t,
                                    style: theme.textTheme.labelSmall
                                        ?.copyWith(
                                            color: cs.onSurfaceVariant)),
                              ],
                            ),
                          ))
                      .toList(),
                ),
              ],

              // Footer: mentions + last turn
              const SizedBox(height: 8),
              Row(
                children: [
                  if (relation.mentionCount > 0)
                    Text(
                      '${relation.mentionCount} mention${relation.mentionCount > 1 ? 's' : ''}',
                      style: theme.textTheme.labelSmall
                          ?.copyWith(color: cs.onSurfaceVariant),
                    ),
                  if (relation.mentionCount > 0 &&
                      relation.lastTurnNumber != null)
                    Text(' · ',
                        style: theme.textTheme.labelSmall
                            ?.copyWith(color: cs.onSurfaceVariant)),
                  if (relation.lastTurnNumber != null)
                    Text(
                      'Dernier tour : ${relation.lastTurnNumber}',
                      style: theme.textTheme.labelSmall
                          ?.copyWith(color: cs.onSurfaceVariant),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
