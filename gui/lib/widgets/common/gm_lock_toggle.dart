import 'package:flutter/material.dart';

/// Lock toggle always visible next to a GM-editable field.
/// Grey open lock = unlocked (pipeline can overwrite).
/// Amber closed lock = locked (pipeline skips this field).
/// Locking is immediate (no confirmation). Unlocking is handled by the parent
/// (typically shows a confirmation dialog via [onUnlock]).
class GmLockToggle extends StatelessWidget {
  final bool locked;
  final String fieldLabel; // used in tooltip
  final VoidCallback onLock;
  final VoidCallback onUnlock;

  const GmLockToggle({
    super.key,
    required this.locked,
    required this.fieldLabel,
    required this.onLock,
    required this.onUnlock,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: locked
          ? '$fieldLabel verrouillé — cliquer pour déverrouiller'
          : 'Verrouiller $fieldLabel (empêche le pipeline de l\'écraser)',
      child: InkWell(
        onTap: locked ? onUnlock : onLock,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: Icon(
            locked ? Icons.lock : Icons.lock_open,
            size: 14,
            color: locked ? Colors.amber : Colors.grey.withValues(alpha: 0.45),
          ),
        ),
      ),
    );
  }
}
