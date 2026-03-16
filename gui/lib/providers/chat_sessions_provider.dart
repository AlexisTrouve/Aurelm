import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/app_constants.dart';
import '../services/chat_sessions_service.dart';

// Re-export
export '../services/chat_sessions_service.dart' show ChatSessionPreview;

// ---------------------------------------------------------------------------
// State Models
// ---------------------------------------------------------------------------

class SessionsFilterState {
  final bool archived;
  final String? selectedTag;

  const SessionsFilterState({
    this.archived = false,
    this.selectedTag,
  });

  SessionsFilterState copyWith({
    bool? archived,
    String? selectedTag,
    bool clearTag = false,
  }) {
    return SessionsFilterState(
      archived: archived ?? this.archived,
      selectedTag: clearTag ? null : (selectedTag ?? this.selectedTag),
    );
  }
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

final chatSessionsServiceProvider = Provider<ChatSessionsService>(
  (_) => ChatSessionsService(port: AppConstants.botDefaultPort),
);

final sessionsFilterProvider = StateProvider<SessionsFilterState>(
  (_) => const SessionsFilterState(),
);

/// List of sessions filtered by current filter state.
final filteredSessionsProvider = FutureProvider<List<ChatSessionPreview>>(
  (ref) async {
    final service = ref.watch(chatSessionsServiceProvider);
    final filter = ref.watch(sessionsFilterProvider);

    return service.listSessions(
      archived: filter.archived,
      tagFilter: filter.selectedTag,
    );
  },
);

/// All unique tags across sessions (for filter dropdown).
final allSessionTagsProvider = FutureProvider<List<String>>(
  (ref) async {
    final service = ref.watch(chatSessionsServiceProvider);
    final sessions = await service.listSessions(archived: false);

    final tags = <String>{};
    for (final session in sessions) {
      tags.addAll(session.tags);
    }

    return tags.toList()..sort();
  },
);

// ---------------------------------------------------------------------------
// Notifier
// ---------------------------------------------------------------------------

class SessionsNotifier {
  final ChatSessionsService _service;

  SessionsNotifier(this._service);

  Future<String> createSession(String name) async {
    final sessionId = await _service.createSession(name);
    return sessionId;
  }

  Future<void> renameSession(String sessionId, String newName) async {
    await _service.renameSession(sessionId, newName);
  }

  Future<void> toggleArchive(String sessionId, bool archived) async {
    await _service.toggleArchive(sessionId, archived);
  }

  Future<void> deleteSession(String sessionId) async {
    await _service.deleteSession(sessionId);
  }

  Future<void> addTag(String sessionId, String tag) async {
    await _service.addTag(sessionId, tag);
  }

  Future<void> removeTag(String sessionId, String tag) async {
    await _service.removeTag(sessionId, tag);
  }

  /// Clone une session avec tous ses messages et tags.
  /// Retourne le nouveau session_id ou null en cas d'échec.
  Future<String?> duplicateSession(String sessionId) async {
    return _service.duplicateSession(sessionId);
  }
}

final sessionsProvider = Provider<SessionsNotifier>(
  (ref) => SessionsNotifier(ref.watch(chatSessionsServiceProvider)),
);

/// Sessions récentes taggées avec le nom d'une civ. Retourne [] si bot offline.
final civSessionsProvider =
    FutureProvider.family<List<ChatSessionPreview>, String>((ref, civName) async {
  final service = ref.watch(chatSessionsServiceProvider);
  try {
    final sessions = await service.listSessions(
      archived: false,
      tagFilter: civName,
    );
    return sessions.take(5).toList();
  } catch (_) {
    // Bot offline — dégradé silencieux
    return [];
  }
});
