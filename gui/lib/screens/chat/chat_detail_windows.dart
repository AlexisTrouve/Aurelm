import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/entity_provider.dart';
import '../../providers/civilization_provider.dart';
import '../../providers/subject_provider.dart';
import '../../providers/turn_provider.dart';
import '../../widgets/common/floating_window.dart';
import '../../widgets/common/entity_type_badge.dart';

// ---------------------------------------------------------------------------
// Entity preview window
// ---------------------------------------------------------------------------

/// Open a floating preview for an entity. Shows name, type, description,
/// and a button to navigate to the full detail page.
void showEntityDetailWindow(BuildContext context, WidgetRef ref, int entityId) {
  insertFloatingWindow(
    context,
    'Entite...',
    Icons.category_outlined,
    (close) => _EntityPreview(entityId: entityId, onClose: close),
    initialOffset: const Offset(260, 120),
  );
}

class _EntityPreview extends ConsumerWidget {
  final int entityId;
  final VoidCallback onClose;

  const _EntityPreview({required this.entityId, required this.onClose});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(entityDetailProvider(entityId));
    return detail.when(
      loading: () => const SizedBox(
        height: 60,
        child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
      ),
      error: (e, _) => Text('Erreur: $e'),
      data: (data) {
        if (data == null) return const Text('Entite introuvable');
        final e = data.entity;
        return Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Name + type badge
            Row(
              children: [
                Expanded(
                  child: Text(
                    e.canonicalName,
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                ),
                EntityTypeBadge(entityType: e.entityType),
              ],
            ),
            const SizedBox(height: 8),
            // Description (truncated)
            if (e.description != null && e.description!.isNotEmpty)
              ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 120),
                child: SingleChildScrollView(
                  child: SelectionArea(
                    child: Text(
                      e.description!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            height: 1.5,
                          ),
                    ),
                  ),
                ),
              ),
            if (e.description == null || e.description!.isEmpty)
              Text(
                'Pas de description',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      fontStyle: FontStyle.italic,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
            const SizedBox(height: 8),
            // Mention count
            Text(
              '${data.mentionCount} mention${data.mentionCount != 1 ? 's' : ''}',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            const SizedBox(height: 12),
            // Open full page button
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.icon(
                icon: const Icon(Icons.open_in_new, size: 14),
                label: const Text('Ouvrir'),
                onPressed: () {
                  onClose();
                  context.push('/entities/$entityId');
                },
              ),
            ),
          ],
        );
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Civilization preview window
// ---------------------------------------------------------------------------

void showCivDetailWindow(BuildContext context, WidgetRef ref, int civId) {
  insertFloatingWindow(
    context,
    'Civilisation...',
    Icons.flag_outlined,
    (close) => _CivPreview(civId: civId, onClose: close),
    initialOffset: const Offset(280, 130),
  );
}

class _CivPreview extends ConsumerWidget {
  final int civId;
  final VoidCallback onClose;

  const _CivPreview({required this.civId, required this.onClose});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(civDetailProvider(civId));
    return detail.when(
      loading: () => const SizedBox(
        height: 60,
        child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
      ),
      error: (e, _) => Text('Erreur: $e'),
      data: (data) {
        if (data == null) return const Text('Civilisation introuvable');
        return Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              data.civ.name,
              style: Theme.of(context)
                  .textTheme
                  .titleMedium
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            if (data.civ.playerName != null) ...[
              const SizedBox(height: 4),
              Text(
                'Joueur : ${data.civ.playerName}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            const SizedBox(height: 8),
            Text(
              '${data.turnCount} tours  -  ${data.entityCount} entites',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.icon(
                icon: const Icon(Icons.open_in_new, size: 14),
                label: const Text('Ouvrir'),
                onPressed: () {
                  onClose();
                  context.push('/civs/$civId');
                },
              ),
            ),
          ],
        );
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Subject preview window
// ---------------------------------------------------------------------------

void showSubjectDetailWindow(BuildContext context, WidgetRef ref, int subjectId) {
  insertFloatingWindow(
    context,
    'Sujet...',
    Icons.question_answer_outlined,
    (close) => _SubjectPreview(subjectId: subjectId, onClose: close),
    initialOffset: const Offset(240, 140),
  );
}

class _SubjectPreview extends ConsumerWidget {
  final int subjectId;
  final VoidCallback onClose;

  const _SubjectPreview({required this.subjectId, required this.onClose});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(subjectDetailProvider(subjectId));
    return detail.when(
      loading: () => const SizedBox(
        height: 60,
        child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
      ),
      error: (e, _) => Text('Erreur: $e'),
      data: (data) {
        if (data == null) return const Text('Sujet introuvable');
        final s = data.subject;
        final statusColor = s.status == 'open'
            ? Colors.orange
            : s.status == 'resolved'
                ? Colors.green
                : Colors.grey;
        return Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              s.title,
              style: Theme.of(context)
                  .textTheme
                  .titleMedium
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            // Status + direction chips
            Wrap(
              spacing: 6,
              children: [
                Chip(
                  label: Text(s.status),
                  labelStyle: TextStyle(color: statusColor, fontSize: 11),
                  side: BorderSide(color: statusColor),
                  padding: EdgeInsets.zero,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  visualDensity: VisualDensity.compact,
                ),
                Chip(
                  label: Text(s.direction == 'mj_to_pj' ? 'MJ->PJ' : 'PJ->MJ'),
                  labelStyle: const TextStyle(fontSize: 11),
                  padding: EdgeInsets.zero,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  visualDensity: VisualDensity.compact,
                ),
              ],
            ),
            if (s.description != null && s.description!.isNotEmpty) ...[
              const SizedBox(height: 8),
              ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 100),
                child: SingleChildScrollView(
                  child: SelectionArea(
                    child: Text(
                      s.description!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            height: 1.5,
                          ),
                    ),
                  ),
                ),
              ),
            ],
            const SizedBox(height: 6),
            Text(
              'Tour ${data.sourceTurnNumber}  -  ${data.civName}',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.icon(
                icon: const Icon(Icons.open_in_new, size: 14),
                label: const Text('Ouvrir'),
                onPressed: () {
                  onClose();
                  context.push('/subjects/$subjectId');
                },
              ),
            ),
          ],
        );
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Turn preview window
// ---------------------------------------------------------------------------

void showTurnDetailWindow(BuildContext context, WidgetRef ref, int turnId) {
  insertFloatingWindow(
    context,
    'Tour...',
    Icons.history_edu_outlined,
    (close) => _TurnPreview(turnId: turnId, onClose: close),
    initialOffset: const Offset(250, 150),
  );
}

class _TurnPreview extends ConsumerWidget {
  final int turnId;
  final VoidCallback onClose;

  const _TurnPreview({required this.turnId, required this.onClose});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(turnDetailDataProvider(turnId));
    return detail.when(
      loading: () => const SizedBox(
        height: 60,
        child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
      ),
      error: (e, _) => Text('Erreur: $e'),
      data: (data) {
        if (data == null) return const Text('Tour introuvable');
        final t = data.turn;
        return Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              t.title ?? 'Tour ${t.turnNumber}',
              style: Theme.of(context)
                  .textTheme
                  .titleMedium
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            Text(
              '${data.civName}  -  ${data.entityCount} entites',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            // Summary preview
            if (t.summary != null && t.summary!.isNotEmpty) ...[
              const SizedBox(height: 8),
              ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 120),
                child: SingleChildScrollView(
                  child: SelectionArea(
                    child: Text(
                      t.summary!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            fontStyle: FontStyle.italic,
                            height: 1.5,
                          ),
                    ),
                  ),
                ),
              ),
            ],
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.icon(
                icon: const Icon(Icons.open_in_new, size: 14),
                label: const Text('Ouvrir'),
                onPressed: () {
                  onClose();
                  context.push('/turns/$turnId');
                },
              ),
            ),
          ],
        );
      },
    );
  }
}
