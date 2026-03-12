import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../data/database.dart';
import '../../../models/subject_with_details.dart';

/// A single subject tile in the subjects list.
class SubjectListTile extends StatelessWidget {
  final SubjectWithDetails subject;

  const SubjectListTile({super.key, required this.subject});

  @override
  Widget build(BuildContext context) {
    final s = subject.subject;
    final isResolved = s.status == 'resolved';
    final isMjToPj = s.direction == 'mj_to_pj';

    // Confidence of best resolution (0–100%)
    final confidence = subject.bestResolution?.confidence;

    return Card(
      margin: const EdgeInsets.only(bottom: 6),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => context.push('/subjects/${s.id}'),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Direction indicator
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: isMjToPj
                      ? Colors.blue.withValues(alpha: 0.15)
                      : Colors.purple.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                alignment: Alignment.center,
                child: Text(
                  isMjToPj ? '→' : '←',
                  style: TextStyle(
                    fontSize: 18,
                    color: isMjToPj ? Colors.blue : Colors.purple,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),

              const SizedBox(width: 12),

              // Content
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Title
                    Text(
                      s.title,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                    ),

                    const SizedBox(height: 4),

                    // Meta row: turn + civ + category
                    Row(
                      children: [
                        _MetaChip(
                          label: 'T${subject.sourceTurnNumber}',
                          color: Colors.grey,
                        ),
                        const SizedBox(width: 4),
                        _MetaChip(
                          label: _categoryLabel(s.category),
                          color: _categoryColor(s.category),
                        ),
                        const Spacer(),
                        // Status badge
                        _StatusBadge(
                          status: s.status,
                          confidence: confidence,
                        ),
                      ],
                    ),

                    // Domain tag chips
                    Builder(builder: (context) {
                      final tags = s.tags.isNotEmpty
                          ? (jsonDecode(s.tags) as List).cast<String>()
                          : <String>[];
                      if (tags.isEmpty) return const SizedBox.shrink();
                      return Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Wrap(
                          spacing: 4,
                          children: tags.map((tag) => Container(
                            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                            decoration: BoxDecoration(
                              color: Colors.blueGrey.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              tag,
                              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                color: Colors.blueGrey.shade300,
                              ),
                            ),
                          )).toList(),
                        ),
                      );
                    }),

                    // Options preview (for mj_to_pj choices)
                    if (subject.options.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        subject.options
                            .map((o) => '${o.optionNumber}. ${o.label}')
                            .join(' · '),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Theme.of(context)
                                  .colorScheme
                                  .onSurfaceVariant,
                              fontStyle: FontStyle.italic,
                            ),
                      ),
                    ],

                    // Resolution preview
                    if (isResolved && subject.bestResolution != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        subject.bestResolution!.resolutionText,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Colors.green.shade300,
                            ),
                      ),
                    ],
                  ],
                ),
              ),

              const SizedBox(width: 8),
              const Icon(Icons.chevron_right, size: 18),
            ],
          ),
        ),
      ),
    );
  }

  String _categoryLabel(String category) {
    return switch (category) {
      'choice' => 'Choix',
      'question' => 'Question',
      'initiative' => 'Initiative',
      'request' => 'Demande',
      _ => category,
    };
  }

  Color _categoryColor(String category) {
    return switch (category) {
      'choice' => Colors.orange,
      'question' => Colors.cyan,
      'initiative' => Colors.purple,
      'request' => Colors.teal,
      _ => Colors.grey,
    };
  }
}

class _MetaChip extends StatelessWidget {
  final String label;
  final Color color;

  const _MetaChip({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(color: color),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final String status;
  final double? confidence;

  const _StatusBadge({required this.status, this.confidence});

  @override
  Widget build(BuildContext context) {
    if (status == 'open') {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: Colors.orange.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: Colors.orange.withValues(alpha: 0.5)),
        ),
        child: Text(
          'Ouvert',
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: Colors.orange,
                fontWeight: FontWeight.w600,
              ),
        ),
      );
    }
    if (status == 'resolved') {
      final pct = confidence != null
          ? '${(confidence! * 100).round()}%'
          : '';
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: Colors.green.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: Colors.green.withValues(alpha: 0.5)),
        ),
        child: Text(
          pct.isEmpty ? 'Résolu' : 'Résolu $pct',
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: Colors.green,
                fontWeight: FontWeight.w600,
              ),
        ),
      );
    }
    return Text(
      status,
      style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
    );
  }
}
