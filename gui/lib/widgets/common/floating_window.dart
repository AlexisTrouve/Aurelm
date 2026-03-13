import 'package:flutter/material.dart';

/// Callback that receives a close function — the body can call it to close itself.
typedef FloatingWindowBody = Widget Function(VoidCallback close);

/// Insert a draggable floating window into the Overlay.
/// Returns the [OverlayEntry] so the caller can remove it programmatically.
OverlayEntry insertFloatingWindow(
  BuildContext context,
  String title,
  IconData icon,
  FloatingWindowBody body, {
  Offset initialOffset = const Offset(200, 140),
}) {
  late OverlayEntry entry;
  entry = OverlayEntry(
    builder: (ctx) => FloatingWindowFrame(
      title: title,
      icon: icon,
      initialOffset: initialOffset,
      onClose: () => entry.remove(),
      body: body(() => entry.remove()),
    ),
  );
  Overlay.of(context).insert(entry);
  return entry;
}

/// Draggable floating window frame with title bar and close button.
/// Used by notes, entity previews, and other floating panels.
class FloatingWindowFrame extends StatefulWidget {
  final String title;
  final IconData icon;
  final Offset initialOffset;
  final VoidCallback onClose;
  final Widget body;

  const FloatingWindowFrame({
    super.key,
    required this.title,
    required this.icon,
    required this.initialOffset,
    required this.onClose,
    required this.body,
  });

  @override
  State<FloatingWindowFrame> createState() => _FloatingWindowFrameState();
}

class _FloatingWindowFrameState extends State<FloatingWindowFrame> {
  late Offset _pos;

  @override
  void initState() {
    super.initState();
    _pos = widget.initialOffset;
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Stack(
      children: [
        Positioned(
          left: _pos.dx,
          top: _pos.dy,
          child: Material(
            elevation: 16,
            borderRadius: BorderRadius.circular(10),
            color: cs.surface,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minWidth: 380, maxWidth: 520),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Draggable title bar
                  GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onPanUpdate: (d) =>
                        setState(() => _pos = _pos + d.delta),
                    child: Container(
                      height: 36,
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      decoration: BoxDecoration(
                        color: cs.surfaceContainerHighest,
                        borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(10)),
                      ),
                      child: Row(
                        children: [
                          Icon(widget.icon, size: 14,
                              color: cs.onSurfaceVariant),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(widget.title,
                                style: Theme.of(context)
                                    .textTheme
                                    .titleSmall
                                    ?.copyWith(fontSize: 12)),
                          ),
                          // Red X — always closes
                          SizedBox(
                            width: 24,
                            height: 24,
                            child: IconButton(
                              padding: EdgeInsets.zero,
                              iconSize: 15,
                              icon: const Icon(Icons.close,
                                  color: Colors.red),
                              tooltip: 'Fermer',
                              onPressed: widget.onClose,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  // Window body
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: widget.body,
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
