import 'package:flutter/material.dart';

class CivBadge extends StatelessWidget {
  final String civName;
  /// When true, uses larger padding and labelMedium for more visual weight.
  final bool prominent;

  const CivBadge({super.key, required this.civName, this.prominent = false});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      padding: prominent
          ? const EdgeInsets.symmetric(horizontal: 10, vertical: 4)
          : const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        civName,
        style: (prominent
                ? Theme.of(context).textTheme.labelMedium
                : Theme.of(context).textTheme.labelSmall)
            ?.copyWith(
              color: colorScheme.onSecondaryContainer,
              fontWeight: prominent ? FontWeight.w600 : FontWeight.normal,
            ),
      ),
    );
  }
}
