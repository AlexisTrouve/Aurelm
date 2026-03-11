import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/app_constants.dart';
import '../services/chat_service.dart';
import '../services/chat_sessions_service.dart';

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
  final String? sessionId;
  /// Tool calls currently in progress (shown with spinner).
  final List<PendingToolCall> pendingTools;
  /// Messages typed while the LLM was busy — will be fused and sent after.
  final List<String> messageQueue;

  const ChatState({
    this.messages = const [],
    this.loading = false,
    this.error,
    this.sessionId,
    this.pendingTools = const [],
    this.messageQueue = const [],
  });

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? loading,
    String? error,
    String? sessionId,
    List<PendingToolCall>? pendingTools,
    List<String>? messageQueue,
    bool clearError = false,
    bool clearSession = false,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      loading: loading ?? this.loading,
      error: clearError ? null : (error ?? this.error),
      sessionId: clearSession
          ? null
          : (sessionId ?? this.sessionId),
      pendingTools: pendingTools ?? this.pendingTools,
      messageQueue: messageQueue ?? this.messageQueue,
    );
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

final chatServiceProvider = Provider<ChatService>(
  (_) => ChatService(port: AppConstants.botDefaultPort),
);

final chatSessionsServiceProvider = Provider<ChatSessionsService>(
  (_) => ChatSessionsService(port: AppConstants.botDefaultPort),
);

final chatProvider = StateNotifierProvider<ChatNotifier, ChatState>(
  (ref) => ChatNotifier(
    ref.watch(chatServiceProvider),
    ref.watch(chatSessionsServiceProvider),
  ),
);

class ChatNotifier extends StateNotifier<ChatState> {
  final ChatService _service;
  final ChatSessionsService _sessionsService;
  bool _cancelled = false; // set to true to silently ignore incoming events

  ChatNotifier(this._service, this._sessionsService) : super(const ChatState());

  /// Send a user message and stream the agent's response events.
  ///
  /// If the LLM is busy, the message is queued and will be fused with other
  /// queued messages when the current turn finishes.
  Future<void> send(String message) async {
    final trimmed = message.trim();
    if (trimmed.isEmpty) return;

    // LLM is busy → queue the message (shown as faded bubble)
    if (state.loading) {
      state = state.copyWith(messageQueue: [...state.messageQueue, trimmed]);
      return;
    }

    await _sendImmediate(trimmed);
  }

  Future<void> _sendImmediate(String message) async {
    _cancelled = false;

    // Append user message immediately
    final userMsg = ChatMessage(
      role: ChatRole.user,
      content: message,
      timestamp: DateTime.now(),
    );
    state = state.copyWith(
      messages: [...state.messages, userMsg],
      loading: true,
      clearError: true,
      pendingTools: [],
      messageQueue: [],
    );

    // Prepare a partial assistant message that we'll build up incrementally
    final toolCalls = <ToolCallInfo>[];
    final thinkingBlocks = <String>[];
    String responseText = '';

    try {
      final stream = _service.sendMessageStream(
        message,
        sessionId: state.sessionId,
      );

      await for (final event in stream) {
        // Cancelled — drain the stream silently without updating UI
        if (_cancelled) continue;

        switch (event) {
          case ToolStartEvent():
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
            final pending = state.pendingTools
                .where((p) => p.name != event.toolCall.name)
                .toList();
            _updateAssistantMessage(responseText, toolCalls, thinkingBlocks);
            state = state.copyWith(pendingTools: pending);

          case ThinkingEvent():
            thinkingBlocks.add(event.content);
            _updateAssistantMessage(responseText, toolCalls, thinkingBlocks);

          case TextEvent():
            responseText = event.content;
            _updateAssistantMessage(responseText, toolCalls, thinkingBlocks);

          case DoneEvent():
            state = state.copyWith(
              loading: false,
              sessionId: event.sessionId,
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

      // Safety: if stream ended without DoneEvent
      if (state.loading) {
        state = state.copyWith(loading: false, pendingTools: []);
      }
    } catch (_) {
      // Swallow connection errors (e.g. ClientException during cancel drain)
      if (state.loading) {
        state = state.copyWith(loading: false, pendingTools: [], messageQueue: []);
      }
    }

    // Drain the queue: fuse all pending messages into one and send
    if (!_cancelled) {
      final queue = state.messageQueue;
      if (queue.isNotEmpty) {
        final fused = queue.join('\n');
        state = state.copyWith(messageQueue: []);
        await _sendImmediate(fused);
      }
    }
    _cancelled = false;
  }

  /// Cancel: pop last queued message, or signal to ignore the ongoing LLM response.
  ///
  /// Does NOT close the HTTP connection (avoids ClientException).
  /// Sets _cancelled = true so incoming events are silently drained.
  /// Adds an "Annulé" indicator message instead of removing the user message.
  void cancelLast() {
    if (state.messageQueue.isNotEmpty) {
      // Remove last queued message
      final newQueue = [...state.messageQueue]..removeLast();
      state = state.copyWith(messageQueue: newQueue);
      return;
    }
    if (state.loading) {
      _cancelled = true;
      // Add "Annulé" indicator as assistant message
      final cancelMsg = ChatMessage(
        role: ChatRole.assistant,
        content: '_Action annulée._',
        timestamp: DateTime.now(),
      );
      // Remove any partial assistant message first
      final msgs = [...state.messages];
      if (msgs.isNotEmpty && msgs.last.role == ChatRole.assistant) {
        msgs.removeLast();
      }
      state = state.copyWith(
        messages: [...msgs, cancelMsg],
        loading: false,
        pendingTools: [],
        messageQueue: [],
        clearError: true,
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

  /// Start a fresh session (clears history and creates new session in DB).
  /// This is async but we fire-and-forget since the UI doesn't wait.
  Future<void> newSession() async {
    _service.cancel();
    state = const ChatState();

    // Create new session in the backend
    try {
      final sessionId = await _sessionsService.createSession('New Session');
      state = state.copyWith(sessionId: sessionId);
    } catch (e) {
      // Silently fail — user can still chat without a saved session
    }
  }

  /// Set the current session ID (e.g. when loading a saved session).
  void setSessionId(String sessionId) {
    state = state.copyWith(sessionId: sessionId);
  }
}
