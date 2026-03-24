/// Generic blocking modal dialog for pipeline sync with progress bars.
/// Reusable from civ detail (per-channel sync) and dashboard (global sync).

import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

/// Show a blocking sync progress dialog.
///
/// [syncAction] is the async function that triggers the sync (e.g. call bot API).
/// [title] is the dialog title (e.g. "Import de 3 tours").
/// [botPort] is the bot HTTP port for polling /progress.
///
/// Returns `true` on success, error string on failure.
Future<dynamic> showSyncProgressDialog(
  BuildContext context, {
  required Future<void> Function() syncAction,
  required String title,
  int botPort = 8473,
}) {
  return showDialog(
    context: context,
    barrierDismissible: false,
    builder: (_) => SyncProgressDialog(
      syncAction: syncAction,
      title: title,
      botPort: botPort,
    ),
  );
}

class SyncProgressDialog extends StatefulWidget {
  final Future<void> Function() syncAction;
  final String title;
  final int botPort;

  const SyncProgressDialog({
    super.key,
    required this.syncAction,
    required this.title,
    this.botPort = 8473,
  });

  @override
  State<SyncProgressDialog> createState() => _SyncProgressDialogState();
}

class _SyncProgressDialogState extends State<SyncProgressDialog> {
  Timer? _timer;
  Map<String, dynamic>? _progress;
  bool _done = false;
  String? _error;
  DateTime? _startTime;

  @override
  void initState() {
    super.initState();
    _startTime = DateTime.now();
    _startSync();
    _timer = Timer.periodic(
        const Duration(seconds: 2), (_) => _pollProgress());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _startSync() async {
    try {
      await widget.syncAction();
      if (mounted) {
        setState(() => _done = true);
        // Auto-close after brief delay so user sees "done"
        Future.delayed(const Duration(milliseconds: 800), () {
          if (mounted) Navigator.of(context).pop(true);
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() { _done = true; _error = e.toString(); });
      }
    }
  }

  Future<void> _pollProgress() async {
    if (_done) return;
    try {
      final resp = await http
          .get(Uri.parse('http://127.0.0.1:${widget.botPort}/progress'))
          .timeout(const Duration(seconds: 3));
      if (!mounted) return;
      if (resp.statusCode == 200) {
        setState(() =>
            _progress = jsonDecode(resp.body) as Map<String, dynamic>);
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AlertDialog(
      title: Row(
        children: [
          if (!_done)
            const SizedBox(
                width: 20, height: 20,
                child: CircularProgressIndicator(strokeWidth: 2.5))
          else if (_error != null)
            const Icon(Icons.error, color: Colors.red, size: 20)
          else
            const Icon(Icons.check_circle, color: Colors.green, size: 20),
          const SizedBox(width: 12),
          Expanded(child: Text(widget.title,
              style: theme.textTheme.titleSmall)),
        ],
      ),
      content: SizedBox(
        width: 400,
        child: _done
            ? _buildDoneContent(theme)
            : _buildProgressContent(theme),
      ),
      actions: _done && _error != null
          ? [
              FilledButton(
                onPressed: () => Navigator.of(context).pop(_error),
                child: const Text('Fermer'),
              ),
            ]
          : null,
    );
  }

  Widget _buildDoneContent(ThemeData theme) {
    if (_error != null) {
      return Text('Erreur: $_error',
          style: TextStyle(color: theme.colorScheme.error));
    }
    return const Text('Import termine !');
  }

  Widget _buildProgressContent(ThemeData theme) {
    final phases = (_progress?['phases'] as List?) ?? [];
    if (phases.isEmpty) {
      return const Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('Demarrage du pipeline...'),
          SizedBox(height: 16),
          LinearProgressIndicator(),
        ],
      );
    }

    if (phases[0] is! Map<String, dynamic>) {
      return const LinearProgressIndicator();
    }

    final p = phases[0] as Map<String, dynamic>;
    final currentTurn = p['current_unit'] as int? ?? 0;
    final totalTurns = p['total_units'] as int? ?? 1;
    final stageName = p['stage_name'] as String? ?? '';
    final callsDone = p['llm_calls_done'] as int? ?? 0;
    final callsTotal = p['llm_calls_total'] as int? ?? 1;
    final turnNumber = p['turn_number'] as int?;
    final civName = p['civ_name'] as String?;

    // Human-readable stage label
    final stageLabel = switch (stageName) {
      'extraction' => 'Extraction entites',
      'validation' => 'Validation entites',
      'summarization' => 'Resume',
      'subjects' => 'Sujets MJ/PJ',
      'profiling' => 'Profiling entites',
      'pj_extraction' => 'Extraction PJ',
      'preanalysis' => 'Pre-analyse',
      'civ_relations' => 'Relations inter-civs',
      'aliases' => 'Resolution aliases',
      _ => stageName.isNotEmpty ? stageName : 'En cours...',
    };

    // Pipeline steps for the top-level progress bar
    const pipelineSteps = [
      'extraction', 'validation', 'summarization', 'pj_extraction',
      'preanalysis', 'subjects', 'profiling', 'civ_relations', 'aliases',
    ];
    const pipelineStepLabels = [
      '6. Extraction', '6. Validation', '6. Resume', '6. PJ',
      '6.5 Pre-analyse', '7. Sujets', '8. Profiling', '8.5 Relations', '9. Aliases',
    ];
    int stepIdx = pipelineSteps.indexOf(stageName);
    if (stepIdx < 0) stepIdx = 0;
    final stepLabel = pipelineStepLabels[stepIdx];
    final stepProgress = (stepIdx + 1) / pipelineSteps.length;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Civ name (useful for global sync with multiple civs)
        if (civName != null && civName.isNotEmpty) ...[
          Text(civName,
              style: theme.textTheme.titleSmall?.copyWith(
                  color: theme.colorScheme.primary)),
          const SizedBox(height: 8),
        ],

        // Pipeline stage (top-level)
        Row(
          children: [
            const Icon(Icons.list_alt, size: 16),
            const SizedBox(width: 6),
            Text('Etape: $stepLabel',
                style: theme.textTheme.labelMedium
                    ?.copyWith(fontWeight: FontWeight.w600)),
            const Spacer(),
            Text('${stepIdx + 1}/${pipelineSteps.length}',
                style: theme.textTheme.bodySmall),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: stepProgress,
            minHeight: 6,
            color: Colors.deepPurple,
          ),
        ),
        const SizedBox(height: 12),

        // Turn progress
        Row(
          children: [
            const Icon(Icons.autorenew, size: 16),
            const SizedBox(width: 6),
            Text(
              turnNumber != null
                  ? 'Tour $turnNumber ($currentTurn/$totalTurns)'
                  : 'Tour $currentTurn/$totalTurns',
              style: theme.textTheme.labelMedium
                  ?.copyWith(fontWeight: FontWeight.w600),
            ),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: theme.colorScheme.primary.withAlpha(30),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(stageLabel,
                  style: theme.textTheme.labelSmall
                      ?.copyWith(color: theme.colorScheme.primary)),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: totalTurns > 0 ? currentTurn / totalTurns : null,
            minHeight: 8,
          ),
        ),
        const SizedBox(height: 12),

        // LLM calls
        Row(
          children: [
            Text('Calls LLM: $callsDone / $callsTotal',
                style: theme.textTheme.bodySmall),
            const Spacer(),
            if (callsTotal > 0)
              Text('${(callsDone / callsTotal * 100).toStringAsFixed(0)}%',
                  style: theme.textTheme.bodySmall
                      ?.copyWith(fontWeight: FontWeight.w600)),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(3),
          child: LinearProgressIndicator(
            value: callsTotal > 0 ? callsDone / callsTotal : null,
            minHeight: 6,
            color: Colors.amber,
          ),
        ),

        // ETA
        if (callsDone > 2 && _startTime != null) ...[
          const SizedBox(height: 8),
          _buildEta(callsDone, callsTotal, stepIdx, pipelineSteps.length, theme),
        ],
      ],
    );
  }

  Widget _buildEta(int callsDone, int callsTotal,
      int stepIdx, int totalSteps, ThemeData theme) {
    final elapsed = DateTime.now().difference(_startTime!);
    if (elapsed.inSeconds < 5) return const SizedBox.shrink();

    final callRatio = callsTotal > 0 ? callsDone / callsTotal : 0.0;
    final stageRatio = totalSteps > 0 ? (stepIdx + callRatio) / totalSteps : 0.0;
    final progress = stageRatio.clamp(0.01, 0.99);

    final estimatedTotal = elapsed.inSeconds / progress;
    final remaining = (estimatedTotal - elapsed.inSeconds).round();

    if (remaining <= 0) return const SizedBox.shrink();

    final etaStr = remaining >= 60
        ? '~${remaining ~/ 60}m ${remaining % 60}s restant'
        : '~${remaining}s restant';

    return Row(
      children: [
        Icon(Icons.timer_outlined, size: 14,
            color: theme.colorScheme.onSurface.withAlpha(120)),
        const SizedBox(width: 4),
        Text(etaStr,
            style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withAlpha(120),
                fontStyle: FontStyle.italic)),
        const Spacer(),
        Text('${elapsed.inSeconds}s ecoules',
            style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withAlpha(80))),
      ],
    );
  }
}
