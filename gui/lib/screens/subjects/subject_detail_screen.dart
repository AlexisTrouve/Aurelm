import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../data/database.dart';
import '../../providers/subject_provider.dart';
import '../../models/subject_with_details.dart';
import '../../widgets/common/loading_indicator.dart';
import '../../widgets/common/error_view.dart';
import '../../widgets/common/section_header.dart';

/// Detail page for a single subject — shows description, options, and all
/// resolution attempts with confidence percentages.
class SubjectDetailScreen extends ConsumerWidget {
  final int subjectId;

  const SubjectDetailScreen({super.key, required this.subjectId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(subjectDetailProvider(subjectId));

    return detailAsync.when(
      loading: () => const Scaffold(body: LoadingIndicator()),
      error: (e, _) => Scaffold(body: ErrorView(message: e.toString())),
      data: (detail) {
        if (detail == null) {
          return Scaffold(
            appBar: AppBar(),
            body: const Center(child: Text('Sujet introuvable')),
          );
        }
        return _SubjectDetailView(detail: detail);
      },
    );
  }
}

class _SubjectDetailView extends StatelessWidget {
  final SubjectDetail detail;

  const _SubjectDetailView({required this.detail});

  @override
  Widget build(BuildContext context) {
    final s = detail.subject;
    final isMjToPj = s.direction == 'mj_to_pj';
    final isResolved = s.status == 'resolved';

    return Scaffold(
      appBar: AppBar(
        title: Text(s.title, overflow: TextOverflow.ellipsis),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.canPop() ? context.pop() : context.go('/subjects'),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: direction, category, status
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                _DirectionBadge(isMjToPj: isMjToPj),
                _CategoryBadge(category: s.category),
                _StatusBadge(status: s.status),
                _TurnChip(
                    turnId: detail.sourceTurnId,
                    label: 'T${detail.sourceTurnNumber} · ${detail.civName}',
                    // Prefer verbatim source_quote for highlight; fall back to title
                    highlight: (s.sourceQuote?.isNotEmpty == true) ? s.sourceQuote : s.title),
              ],
            ),

            // Description
            if (s.description != null && s.description!.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text(s.description!,
                  style: Theme.of(context).textTheme.bodyMedium),
            ],

            // Options (for mj_to_pj choices)
            if (detail.options.isNotEmpty) ...[
              const SizedBox(height: 24),
              const SectionHeader(title: 'Options proposées'),
              const SizedBox(height: 8),
              ...detail.options.map((opt) => _OptionTile(
                    option: opt,
                    isChosen: detail.bestResolution?.chosenOptionId == opt.id,
                  )),
            ],

            // Resolutions
            const SizedBox(height: 24),
            SectionHeader(
              title: isResolved
                  ? 'Résolutions (${detail.resolutionCount})'
                  : 'Tentatives de résolution (${detail.resolutionCount})',
            ),
            const SizedBox(height: 8),

            if (detail.allResolutions.isEmpty)
              Text(
                'Aucune résolution détectée',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                      fontStyle: FontStyle.italic,
                    ),
              )
            else
              ...detail.allResolutions.map((r) => _ResolutionCard(
                    resolution: r,
                    isAccepted: detail.bestResolution?.id == r.resolution.id &&
                        isResolved,
                  )),
          ],
        ),
      ),
    );
  }
}

/// Option tile — shows option number, label, description, and "chosen" indicator.
class _OptionTile extends StatelessWidget {
  final SubjectOptionRow option;
  final bool isChosen;

  const _OptionTile({required this.option, required this.isChosen});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isChosen
            ? Colors.green.withValues(alpha: 0.1)
            : Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isChosen
              ? Colors.green.withValues(alpha: 0.5)
              : Theme.of(context).colorScheme.outline.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: isChosen
                  ? Colors.green
                  : Theme.of(context).colorScheme.primaryContainer,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Text(
              option.isLibre ? 'L' : '${option.optionNumber}',
              style: TextStyle(
                color: isChosen
                    ? Colors.white
                    : Theme.of(context).colorScheme.onPrimaryContainer,
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(option.label,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          fontWeight:
                              isChosen ? FontWeight.bold : FontWeight.normal,
                        )),
                if (option.description != null && option.description!.isNotEmpty)
                  Text(option.description!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context)
                                .colorScheme
                                .onSurfaceVariant,
                          )),
              ],
            ),
          ),
          if (isChosen)
            const Icon(Icons.check_circle, color: Colors.green, size: 18),
        ],
      ),
    );
  }
}

/// Card showing one resolution attempt with confidence bar.
class _ResolutionCard extends StatelessWidget {
  final ResolutionWithTurn resolution;
  final bool isAccepted;

  const _ResolutionCard({required this.resolution, required this.isAccepted});

  @override
  Widget build(BuildContext context) {
    final r = resolution.resolution;
    final pct = (r.confidence * 100).round();
    final barColor = pct >= 70
        ? Colors.green
        : pct >= 40
            ? Colors.orange
            : Colors.red;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isAccepted
            ? Colors.green.withValues(alpha: 0.07)
            : Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isAccepted
              ? Colors.green.withValues(alpha: 0.4)
              : Colors.transparent,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Confidence bar + turn info
          Row(
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: r.confidence,
                    backgroundColor:
                        Theme.of(context).colorScheme.outline.withValues(alpha: 0.2),
                    valueColor: AlwaysStoppedAnimation<Color>(barColor),
                    minHeight: 6,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Text(
                '$pct%',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: barColor,
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(width: 10),
              InkWell(
                onTap: () => context.push(
                  '/turns/${resolution.turnId}',
                  // Prefer verbatim source_quote; fall back to resolution_text summary
                  extra: {
                    'highlight': (resolution.resolution.sourceQuote?.isNotEmpty == true)
                        ? resolution.resolution.sourceQuote
                        : resolution.resolution.resolutionText,
                  },
                ),
                borderRadius: BorderRadius.circular(4),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                  child: Text(
                    'T${resolution.turnNumber}',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: Theme.of(context).colorScheme.primary,
                          decoration: TextDecoration.underline,
                        ),
                  ),
                ),
              ),
              if (isAccepted) ...[
                const SizedBox(width: 6),
                const Icon(Icons.verified, color: Colors.green, size: 16),
              ],
            ],
          ),
          const SizedBox(height: 8),
          // Resolution text
          Text(
            r.resolutionText,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}

// Small reusable badges

class _DirectionBadge extends StatelessWidget {
  final bool isMjToPj;
  const _DirectionBadge({required this.isMjToPj});

  @override
  Widget build(BuildContext context) {
    final color = isMjToPj ? Colors.blue : Colors.purple;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        isMjToPj ? '→ MJ→PJ' : '← PJ→MJ',
        style: Theme.of(context)
            .textTheme
            .labelSmall
            ?.copyWith(color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}

class _CategoryBadge extends StatelessWidget {
  final String category;
  const _CategoryBadge({required this.category});

  @override
  Widget build(BuildContext context) {
    final color = switch (category) {
      'choice' => Colors.orange,
      'question' => Colors.cyan,
      'initiative' => Colors.purple,
      'request' => Colors.teal,
      _ => Colors.grey,
    };
    final label = switch (category) {
      'choice' => 'Choix',
      'question' => 'Question',
      'initiative' => 'Initiative',
      'request' => 'Demande',
      _ => category,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(label,
          style: Theme.of(context)
              .textTheme
              .labelSmall
              ?.copyWith(color: color, fontWeight: FontWeight.w600)),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final String status;
  const _StatusBadge({required this.status});

  @override
  Widget build(BuildContext context) {
    final (color, label) = switch (status) {
      'open' => (Colors.orange, 'Ouvert'),
      'resolved' => (Colors.green, 'Résolu'),
      'superseded' => (Colors.grey, 'Remplacé'),
      'abandoned' => (Colors.red, 'Abandonné'),
      _ => (Colors.grey, status),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(label,
          style: Theme.of(context)
              .textTheme
              .labelSmall
              ?.copyWith(color: color, fontWeight: FontWeight.w600)),
    );
  }
}

class _MetaChip extends StatelessWidget {
  final String label;
  const _MetaChip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              )),
    );
  }
}

/// Chip de tour cliquable — fast travel vers le turn detail avec highlight optionnel.
class _TurnChip extends StatelessWidget {
  final int turnId;
  final String label;
  /// Text to auto-highlight in the turn detail on arrival.
  final String? highlight;
  const _TurnChip({required this.turnId, required this.label, this.highlight});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => context.push(
        '/turns/$turnId',
        extra: highlight != null ? {'highlight': highlight} : null,
      ),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.primaryContainer.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
              color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.open_in_new,
                size: 10,
                color: Theme.of(context).colorScheme.primary),
            const SizedBox(width: 4),
            Text(label,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                      fontWeight: FontWeight.w600,
                    )),
          ],
        ),
      ),
    );
  }
}
