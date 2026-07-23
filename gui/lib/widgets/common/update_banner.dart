import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/update_provider.dart';

/// Slim bar shown above every screen once the startup check finds a newer build.
///
/// Renders nothing at all when there is no update — mounting it in the shell is
/// also what kicks off the automatic check (the provider is lazy, the shell is
/// built once at launch). Dismissible for the session so it never nags.
class UpdateBanner extends ConsumerWidget {
  const UpdateBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(updateControllerProvider);
    if (!state.showBanner) return const SizedBox.shrink();

    final scheme = Theme.of(context).colorScheme;
    final ctrl = ref.read(updateControllerProvider.notifier);
    final info = state.available!;

    return Material(
      color: scheme.primaryContainer,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                Icon(Icons.system_update_alt, size: 18, color: scheme.onPrimaryContainer),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    state.error ??
                        state.status ??
                        'Aurelm ${info.version} est disponible'
                            '${info.notes.isNotEmpty ? ' — ${info.notes}' : ''}',
                    style: TextStyle(
                      fontSize: 13,
                      color: state.error != null ? Colors.red : scheme.onPrimaryContainer,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (!state.busy) ...[
                  TextButton(
                    onPressed: ctrl.dismiss,
                    child: const Text('Plus tard'),
                  ),
                  const SizedBox(width: 4),
                  FilledButton(
                    onPressed: ctrl.install,
                    child: const Text('Installer'),
                  ),
                ],
              ],
            ),
          ),
          if (state.progress != null)
            LinearProgressIndicator(value: state.progress, minHeight: 2),
        ],
      ),
    );
  }
}
