import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_constants.dart';
import '../../providers/bot_provider.dart';
import '../../services/update_service.dart';

/// "Mises à jour" panel: shows the installed version, checks the distribution
/// server, and installs a newer build.
///
/// Deliberate choices:
///  - the check is manual + best-effort; an unreachable server reports "à jour ou
///    injoignable" rather than an error, because the update host is allowed to be down;
///  - a sha256 mismatch is shown LOUDLY. It is the one failure the user must see:
///    it means the binary we downloaded is not the one that was published.
class UpdateSection extends ConsumerStatefulWidget {
  const UpdateSection({super.key});

  @override
  ConsumerState<UpdateSection> createState() => _UpdateSectionState();
}

class _UpdateSectionState extends ConsumerState<UpdateSection> {
  final _service = UpdateService();
  UpdateInfo? _available;
  bool _busy = false;
  String? _status;
  String? _error;
  double? _progress;

  Future<void> _check() async {
    setState(() {
      _busy = true;
      _error = null;
      _status = 'Vérification…';
    });
    final info = await _service.check(currentVersion: AppConstants.appVersion);
    if (!mounted) return;
    setState(() {
      _busy = false;
      _available = info;
      _status = info == null
          ? 'Aucune mise à jour (ou serveur injoignable).'
          : 'Version ${info.version} disponible.';
    });
  }

  Future<void> _install() async {
    final info = _available;
    if (info == null) return;
    setState(() {
      _busy = true;
      _error = null;
      _progress = 0;
      _status = 'Téléchargement…';
    });
    try {
      final file = await _service.download(info, onProgress: (received, total) {
        if (!mounted || total == null || total <= 0) return;
        setState(() => _progress = received / total);
      });
      if (!mounted) return;
      setState(() => _status = 'Installation — l\'application va se fermer…');
      // Stopping the bot releases the embedded python's handles inside the install
      // directory; without it the installer cannot replace those files.
      await _service.installAndExit(
        file,
        onBeforeExit: () async => ref.read(botServiceProvider).stop(),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _progress = null;
        _status = null;
        _error = e is UpdateIntegrityError ? e.message : 'Échec : $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
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
                    onPressed: _busy ? null : _check,
                    child: const Text('Vérifier'),
                  ),
              ],
            ),
            if (_status != null) ...[
              const SizedBox(height: 8),
              Text(_status!, style: TextStyle(color: scheme.onSurfaceVariant)),
            ],
            if (_progress != null) ...[
              const SizedBox(height: 8),
              LinearProgressIndicator(value: _progress),
            ],
            if (_available != null && !_busy) ...[
              if (_available!.notes.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(_available!.notes, style: const TextStyle(fontSize: 12)),
              ],
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: _install,
                icon: const Icon(Icons.download, size: 18),
                label: Text('Installer ${_available!.version}'),
              ),
            ],
            if (_error != null) ...[
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
                      child: Text(_error!,
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
