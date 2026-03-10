import 'dart:convert';
import 'package:http/http.dart' as http;

import '../core/constants/app_constants.dart';

/// Response from POST /chat.
class ChatResponse {
  final String response;
  final String conversationId;

  const ChatResponse({required this.response, required this.conversationId});

  factory ChatResponse.fromJson(Map<String, dynamic> json) {
    return ChatResponse(
      response: json['response'] as String,
      conversationId: json['conversation_id'] as String,
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

    final response = await http
        .post(uri, headers: {'Content-Type': 'application/json'}, body: body)
        .timeout(const Duration(seconds: 60));

    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200) {
      return ChatResponse.fromJson(data);
    }
    throw Exception(data['error'] ?? 'Chat request failed: ${response.statusCode}');
  }
}
