import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

import '../core/constants/app_constants.dart';

/// One tool call performed by the agent during a response turn.
class ToolCallInfo {
  final String name;
  final String inputSummary;
  final String resultSummary;
  final String fullResult; // full tool output for expanded view

  const ToolCallInfo({
    required this.name,
    required this.inputSummary,
    required this.resultSummary,
    this.fullResult = '',
  });

  factory ToolCallInfo.fromJson(Map<String, dynamic> json) {
    return ToolCallInfo(
      name: json['name'] as String? ?? '',
      inputSummary: json['input_summary'] as String? ?? '',
      resultSummary: json['result_summary'] as String? ?? '',
      fullResult: json['result'] as String? ?? '',
    );
  }
}

/// A single SSE event from the /chat NDJSON stream.
sealed class ChatEvent {}

/// Tool execution started (tool name + input visible, result pending).
class ToolStartEvent extends ChatEvent {
  final String name;
  final String inputSummary;
  ToolStartEvent({required this.name, required this.inputSummary});
}

/// Tool execution completed — full result available.
class ToolResultEvent extends ChatEvent {
  final ToolCallInfo toolCall;
  ToolResultEvent({required this.toolCall});
}

/// Claude thinking block.
class ThinkingEvent extends ChatEvent {
  final String content;
  ThinkingEvent({required this.content});
}

/// Final text response from the agent.
class TextEvent extends ChatEvent {
  final String content;
  TextEvent({required this.content});
}

/// Stream complete — session_id for next turn.
class DoneEvent extends ChatEvent {
  final String sessionId;
  final String sessionName;
  final List<String> sessionTags;
  DoneEvent({
    required this.sessionId,
    this.sessionName = '',
    this.sessionTags = const [],
  });
}

/// Cumulative token usage after each LLM round.
class UsageEvent extends ChatEvent {
  final int inputTokens;
  final int outputTokens;
  UsageEvent({required this.inputTokens, required this.outputTokens});
}

/// Local token estimate — context size before/after compression.
class ContextEstimateEvent extends ChatEvent {
  final int rawTokens;
  final int compressedTokens;
  final int round;
  ContextEstimateEvent({
    required this.rawTokens,
    required this.compressedTokens,
    required this.round,
  });
}

/// Conversation history compressed into a summary block.
class CompressEvent extends ChatEvent {
  final String content;
  CompressEvent({required this.content});
}

/// Multiple compress blocks merged into a resume block.
class ResumeEvent extends ChatEvent {
  final String content;
  ResumeEvent({required this.content});
}

/// Agent error.
class ErrorEvent extends ChatEvent {
  final String message;
  ErrorEvent({required this.message});
}

/// HTTP client for the /chat endpoint on the local bot server.
class ChatService {
  final int port;
  late final String _baseUrl;
  http.Client? _activeClient;

  ChatService({this.port = AppConstants.botDefaultPort}) {
    _baseUrl = 'http://127.0.0.1:$port';
  }

  /// Stream chat events from the agent in real time (NDJSON).
  ///
  /// Each event is parsed and yielded as a [ChatEvent] subclass.
  /// Tool calls appear as they resolve, not at the end.
  Stream<ChatEvent> sendMessageStream(
    String message, {
    String? sessionId,
  }) async* {
    final uri = Uri.parse('$_baseUrl${AppConstants.botChatEndpoint}');
    final body = jsonEncode({
      'message': message,
      if (sessionId != null) 'session_id': sessionId,
    });

    final client = http.Client();
    _activeClient = client;

    try {
      final request = http.Request('POST', uri)
        ..headers['Content-Type'] = 'application/json'
        ..body = body;

      final streamed = await client.send(request).timeout(
        const Duration(seconds: 180),
      );

      if (streamed.statusCode != 200) {
        yield ErrorEvent(message: 'HTTP ${streamed.statusCode}');
        return;
      }

      // Read NDJSON: one JSON object per line
      await for (final chunk in streamed.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())) {
        if (chunk.trim().isEmpty) continue;

        try {
          final json = jsonDecode(chunk) as Map<String, dynamic>;
          final type = json['type'] as String? ?? '';

          switch (type) {
            case 'tool_start':
              yield ToolStartEvent(
                name: json['name'] as String? ?? '',
                inputSummary: json['input_summary'] as String? ?? '',
              );
            case 'tool_result':
              yield ToolResultEvent(
                toolCall: ToolCallInfo.fromJson(json),
              );
            case 'thinking':
              yield ThinkingEvent(
                content: json['content'] as String? ?? '',
              );
            case 'usage':
              yield UsageEvent(
                inputTokens: json['input_tokens'] as int? ?? 0,
                outputTokens: json['output_tokens'] as int? ?? 0,
              );
            case 'context_estimate':
              yield ContextEstimateEvent(
                rawTokens: json['raw_tokens'] as int? ?? 0,
                compressedTokens: json['compressed_tokens'] as int? ?? 0,
                round: json['round'] as int? ?? 0,
              );
            case 'text':
              yield TextEvent(
                content: json['content'] as String? ?? '',
              );
            case 'compress':
              yield CompressEvent(
                content: json['content'] as String? ?? '',
              );
            case 'resume':
              yield ResumeEvent(
                content: json['content'] as String? ?? '',
              );
            case 'done':
              yield DoneEvent(
                sessionId: json['session_id'] as String? ?? '',
                sessionName: json['session_name'] as String? ?? '',
                sessionTags: (json['session_tags'] as List?)
                    ?.cast<String>() ?? const [],
              );
            case 'error':
              yield ErrorEvent(
                message: json['message'] as String? ?? 'Unknown error',
              );
          }
        } catch (_) {
          // Skip malformed lines
        }
      }
    } finally {
      _activeClient = null;
      client.close();
    }
  }

  /// Cancel the active request (if any).
  void cancel() {
    _activeClient?.close();
    _activeClient = null;
  }
}
