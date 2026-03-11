import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/app_constants.dart';
import '../services/chat_service.dart';

// Re-export ToolCallInfo so consumers only need to import this file
export '../services/chat_service.dart' show ToolCallInfo;

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

enum ChatRole { user, assistant }

class ChatMessage {
  final ChatRole role;
  final String content;
  final DateTime timestamp;
  /// Tool calls made by the agent while generating this message (assistant only).
  final List<ToolCallInfo> toolCalls;

  const ChatMessage({
    required this.role,
    required this.content,
    required this.timestamp,
    this.toolCalls = const [],
  });
}

class ChatState {
  final List<ChatMessage> messages;
  final bool loading;
  final String? error;
  final String? conversationId;

  const ChatState({
    this.messages = const [],
    this.loading = false,
    this.error,
    this.conversationId,
  });

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? loading,
    String? error,
    String? conversationId,
    bool clearError = false,
    bool clearConversation = false,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      loading: loading ?? this.loading,
      error: clearError ? null : (error ?? this.error),
      conversationId: clearConversation
          ? null
          : (conversationId ?? this.conversationId),
    );
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

final chatServiceProvider = Provider<ChatService>(
  (_) => ChatService(port: AppConstants.botDefaultPort),
);

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>(
  (ref) => ChatNotifier(ref.watch(chatServiceProvider)),
);

class ChatNotifier extends StateNotifier<ChatState> {
  final ChatService _service;

  ChatNotifier(this._service) : super(const ChatState());

  /// Send a user message and await the agent's response.
  Future<void> send(String message) async {
    if (message.trim().isEmpty || state.loading) return;

    // Append the user message immediately for responsiveness
    final userMsg = ChatMessage(
      role: ChatRole.user,
      content: message.trim(),
      timestamp: DateTime.now(),
    );
    state = state.copyWith(
      messages: [...state.messages, userMsg],
      loading: true,
      clearError: true,
    );

    try {
      final result = await _service.sendMessage(
        message.trim(),
        conversationId: state.conversationId,
      );

      final assistantMsg = ChatMessage(
        role: ChatRole.assistant,
        content: result.response,
        timestamp: DateTime.now(),
        toolCalls: result.toolCalls,
      );

      state = state.copyWith(
        messages: [...state.messages, assistantMsg],
        loading: false,
        conversationId: result.conversationId,
      );
    } catch (e) {
      state = state.copyWith(
        loading: false,
        error: e.toString(),
      );
    }
  }

  /// Start a fresh conversation (clears history and conversation ID).
  void newConversation() {
    state = const ChatState();
  }
}
