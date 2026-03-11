import 'dart:convert';
import 'package:http/http.dart' as http;

import '../core/constants/app_constants.dart';

/// One tool call performed by the agent during a response turn.
class ToolCallInfo {
  final String name;
  final String inputSummary;   // e.g. "query='bronze', civName='Confluence'"
  final String resultSummary;  // first non-empty line of the tool result

  const ToolCallInfo({
    required this.name,
    required this.inputSummary,
    required this.resultSummary,
  });

  factory ToolCallInfo.fromJson(Map<String, dynamic> json) {
    return ToolCallInfo(
      name: json['name'] as String? ?? '',
      inputSummary: json['input_summary'] as String? ?? '',
      resultSummary: json['result_summary'] as String? ?? '',
    );
  }
}

/// Response from POST /chat.
class ChatResponse {
  final String response;
  final String conversationId;
  final List<ToolCallInfo> toolCalls;

  const ChatResponse({
    required this.response,
    required this.conversationId,
    this.toolCalls = const [],
  });

  factory ChatResponse.fromJson(Map<String, dynamic> json) {
    final rawCalls = json['tool_calls'] as List<dynamic>? ?? [];
    return ChatResponse(
      response: json['response'] as String,
      conversationId: json['conversation_id'] as String,
      toolCalls: rawCalls
          .map((e) => ToolCallInfo.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// HTTP client for the /chat endpoint on the local bot server.
class ChatService {
  final int port;
  late final String _baseUrl;

  ChatService({this.port = AppConstants.botDefaultPort}) {
    _baseUrl = 'http://127.0.0.1:$port';
  }

  /// Send [message] to the agent, optionally continuing [conversationId].
  ///
  /// Returns the assistant's text response and the conversation ID
  /// (use it on next calls to maintain context).
  Future<ChatResponse> sendMessage(
    String message, {
    String? conversationId,
  }) async {
    final uri = Uri.parse('$_baseUrl${AppConstants.botChatEndpoint}');
    final body = jsonEncode({
      'message': message,
      if (conversationId != null) 'conversation_id': conversationId,
    });

    // 180s — multi-tool chains (searchLore × N + getEntityDetail × N) can take time
    final response = await http
        .post(uri, headers: {'Content-Type': 'application/json'}, body: body)
        .timeout(const Duration(seconds: 180));

    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200) {
      return ChatResponse.fromJson(data);
    }
    throw Exception(data['error'] ?? 'Chat request failed: ${response.statusCode}');
  }
}
