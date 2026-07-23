import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_constants.dart';
import '../../providers/update_provider.dart';

/// "Mises à jour" panel — a VIEW over [updateControllerProvider].
///
/// The app checks automatically at startup (see UpdateBanner); this card shows the
/// installed version, lets the user re-check on demand, and is where a failure is
/// reported in full. A sha256 mismatch is shown LOUDLY: it is the one failure the
/// user must see, because it means the binary we downloaded is not the one published.
class UpdateSection extends ConsumerWidget {
  const UpdateSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(updateControllerProvider);
    final ctrl = ref.read(updateControllerProvider.notifier);
    final scheme = Theme.of(context).colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.system_update_alt),
                const SizedBox(width: 12),
                const Expanded(
                  child: Text('Version installée : ${AppConstants.appVersion}',
                      style: TextStyle(fontWeight: FontWeight.w600)),
                ),
                if (Platform.isWindows)
                  FilledButton.tonal(
                    onPressed: state.busy ? null : ctrl.check,
                    child: const Text('Vérifier'),
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text('Vérification automatique au démarrage.',
                style: TextStyle(fontSize: 11, color: scheme.onSurfaceVariant)),
            if (state.status != null) ...[
              const SizedBox(height: 8),
              Text(state.status!, style: TextStyle(color: scheme.onSurfaceVariant)),
            ],
            if (state.progress != null) ...[
              const SizedBox(height: 8),
              LinearProgressIndicator(value: state.progress),
            ],
            if (state.available != null && !state.busy) ...[
              if (state.available!.notes.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(state.available!.notes, style: const TextStyle(fontSize: 12)),
              ],
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: ctrl.install,
                icon: const Icon(Icons.download, size: 18),
                label: Text('Installer ${state.available!.version}'),
              ),
            ],
            if (state.error != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.red.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.gpp_bad, color: Colors.red, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(state.error!,
                          style: const TextStyle(color: Colors.red, fontSize: 12)),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
