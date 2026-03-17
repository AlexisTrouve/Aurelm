import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../models/turn_with_entities.dart';
import '../../../providers/favorites_provider.dart';
import '../../../widgets/common/civ_badge.dart';

/// Affiche une ou deux cartes par tour selon si des segments PJ existent.
/// - Carte MJ (gold) : narrative GM, entités GM, tags + étoile favori
/// - Carte PJ (purple) : réponse joueur, entités PJ
class TimelineTurnCard extends ConsumerWidget {
  final TurnWithEntities turn;

  const TimelineTurnCard({super.key, required this.turn});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final showPjCard = turn.hasPjContent;
    final isFav = ref.watch(favoritesProvider).contains('turn_${turn.turn.id}');

    return Column(
      children: [
        _TurnCard(
          turn: turn,
          source: 'mj',
          entityCount: turn.gmEntityCount,
          isFav: isFav,
          onTap: () => context.push('/turns/${turn.turn.id}'),
          onFavTap: () => ref
              .read(favoritesProvider.notifier)
              .toggle('turn', turn.turn.id, turn.turn.civId),
        ),
        if (showPjCard) ...[
          const SizedBox(height: 4),
          _TurnCard(
            turn: turn,
            source: 'pj',
            entityCount: turn.pjEntityCount,
            onTap: () => context.push('/turns/${turn.turn.id}'),
          ),
        ],
      ],
    );
  }
}

class _TurnCard extends StatelessWidget {
  final TurnWithEntities turn;
  final String source; // 'mj' or 'pj'
  final int entityCount;
  final VoidCallback onTap;
  // Only provided for MJ card — null means no star shown (PJ card)
  final bool? isFav;
  final VoidCallback? onFavTap;

  const _TurnCard({
    required this.turn,
    required this.source,
    required this.entityCount,
    required this.onTap,
    this.isFav,
    this.onFavTap,
  });

  @override
  Widget build(BuildContext context) {
    final t = turn.turn;
    final isMj = source == 'mj';

    // MJ = gold/amber, PJ = purple
    final typeColor = isMj
        ? (AppColors.turnTypeColors[t.turnType] ?? Colors.amber)
        : Colors.deepPurple;

    final label = isMj ? 'MJ' : 'PJ';
    final labelColor = isMj ? Colors.amber.shade700 : Colors.deepPurple;

    // Parse thematic tags from JSON string (only shown on MJ card)
    final tags = isMj && t.thematicTags != null
        ? (jsonDecode(t.thematicTags!) as List).cast<String>()
        : <String>[];

    final showTags =
        isMj && (tags.isNotEmpty || t.techEra != null || t.fantasyLevel != null);

    return Card(
      margin: const EdgeInsets.only(bottom: 2),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: EdgeInsets.fromLTRB(isMj ? 16 : 32, 12, 16, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // --- Main info row ---
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  // Turn number badge (MJ) or source badge (PJ)
                  if (isMj)
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        color: typeColor.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        '${t.turnNumber}',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              color: typeColor,
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                    )
                  else
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color: labelColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        label,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              color: labelColor,
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                    ),

                  const SizedBox(width: 16),

                  Expanded(
                    child: Row(
                      children: [
                        // MJ/PJ badge
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: labelColor.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            label,
                            style: Theme.of(context)
                                .textTheme
                                .labelSmall
                                ?.copyWith(
                                  color: labelColor,
                                  fontWeight: FontWeight.w700,
                                ),
                          ),
                        ),


                        const Spacer(),

                        // Civ badge (MJ only) — larger for readability
                        if (isMj) ...[
                          CivBadge(civName: turn.civName, prominent: true),
                          const SizedBox(width: 8),
                        ],

                        // Favorite star (MJ card only)
                        if (isMj && isFav != null) ...[
                          GestureDetector(
                            onTap: onFavTap,
                            child: Icon(
                              isFav! ? Icons.star : Icons.star_border,
                              size: 16,
                              color: isFav! ? Colors.amber : Colors.grey,
                            ),
                          ),
                          const SizedBox(width: 8),
                        ],

                        // Entity count
                        Text(
                          '$entityCount entities',
                          style:
                              Theme.of(context).textTheme.labelSmall?.copyWith(
                                    color: Theme.of(context)
                                        .colorScheme
                                        .onSurfaceVariant,
                                  ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),

              // --- Tags row: tech_era + fantasy_level + thematic_tags (MJ only) ---
              if (showTags) ...[
                const SizedBox(height: 6),
                Wrap(
                  spacing: 4,
                  runSpacing: 2,
                  children: [
                    if (t.techEra != null)
                      _TagChip(label: t.techEra!, color: Colors.teal),
                    if (t.fantasyLevel != null)
                      _TagChip(label: t.fantasyLevel!, color: Colors.deepPurple),
                    ...tags.map((tag) => _TagChip(label: tag, color: _tagColor(tag))),
                  ],
                ),
              ],

              // --- LLM summary (MJ only, truncated to 2 lines) ---
              if (isMj && t.summary != null && t.summary!.isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(
                  t.summary!,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                        fontStyle: FontStyle.italic,
                      ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Couleur sémantique par tag thématique.
Color _tagColor(String tag) => switch (tag) {
      'religion' => Colors.indigo,
      'culture' => Colors.amber,
      'exploration' => Colors.cyan,
      'construction' => Colors.brown,
      'agriculture' => Colors.green,
      'crise' => Colors.red,
      'migration' => Colors.orange,
      'decouverte' => Colors.lightBlue,
      'politique' => Colors.purple,
      'commerce' => Colors.yellow,
      'technologie' => Colors.blueGrey,
      'diplomatie' => Colors.pink,
      'combat' => Colors.deepOrange,
      'mort' => Colors.grey,
      'ressource' => Colors.lime,
      _ => Colors.blueGrey,
    };

/// Mini chip pour les tags de tour (tech_era, fantasy_level, thematic_tags).
class _TagChip extends StatelessWidget {
  final String label;
  final Color color;

  const _TagChip({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(3),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: color.withValues(alpha: 0.85),
              fontSize: 9,
            ),
      ),
    );
  }
}
