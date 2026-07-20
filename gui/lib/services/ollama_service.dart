import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

/// One progress update while a model is downloading.
class PullProgress {
  /// Ollama's status text, e.g. "pulling manifest", "downloading …", "success".
  final String status;

  /// 0.0–1.0 during a download phase, or null when the phase has no byte counts
  /// (manifest, verifying) — the UI shows an indeterminate bar then.
  final double? fraction;

  /// True on the terminal success message.
  final bool done;

  /// Non-null if the pull failed (network, unknown model, Ollama down).
  final String? error;

  const PullProgress({
    required this.status,
    this.fraction,
    this.done = false,
    this.error,
  });
}

/// Drives model downloads through the locally running Ollama.
///
/// WHAT: streams `POST /api/pull` so the wizard can show a real progress bar. We do
/// NOT install Ollama itself — its presence is the user's responsibility (the wizard
/// detects it and guides otherwise); this only pulls a model into an Ollama that is
/// already running.
///
/// COMMENT: `/api/pull` emits one JSON object per line. Download phases carry
/// `total` + `completed` byte counts; other phases (manifest, verifying) don't, so
/// fraction is null there. The stream ends with `{"status":"success"}`.
class OllamaService {
  static const _base = 'http://localhost:11434';
  final http.Client Function() _clientFactory;

  OllamaService({http.Client Function()? clientFactory})
      : _clientFactory = clientFactory ?? http.Client.new;

  /// Pull [model] (e.g. `qwen3:14b`), yielding progress until done or error.
  ///
  /// A 9 GB pull can take many minutes; the caller keeps the wizard responsive and
  /// offers a "do it later" escape rather than blocking on completion.
  Stream<PullProgress> pull(String model) async* {
    final client = _clientFactory();
    try {
      final req = http.Request('POST', Uri.parse('$_base/api/pull'))
        ..headers['Content-Type'] = 'application/json'
        ..body = jsonEncode({'name': model, 'stream': true});

      final resp = await client.send(req).timeout(const Duration(seconds: 30));
      if (resp.statusCode != 200) {
        yield PullProgress(status: 'error', error: 'HTTP ${resp.statusCode}');
        return;
      }

      await for (final line in resp.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())) {
        if (line.trim().isEmpty) continue;
        Map<String, dynamic> obj;
        try {
          obj = jsonDecode(line) as Map<String, dynamic>;
        } catch (_) {
          continue; // skip a malformed line rather than abort the download
        }

        if (obj['error'] != null) {
          yield PullProgress(status: 'error', error: obj['error'].toString());
          return;
        }

        final status = obj['status'] as String? ?? '';
        final total = (obj['total'] as num?)?.toDouble();
        final completed = (obj['completed'] as num?)?.toDouble();
        final fraction = (total != null && total > 0 && completed != null)
            ? (completed / total).clamp(0.0, 1.0)
            : null;

        final done = status == 'success';
        yield PullProgress(status: status, fraction: fraction, done: done);
        if (done) return;
      }
    } on TimeoutException {
      yield const PullProgress(
          status: 'error', error: 'Ollama ne répond pas (localhost:11434).');
    } catch (e) {
      yield PullProgress(status: 'error', error: e.toString());
    } finally {
      client.close();
    }
  }
}
