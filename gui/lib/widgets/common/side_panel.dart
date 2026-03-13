import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/side_panel_provider.dart';
import '../../screens/entities/entity_detail_screen.dart';
import '../../screens/civilization/civ_detail_screen.dart';
import '../../screens/subjects/subject_detail_screen.dart';
import '../../screens/timeline/turn_detail_screen.dart';
import '../../utils/lore_linker.dart';

// ---------------------------------------------------------------------------
// Side panel — 3 vertical slots (top / center / bottom), max 40% width
// ---------------------------------------------------------------------------

/// A side panel showing up to 3 detail views stacked vertically.
/// Each slot renders the full body of the corresponding detail screen
/// (entity, civ, subject, or turn) with a title bar and close button.
class SidePanel extends ConsumerWidget {
  const SidePanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(sidePanelProvider);
    if (!state.isOpen) return const SizedBox.shrink();

    final slots = <(PanelSlot, SidePanelItem)>[
      if (state.top != null) (PanelSlot.top, state.top!),
      if (state.center != null) (PanelSlot.center, state.center!),
      if (state.bottom != null) (PanelSlot.bottom, state.bottom!),
    ];

    return Container(
      constraints: BoxConstraints(
        maxWidth: MediaQuery.of(context).size.width * 0.4,
        minWidth: 320,
      ),
      decoration: BoxDecoration(
        border: Border(
          left: BorderSide(
            color: Theme.of(context).colorScheme.outlineVariant,
            width: 0.5,
          ),
        ),
      ),
      child: Column(
        children: [
          // Close all button
          _PanelToolbar(slotCount: slots.length),
          // Slots — each takes equal vertical space
          ...slots.map((entry) {
            final (slot, item) = entry;
            return Expanded(
              child: _PanelSlotView(slot: slot, item: item),
            );
          }),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Panel toolbar — close all button
// ---------------------------------------------------------------------------

class _PanelToolbar extends StatelessWidget {
  final int slotCount;
  const _PanelToolbar({required this.slotCount});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 32,
      padding: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLow,
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).colorScheme.outlineVariant,
            width: 0.5,
          ),
        ),
      ),
      child: Row(
        children: [
          Icon(Icons.view_sidebar,
              size: 14, color: Theme.of(context).colorScheme.onSurfaceVariant),
          const SizedBox(width: 6),
          Text(
            '$slotCount panneau${slotCount > 1 ? 'x' : ''}',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          ),
          const Spacer(),
          Consumer(builder: (context, ref, _) {
            return SizedBox(
              width: 24,
              height: 24,
              child: IconButton(
                padding: EdgeInsets.zero,
                iconSize: 14,
                icon: const Icon(Icons.close),
                tooltip: 'Tout fermer',
                onPressed: () =>
                    ref.read(sidePanelProvider.notifier).closeAll(),
              ),
            );
          }),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Single panel slot — title bar + scrollable body for the detail content
// ---------------------------------------------------------------------------

class _PanelSlotView extends ConsumerWidget {
  final PanelSlot slot;
  final SidePanelItem item;

  const _PanelSlotView({required this.slot, required this.item});

  /// Title and icon for each lore type
  (String, IconData) _titleInfo(SidePanelItem item) {
    return switch (item.type) {
      LoreLinkType.entity => ('Entite', Icons.category_outlined),
      LoreLinkType.civ => ('Civilisation', Icons.flag_outlined),
      LoreLinkType.subject => ('Sujet', Icons.question_answer_outlined),
      LoreLinkType.turn => ('Tour', Icons.history_edu_outlined),
    };
  }

  /// Route for full-page navigation
  String _route(SidePanelItem item) {
    return switch (item.type) {
      LoreLinkType.entity => '/entities/${item.id}',
      LoreLinkType.civ => '/civs/${item.id}',
      LoreLinkType.subject => '/subjects/${item.id}',
      LoreLinkType.turn => '/turns/${item.id}',
    };
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final (title, icon) = _titleInfo(item);
    final cs = Theme.of(context).colorScheme;

    return Container(
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: cs.outlineVariant, width: 0.5),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Title bar with close + open-in-page buttons
          Container(
            height: 30,
            padding: const EdgeInsets.symmetric(horizontal: 8),
            color: cs.surfaceContainerHighest,
            child: Row(
              children: [
                Icon(icon, size: 13, color: cs.onSurfaceVariant),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context)
                        .textTheme
                        .labelSmall
                        ?.copyWith(fontWeight: FontWeight.w600),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                // Open in full page (keeps the panel slot open)
                SizedBox(
                  width: 22,
                  height: 22,
                  child: IconButton(
                    padding: EdgeInsets.zero,
                    iconSize: 13,
                    icon: const Icon(Icons.open_in_new),
                    tooltip: 'Ouvrir en pleine page',
                    onPressed: () => context.push(_route(item)),
                  ),
                ),
                const SizedBox(width: 2),
                // Close this slot
                SizedBox(
                  width: 22,
                  height: 22,
                  child: IconButton(
                    padding: EdgeInsets.zero,
                    iconSize: 13,
                    icon: const Icon(Icons.close, color: Colors.red),
                    tooltip: 'Fermer',
                    onPressed: () =>
                        ref.read(sidePanelProvider.notifier).close(slot),
                  ),
                ),
              ],
            ),
          ),
          // Body — the actual detail content
          Expanded(
            child: SelectionArea(
              child: _buildBody(context, ref),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(BuildContext context, WidgetRef ref) {
    // Embed the actual full detail screens — they contain their own Scaffold
    // which works fine in a constrained area (nested Scaffold is supported).
    return switch (item.type) {
      LoreLinkType.entity => EntityDetailScreen(entityId: item.id),
      LoreLinkType.civ => CivDetailScreen(civId: item.id),
      LoreLinkType.subject => SubjectDetailScreen(subjectId: item.id),
      LoreLinkType.turn => TurnDetailScreen(turnId: item.id),
    };
  }
}

