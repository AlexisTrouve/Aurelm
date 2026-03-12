import 'dart:convert';
import 'package:http/http.dart' as http;

import '../core/constants/app_constants.dart';

/// Session metadata (preview for list).
class ChatSessionPreview {
  final String sessionId;
  final String name;
  final int messageCount;
  final List<String> tags;
  final bool archived;
  final String createdAt;
  final String updatedAt;
  final String? lastMessage;

  ChatSessionPreview({
    required this.sessionId,
    required this.name,
    required this.messageCount,
    required this.tags,
    required this.archived,
    required this.createdAt,
    required this.updatedAt,
    this.lastMessage,
  });

  factory ChatSessionPreview.fromJson(Map<String, dynamic> json) {
    return ChatSessionPreview(
      sessionId: json['session_id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      messageCount: json['message_count'] as int? ?? 0,
      tags: List<String>.from((json['tags'] as List?) ?? []),
      archived: json['archived'] as bool? ?? false,
      createdAt: json['created_at'] as String? ?? '',
      updatedAt: json['updated_at'] as String? ?? '',
      lastMessage: json['last_message'] as String?,
    );
  }
}

/// HTTP client for session management endpoints.
class ChatSessionsService {
  final int port;
  late final String _baseUrl;

  ChatSessionsService({this.port = AppConstants.botDefaultPort}) {
    _baseUrl = 'http://127.0.0.1:$port';
  }

  /// GET /chat/sessions — List all sessions.
  Future<List<ChatSessionPreview>> listSessions({
    bool archived = false,
    String? tagFilter,
  }) async {
    final uri = Uri.parse('$_baseUrl${AppConstants.botChatEndpoint}/sessions')
        .replace(queryParameters: {
      'archived': archived.toString(),
      if (tagFilter != null) 'tag': tagFilter,
    });

    try {
      final response = await http.get(uri).timeout(const Duration(seconds: 10));
      if (response.statusCode != 200) {
        throw Exception('Failed to list sessions: ${response.statusCode}');
      }

      final json = jsonDecode(response.body) as Map<String, dynamic>;
      final sessions = (json['sessions'] as List<dynamic>? ?? [])
          .cast<Map<String, dynamic>>()
          .map(ChatSessionPreview.fromJson)
          .toList();

      return sessions;
    } catch (e) {
      throw Exception('Error listing sessions: $e');
    }
  }

  /// POST /chat/sessions — Create a new session.
  Future<String> createSession(String name) async {
    final uri = Uri.parse('$_baseUrl${AppConstants.botChatEndpoint}/sessions');
    final body = jsonEncode({'name': name});

    try {
      final response = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode != 201) {
        throw Exception('Failed to create session: ${response.statusCode}');
      }

      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return json['session_id'] as String? ?? '';
    } catch (e) {
      throw Exception('Error creating session: $e');
    }
  }

  /// POST /chat/sessions/{session_id}/rename — Rename a session.
  Future<void> renameSession(String sessionId, String newName) async {
    final uri = Uri.parse(
        '$_baseUrl${AppConstants.botChatEndpoint}/sessions/$sessionId/rename');
    final body = jsonEncode({'name': newName});

    try {
      final response = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode != 200) {
        throw Exception('Failed to rename session: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error renaming session: $e');
    }
  }

  /// POST /chat/sessions/{session_id}/archive — Archive/unarchive a session.
  Future<void> toggleArchive(String sessionId, bool archived) async {
    final uri = Uri.parse(
        '$_baseUrl${AppConstants.botChatEndpoint}/sessions/$sessionId/archive');
    final body = jsonEncode({'archived': archived});

    try {
      final response = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode != 200) {
        throw Exception('Failed to toggle archive: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error toggling archive: $e');
    }
  }

  /// DELETE /chat/sessions/{session_id} — Delete a session.
  Future<void> deleteSession(String sessionId) async {
    final uri = Uri.parse(
        '$_baseUrl${AppConstants.botChatEndpoint}/sessions/$sessionId');

    try {
      final response =
          await http.delete(uri).timeout(const Duration(seconds: 10));

      if (response.statusCode != 200) {
        throw Exception('Failed to delete session: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error deleting session: $e');
    }
  }

  /// GET /chat/sessions/{session_id}/messages — Load full message history.
  ///
  /// Returns raw message maps from the backend. The caller ([ChatNotifier])
  /// is responsible for converting them into [ChatMessage] objects.
  Future<List<Map<String, dynamic>>> getSessionMessages(String sessionId) async {
    final uri = Uri.parse(
        '$_baseUrl${AppConstants.botChatEndpoint}/sessions/$sessionId/messages');

    try {
      final response = await http.get(uri).timeout(const Duration(seconds: 10));
      if (response.statusCode != 200) {
        throw Exception('Failed to load messages: ${response.statusCode}');
      }

      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return List<Map<String, dynamic>>.from(data['messages'] as List? ?? []);
    } catch (e) {
      throw Exception('Error loading session messages: $e');
    }
  }

  /// POST /bot/reload-db — Hot-swap the active game database.
  ///
  /// Called from the settings screen when the user selects a new DB file.
  /// Silently succeeds if the bot is not running.
  Future<void> reloadDb(String dbPath) async {
    final uri = Uri.parse('$_baseUrl/bot/reload-db');

    final response = await http
        .post(
          uri,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'db_path': dbPath}),
        )
        .timeout(const Duration(seconds: 10));

    if (response.statusCode != 200) {
      throw Exception('Failed to reload db: ${response.statusCode}');
    }
  }

  /// POST /chat/sessions/{session_id}/tags — Add a tag to a session.
  Future<void> addTag(String sessionId, String tag) async {
    final uri = Uri.parse(
        '$_baseUrl${AppConstants.botChatEndpoint}/sessions/$sessionId/tags');
    final body = jsonEncode({'tag': tag});

    try {
      final response = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode != 200) {
        throw Exception('Failed to add tag: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error adding tag: $e');
    }
  }

  /// DELETE /chat/sessions/{session_id}/tags/{tag} — Remove a tag.
  Future<void> removeTag(String sessionId, String tag) async {
    final uri = Uri.parse(
        '$_baseUrl${AppConstants.botChatEndpoint}/sessions/$sessionId/tags/$tag');

    try {
      final response =
          await http.delete(uri).timeout(const Duration(seconds: 10));

      if (response.statusCode != 200) {
        throw Exception('Failed to remove tag: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error removing tag: $e');
    }
  }
}
