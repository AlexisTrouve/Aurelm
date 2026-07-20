// Unit tests for OllamaService.pull — proves the /api/pull stream parse against
// Ollama's documented NDJSON format, deterministically, with no live server.
//
// WHY a mock and not a live pull: on the dev machine port 11434 is blocked at the
// socket level, and a real 9 GB pull is impractical in a test anyway. The parse
// (status → fraction from total/completed → success → done, plus errors) is the
// novel logic; the format modelled here matches Ollama's real /api/pull output.
import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:flutter_test/flutter_test.dart';

import 'package:aurelm_gui/services/ollama_service.dart';

/// Returns a streamed response whose body is the given NDJSON lines.
class _FakeClient extends http.BaseClient {
  final List<String> lines;
  final int statusCode;
  _FakeClient(this.lines, {this.statusCode = 200});

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final bytes = utf8.encode(lines.map((l) => '$l\n').join());
    return http.StreamedResponse(Stream.value(bytes), statusCode);
  }
}

OllamaService _serviceFor(List<String> lines, {int status = 200}) =>
    OllamaService(clientFactory: () => _FakeClient(lines, statusCode: status));

void main() {
  test('parses a normal download to completion with fractions', () async {
    // Exactly the shape Ollama streams: manifest (no bytes), download phases with
    // total/completed, verify/write (no bytes), then success.
    final svc = _serviceFor([
      '{"status":"pulling manifest"}',
      '{"status":"pulling abc","digest":"sha256:abc","total":1000,"completed":250}',
      '{"status":"pulling abc","digest":"sha256:abc","total":1000,"completed":1000}',
      '{"status":"verifying sha256 digest"}',
      '{"status":"writing manifest"}',
      '{"status":"success"}',
    ]);

    final updates = await svc.pull('qwen3:14b').toList();

    // Manifest phase has no byte counts → indeterminate.
    expect(updates.first.fraction, isNull);
    // The two download phases report 0.25 then 1.0.
    final fractions = updates.map((u) => u.fraction).whereType<double>().toList();
    expect(fractions, [0.25, 1.0]);
    // Terminal update is success/done, and nothing errored.
    expect(updates.last.done, isTrue);
    expect(updates.any((u) => u.error != null), isFalse);
  });

  test('an error object in the stream surfaces as an error and stops', () async {
    final svc = _serviceFor([
      '{"status":"pulling manifest"}',
      '{"error":"model \'nope\' not found"}',
      '{"status":"success"}', // must never be reached
    ]);

    final updates = await svc.pull('nope').toList();

    expect(updates.last.error, contains('not found'));
    expect(updates.any((u) => u.done), isFalse,
        reason: 'the stream must stop at the error, not report success');
  });

  test('a non-200 response is reported as an error', () async {
    final svc = _serviceFor(['irrelevant'], status: 500);
    final updates = await svc.pull('qwen3:14b').toList();
    expect(updates.single.error, contains('500'));
  });

  test('malformed lines are skipped, not fatal', () async {
    final svc = _serviceFor([
      'not json at all',
      '{"status":"pulling manifest"}',
      '{"status":"success"}',
    ]);
    final updates = await svc.pull('qwen3:14b').toList();
    expect(updates.last.done, isTrue);
  });
}
