import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../data/database.dart';
import '../../providers/turn_provider.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/section_header.dart';

/// Full turn detail — shows title, summary, and all classified segments.
/// Navigated to from the timeline when a turn card is tapped.
class TurnDetailScreen extends ConsumerWidget {
  final int turnId;

  const TurnDetailScreen({super.key, required this.turnId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dataAsync = ref.watch(turnDetailDataProvider(turnId));

    return dataAsync.when(
      loading: () => const Scaffold(body: LoadingIndicator()),
      error: (e, _) => Scaffold(body: ErrorView(message: e.toString())),
      data: (data) {
        if (data == null) {
          return Scaffold(
            appBar: AppBar(),
            body: const Center(child: Text('Tour introuvable')),
          );
        }

        final t = data.turn;
        final typeColor =
            AppColors.turnTypeColors[t.turnType] ?? Colors.grey;

        // Split segments by source (migration 007: 'gm' vs 'pj')
        final gmSegs =
            data.segments.where((s) => s.source == 'gm').toList();
        final pjSegs =
            data.segments.where((s) => s.source == 'pj').toList();

        return Scaffold(
          appBar: AppBar(
            title: Text(t.title ?? 'Tour ${t.turnNumber}',
                overflow: TextOverflow.ellipsis),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.go('/timeline'),
            ),
          ),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header metadata row
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    // Turn number badge
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: typeColor.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'Tour ${t.turnNumber}',
                        style: Theme.of(context)
                            .textTheme
                            .labelLarge
                            ?.copyWith(
                                color: typeColor,
                                fontWeight: FontWeight.bold),
                      ),
                    ),
                    // Type badge
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: typeColor.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                            color: typeColor.withValues(alpha: 0.4)),
                      ),
                      child: Text(
                        t.turnType.replaceAll('_', ' '),
                        style: Theme.of(context)
                            .textTheme
                            .labelSmall
                            ?.copyWith(color: typeColor),
                      ),
                    ),
                    // Civ badge
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Theme.of(context)
                            .colorScheme
                            .surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        data.civName,
                        style: Theme.of(context)
                            .textTheme
                            .labelSmall
                            ?.copyWith(
                                color: Theme.of(context)
                                    .colorScheme
                                    .onSurfaceVariant),
                      ),
                    ),
                    // Entity count
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Theme.of(context)
                            .colorScheme
                            .surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '${data.entityCount} entités',
                        style: Theme.of(context)
                            .textTheme
                            .labelSmall
                            ?.copyWith(
                                color: Theme.of(context)
                                    .colorScheme
                                    .onSurfaceVariant),
                      ),
                    ),
                  ],
                ),

                // Summary (condensed AI summary)
                if (t.summary != null && t.summary!.isNotEmpty) ...[
                  const SizedBox(height: 20),
                  const SectionHeader(title: 'Résumé'),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Theme.of(context)
                          .colorScheme
                          .surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      t.summary!,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontStyle: FontStyle.italic,
                          ),
                    ),
                  ),
                ],

                // GM narrative segments
                if (gmSegs.isNotEmpty) ...[
                  const SizedBox(height: 24),
                  const SectionHeader(title: 'Tour MJ'),
                  const SizedBox(height: 8),
                  ...gmSegs.map((seg) => _SegmentCard(segment: seg)),
                ],

                // PJ response segments (migration 007 fusion)
                if (pjSegs.isNotEmpty) ...[
                  const SizedBox(height: 24),
                  const SectionHeader(title: 'Réponse Joueur'),
                  const SizedBox(height: 8),
                  ...pjSegs.map((seg) => _SegmentCard(
                        segment: seg,
                        isPj: true,
                      )),
                ],

                // Fallback: segments with no source distinction (pre-migration)
                if (gmSegs.isEmpty && pjSegs.isEmpty && data.segments.isNotEmpty) ...[
                  const SizedBox(height: 24),
                  const SectionHeader(title: 'Contenu du tour'),
                  const SizedBox(height: 8),
                  ...data.segments.map((seg) => _SegmentCard(segment: seg)),
                ],

                // Game date if available
                if (t.gameDateStart != null) ...[
                  const SizedBox(height: 16),
                  Text(
                    'Période : ${t.gameDateStart}'
                    '${t.gameDateEnd != null ? ' → ${t.gameDateEnd}' : ''}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context)
                              .colorScheme
                              .onSurfaceVariant,
                          fontStyle: FontStyle.italic,
                        ),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}

/// One segment card — uses color-coded left border per segment type.
/// [isPj] tints the background slightly purple to distinguish player content.
class _SegmentCard extends StatelessWidget {
  final SegmentRow segment;
  final bool isPj;

  const _SegmentCard({super.key, required this.segment, this.isPj = false});

  @override
  Widget build(BuildContext context) {
    final color = isPj
        ? Colors.purple
        : AppColors.segmentTypeColors[segment.segmentType] ?? Colors.grey;
    final typeLabel = switch (segment.segmentType) {
      'narrative' => 'Narration',
      'choice' => 'Choix',
      'consequence' => 'Conséquence',
      'ooc' => 'Hors-Jeu',
      'description' => 'Description',
      _ => segment.segmentType,
    };

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        border: Border(
          left: BorderSide(color: color, width: 3),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 8, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Segment type label
            Text(
              typeLabel,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: color,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.5,
                  ),
            ),
            const SizedBox(height: 6),
            // Full content
            SelectableText(
              segment.content,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    height: 1.5,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
