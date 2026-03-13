import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../utils/lore_linker.dart';

// ---------------------------------------------------------------------------
// Side panel state — 3 vertical slots (top / center / bottom)
// ---------------------------------------------------------------------------

/// One item displayed in a side panel slot.
class SidePanelItem {
  final LoreLinkType type;
  final int id;
  /// Optional civ ID context — used for turn disambiguation.
  final int? civId;

  const SidePanelItem({required this.type, required this.id, this.civId});

  @override
  bool operator ==(Object other) =>
      other is SidePanelItem &&
      other.type == type &&
      other.id == id &&
      other.civId == civId;

  @override
  int get hashCode => Object.hash(type, id, civId);
}

enum PanelSlot { top, center, bottom }

/// Immutable state for 3 panel slots.
class SidePanelState {
  final SidePanelItem? top;
  final SidePanelItem? center;
  final SidePanelItem? bottom;

  const SidePanelState({this.top, this.center, this.bottom});

  /// True if at least one slot is occupied.
  bool get isOpen => top != null || center != null || bottom != null;

  /// Number of occupied slots.
  int get count => (top != null ? 1 : 0) + (center != null ? 1 : 0) + (bottom != null ? 1 : 0);

  SidePanelState copyWith({
    SidePanelItem? Function()? top,
    SidePanelItem? Function()? center,
    SidePanelItem? Function()? bottom,
  }) {
    return SidePanelState(
      top: top != null ? top() : this.top,
      center: center != null ? center() : this.center,
      bottom: bottom != null ? bottom() : this.bottom,
    );
  }
}

class SidePanelNotifier extends StateNotifier<SidePanelState> {
  SidePanelNotifier() : super(const SidePanelState());

  /// Open an item in the first available slot, or replace bottom if full.
  /// If the same item is already shown, does nothing.
  void open(SidePanelItem item) {
    // Already showing this exact item — skip
    if (state.top == item || state.center == item || state.bottom == item) {
      return;
    }

    // Fill first empty slot
    if (state.top == null) {
      state = state.copyWith(top: () => item);
    } else if (state.center == null) {
      state = state.copyWith(center: () => item);
    } else if (state.bottom == null) {
      state = state.copyWith(bottom: () => item);
    } else {
      // All full — replace bottom (most recent is least important)
      state = state.copyWith(bottom: () => item);
    }
  }

  /// Open in a specific slot, replacing whatever was there.
  void openInSlot(PanelSlot slot, SidePanelItem item) {
    switch (slot) {
      case PanelSlot.top:
        state = state.copyWith(top: () => item);
      case PanelSlot.center:
        state = state.copyWith(center: () => item);
      case PanelSlot.bottom:
        state = state.copyWith(bottom: () => item);
    }
  }

  /// Close a specific slot.
  void close(PanelSlot slot) {
    switch (slot) {
      case PanelSlot.top:
        state = state.copyWith(top: () => null);
      case PanelSlot.center:
        state = state.copyWith(center: () => null);
      case PanelSlot.bottom:
        state = state.copyWith(bottom: () => null);
    }
  }

  /// Close all slots.
  void closeAll() {
    state = const SidePanelState();
  }
}

final sidePanelProvider =
    StateNotifierProvider<SidePanelNotifier, SidePanelState>(
  (ref) => SidePanelNotifier(),
);
