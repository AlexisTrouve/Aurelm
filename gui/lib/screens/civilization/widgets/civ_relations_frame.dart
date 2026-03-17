import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/repositories/civ_relations_repository.dart';
import '../../../providers/civilization_provider.dart';
import '../../../widgets/common/section_header.dart';

/// Displays inter-civ relation profiles for a given civilization.
///
/// Shows outgoing relations (how this civ perceives others) and incoming
/// (how others perceive this civ). Opinion is color-coded:
///   allied/friendly → green, neutral → grey, suspicious → orange, hostile → red.
class CivRelationsFrame extends ConsumerWidget {
  final int civId;

  const CivRelationsFrame({super.key, required this.civId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final relationsAsync = ref.watch(civRelationsProvider(civId));

    return relationsAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (relations) {
        if (relations.isEmpty) return const SizedBox.shrink();

        final outgoing = relations
            .where((r) => r.sourceCivId == civId)
            .toList();
        final incoming = relations
            .where((r) => r.targetCivId == civId)
            .toList();

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 28),
            const SectionHeader(title: 'Relations inter-civs'),
            const SizedBox(height: 12),

            if (outgoing.isNotEmpty) ...[
              Text(
                'Notre vision',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const SizedBox(height: 8),
              ...outgoing.map((r) => _RelationCard(
                    relation: r,
                    perspective: _Perspective.outgoing,
                    currentCivId: civId,
                  )),
            ],

            if (incoming.isNotEmpty) ...[
              if (outgoing.isNotEmpty) const SizedBox(height: 16),
              Text(
                'Leur vision de nous',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const SizedBox(height: 8),
              ...incoming.map((r) => _RelationCard(
                    relation: r,
                    perspective: _Perspective.incoming,
                    currentCivId: civId,
                  )),
            ],
          ],
        );
      },
    );
  }
}

enum _Perspective { outgoing, incoming }

class _RelationCard extends StatelessWidget {
  final CivRelation relation;
  final _Perspective perspective;
  final int currentCivId;

  const _RelationCard({
    required this.relation,
    required this.perspective,
    required this.currentCivId,
  });

  // Opinion → display label + color
  static const _opinionColors = <String, Color>{
    'allied':     Color(0xFF4CAF50), // green
    'friendly':   Color(0xFF8BC34A), // light green
    'neutral':    Color(0xFF9E9E9E), // grey
    'suspicious': Color(0xFFFF9800), // orange
    'hostile':    Color(0xFFF44336), // red
    'unknown':    Color(0xFF757575), // dark grey
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
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final color = _opinionColors[relation.opinion] ?? _opinionColors['unknown']!;
    final label = _opinionLabels[relation.opinion] ?? relation.opinion;

    // Show the "other" civ name regardless of direction
    final otherName = perspective == _Perspective.outgoing
        ? relation.targetCivName
        : relation.sourceCivName;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: civ name + opinion chip
          Row(
            children: [
              Expanded(
                child: Text(
                  otherName,
                  style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
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

          // Description
          if (relation.description != null &&
              relation.description!.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              relation.description!,
              style: theme.textTheme.bodySmall?.copyWith(
                    color: cs.onSurface,
                    height: 1.5,
                  ),
            ),
          ],

          // Treaties list
          if (relation.treaties.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: relation.treaties.map((t) => Container(
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
                        Text(
                          t,
                          style: theme.textTheme.labelSmall?.copyWith(
                                color: cs.onSurfaceVariant,
                              ),
                        ),
                      ],
                    ),
                  )).toList(),
            ),
          ],

          // Footer: mention count + last turn
          const SizedBox(height: 6),
          Row(
            children: [
              if (relation.mentionCount > 0)
                Text(
                  '${relation.mentionCount} mention${relation.mentionCount > 1 ? 's' : ''}',
                  style: theme.textTheme.labelSmall?.copyWith(
                        color: cs.onSurfaceVariant,
                      ),
                ),
              if (relation.mentionCount > 0 && relation.lastTurnNumber != null)
                Text(' · ',
                    style: theme.textTheme.labelSmall?.copyWith(
                          color: cs.onSurfaceVariant,
                        )),
              if (relation.lastTurnNumber != null)
                Text(
                  'Tour ${relation.lastTurnNumber}',
                  style: theme.textTheme.labelSmall?.copyWith(
                        color: cs.onSurfaceVariant,
                      ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
