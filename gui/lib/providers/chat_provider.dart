import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/app_constants.dart';
import '../services/chat_service.dart';

// Re-export so consumers only need to import this file
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
  /// Claude thinking blocks emitted during this turn.
  final List<String> thinkingBlocks;

  const ChatMessage({
    required this.role,
    required this.content,
    required this.timestamp,
    this.toolCalls = const [],
    this.thinkingBlocks = const [],
  });

  /// Create a copy with additional fields appended (used during streaming).
  ChatMessage copyAppending({
    String? content,
    ToolCallInfo? toolCall,
    String? thinkingBlock,
  }) {
    return ChatMessage(
      role: role,
      content: content ?? this.content,
      timestamp: timestamp,
      toolCalls: toolCall != null ? [...toolCalls, toolCall] : toolCalls,
      thinkingBlocks: thinkingBlock != null
          ? [...thinkingBlocks, thinkingBlock]
          : thinkingBlocks,
    );
  }
}

/// A tool call that's started but not yet resolved (spinner in UI).
class PendingToolCall {
  final String name;
  final String inputSummary;

  const PendingToolCall({required this.name, required this.inputSummary});
}

class ChatState {
  final List<ChatMessage> messages;
  final bool loading;
  final String? error;
  final String? conversationId;
  /// Tool calls currently in progress (shown with spinner).
  final List<PendingToolCall> pendingTools;

  const ChatState({
    this.messages = const [],
    this.loading = false,
    this.error,
    this.conversationId,
    this.pendingTools = const [],
  });

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? loading,
    String? error,
    String? conversationId,
    List<PendingToolCall>? pendingTools,
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
      pendingTools: pendingTools ?? this.pendingTools,
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

  /// Send a user message and stream the agent's response events.
  Future<void> send(String message) async {
    if (message.trim().isEmpty || state.loading) return;

    // Append user message immediately
    final userMsg = ChatMessage(
      role: ChatRole.user,
      content: message.trim(),
      timestamp: DateTime.now(),
    );
    state = state.copyWith(
      messages: [...state.messages, userMsg],
      loading: true,
      clearError: true,
      pendingTools: [],
    );

    // Prepare a partial assistant message that we'll build up incrementally
    final toolCalls = <ToolCallInfo>[];
    final thinkingBlocks = <String>[];
    String responseText = '';

    try {
      final stream = _service.sendMessageStream(
        message.trim(),
        conversationId: state.conversationId,
      );

      await for (final event in stream) {
        switch (event) {
          case ToolStartEvent():
            // Show spinner for this tool
            state = state.copyWith(
              pendingTools: [
                ...state.pendingTools,
                PendingToolCall(
                  name: event.name,
                  inputSummary: event.inputSummary,
                ),
              ],
            );

          case ToolResultEvent():
            toolCalls.add(event.toolCall);
            // Remove from pending, add to resolved list shown in UI
            final pending = state.pendingTools
                .where((p) => p.name != event.toolCall.name)
                .toList();
            // Update the assistant message in-place
            _updateAssistantMessage(
              responseText, toolCalls, thinkingBlocks,
            );
            state = state.copyWith(pendingTools: pending);

          case ThinkingEvent():
            thinkingBlocks.add(event.content);
            _updateAssistantMessage(
              responseText, toolCalls, thinkingBlocks,
            );

          case TextEvent():
            responseText = event.content;
            _updateAssistantMessage(
              responseText, toolCalls, thinkingBlocks,
            );

          case DoneEvent():
            state = state.copyWith(
              loading: false,
              conversationId: event.conversationId,
              pendingTools: [],
            );

          case ErrorEvent():
            state = state.copyWith(
              loading: false,
              error: event.message,
              pendingTools: [],
            );
        }
      }

      // Safety: if stream ended without a DoneEvent
      if (state.loading) {
        state = state.copyWith(loading: false, pendingTools: []);
      }
    } catch (e) {
      state = state.copyWith(
        loading: false,
        error: e.toString(),
        pendingTools: [],
      );
    }
  }

  /// Update or append the in-progress assistant message at the end of the list.
  void _updateAssistantMessage(
    String content,
    List<ToolCallInfo> toolCalls,
    List<String> thinkingBlocks,
  ) {
    final msgs = [...state.messages];
    final assistantMsg = ChatMessage(
      role: ChatRole.assistant,
      content: content,
      timestamp: DateTime.now(),
      toolCalls: List.unmodifiable(toolCalls),
      thinkingBlocks: List.unmodifiable(thinkingBlocks),
    );

    // Replace or append the assistant message
    if (msgs.isNotEmpty && msgs.last.role == ChatRole.assistant) {
      msgs[msgs.length - 1] = assistantMsg;
    } else {
      msgs.add(assistantMsg);
    }
    state = state.copyWith(messages: msgs);
  }

  /// Start a fresh conversation (clears history and conversation ID).
  void newConversation() {
    _service.cancel();
    state = const ChatState();
  }
}
