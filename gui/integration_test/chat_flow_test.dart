// E2E net for the chat screen — the SAFETY net that must stay green across the
// chat_screen.dart decomposition (2267-line monolith → components).
//
// WHY this exists: app_boot_test.dart explicitly SKIPS Chat because it needed
// "live-bot HTTP". That is the wrong reason to skip an E2E — the LLM/proxy is not
// the UI under test. Here we fake ONLY the network boundary (ChatService's event
// stream + the sessions service) and drive the REAL ChatScreen with REAL taps and
// key presses. Everything the refactor could break — the notifier wiring, the
// message list, tool cards, the pending spinner, cancel, and the busy-queue — is
// asserted through the rendered widget tree, not read off the source.
//
// WHY pump ChatScreen directly (not the whole app via the nav rail): the target of
// the refactor IS ChatScreen, so the net targets it; it also sidesteps the shell's
// 5s health-poll timer that forces "never pumpAndSettle" elsewhere.
//
// Faked seams (verified against the provider map):
//  - chatServiceProvider        -> _FakeChatService (a test-driven event stream)
//  - chatSessionsServiceProvider -> _FakeSessionsService (empty, offline-tolerant)
//  - botHealthProvider          -> always online, so the input bar is ENABLED
//  - loreLinkTextProvider       -> identity, so assistant bubbles need no DB
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:aurelm_gui/providers/bot_provider.dart';
import 'package:aurelm_gui/providers/chat_provider.dart';
import 'package:aurelm_gui/providers/chat_sessions_provider.dart';
import 'package:aurelm_gui/providers/database_provider.dart';
import 'package:aurelm_gui/providers/lore_links_provider.dart';
import 'package:aurelm_gui/screens/chat/chat_screen.dart';
import 'package:aurelm_gui/services/chat_service.dart';
import 'package:aurelm_gui/services/chat_sessions_service.dart';

// ---------------------------------------------------------------------------
// Fakes — the ONLY thing mocked is the network boundary.
// ---------------------------------------------------------------------------

/// A ChatService whose stream the TEST drives event-by-event, so intermediate
/// states (a tool pending before its result; loading while a message is queued)
/// are observable between pumps. Each send opens a fresh controller exposed as
/// [current]; closing it ends that turn (and triggers the queue drain).
class _FakeChatService extends ChatService {
  _FakeChatService() : super(port: 0);

  /// Every message the screen actually dispatched, in order. Proves what was sent
  /// (and that a queued message was fused and re-sent after the busy turn).
  final List<String> sent = [];
  final List<StreamController<ChatEvent>> _all = [];
  StreamController<ChatEvent>? _current;

  StreamController<ChatEvent> get current => _current!;

  @override
  Stream<ChatEvent> sendMessageStream(
    String message, {
    String? sessionId,
    String? model,
    String? effort,
    bool showThinking = false,
  }) {
    sent.add(message);
    final c = StreamController<ChatEvent>();
    _current = c;
    _all.add(c);
    return c.stream;
  }

  @override
  Future<ChatModels> fetchModels() async =>
      const ChatModels(models: [], defaultModel: '');

  @override
  void cancel() {}

  /// Close any stream still open — keeps the test from leaking a subscription.
  Future<void> disposeAll() async {
    for (final c in _all) {
      if (!c.isClosed) await c.close();
    }
  }
}

/// Sessions service that never touches the network. All reads return empty; all
/// writes are no-ops. The base class already swallows errors, but overriding the
/// throwing reads (listSessions) keeps the drawer's provider deterministic.
class _FakeSessionsService extends ChatSessionsService {
  _FakeSessionsService() : super(port: 0);

  @override
  Future<List<ChatSessionPreview>> listSessions(
          {bool archived = false, String? tagFilter}) async =>
      [];
  @override
  Future<String> createSession(String name) async => 'test-session';
  @override
  Future<int> getContextSize(String sessionId) async => 0;
  @override
  Future<List<Map<String, dynamic>>> getSessionMessages(
          String sessionId) async =>
      [];
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

/// Pump a few fixed frames — no pumpAndSettle (a test-driven stream stays open
/// deliberately, and we want to observe frames between events).
Future<void> _settle(WidgetTester tester, {int frames = 6}) async {
  for (var i = 0; i < frames; i++) {
    await tester.pump(const Duration(milliseconds: 60));
  }
}

/// Boot just the ChatScreen with the four faked seams. Returns the fake service
/// so the test can drive its stream and inspect what was sent.
Future<_FakeChatService> _bootChat(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(1400, 900));
  addTearDown(() => tester.binding.setSurfaceSize(null));

  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();

  final fake = _FakeChatService();
  addTearDown(fake.disposeAll);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        sharedPrefsProvider.overrideWithValue(prefs),
        chatServiceProvider.overrideWithValue(fake),
        chatSessionsServiceProvider.overrideWithValue(_FakeSessionsService()),
        // Online → input bar enabled (send button + field active).
        botHealthProvider.overrideWith((ref) => Stream.value(true)),
        // Assistant bubbles get their text verbatim; no DB, no isolate.
        loreLinkTextProvider.overrideWith((ref, raw) => raw),
      ],
      child: const MaterialApp(home: ChatScreen()),
    ),
  );
  await _settle(tester);
  return fake;
}

/// The message input — the only multiline TextField in the chat column.
final _input = find.byType(TextField);

/// The send button (IconButton.filled with the send icon).
final _sendBtn = find.byIcon(Icons.send);

/// Find MarkdownBody-rendered (RichText) assistant text containing [s].
Finder _assistantText(String s) => find.byWidgetPredicate(
      (w) => w is RichText && w.text.toPlainText().contains(s),
      description: 'assistant markdown containing "$s"',
    );

Future<void> _type(WidgetTester tester, String text) async {
  await tester.enterText(_input, text);
  await _settle(tester, frames: 2);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('empty state shows before any message', (tester) async {
    await _bootChat(tester);
    // 'Aurelm Agent' also appears in the app bar; the hero icon is unique to the
    // empty state.
    expect(find.byIcon(Icons.auto_awesome), findsOneWidget,
        reason: 'a fresh chat must show the empty-state hero');
    expect(find.byType(MarkdownBody), findsNothing);
  });

  testWidgets('sending a message renders the user bubble, a tool card and the answer',
      (tester) async {
    final fake = await _bootChat(tester);

    await _type(tester, 'Les Confluents ont-ils du bronze ?');
    await tester.tap(_sendBtn);
    await _settle(tester);

    // The message was dispatched to the service and the user bubble rendered.
    expect(fake.sent, ['Les Confluents ont-ils du bronze ?']);
    expect(find.text('Les Confluents ont-ils du bronze ?'), findsOneWidget,
        reason: 'the user bubble must show the typed text');
    // Input cleared after send.
    expect(tester.widget<TextField>(_input).controller!.text, '');

    // Drive the streamed turn: a tool call, then the answer, then done.
    fake.current.add(ToolStartEvent(name: 'searchLore', inputSummary: 'bronze'));
    await _settle(tester);
    fake.current.add(ToolResultEvent(
      toolCall: const ToolCallInfo(
        name: 'searchLore',
        inputSummary: 'bronze',
        resultSummary: '0 résultats',
        fullResult: 'Aucune entité bronze.',
      ),
    ));
    await _settle(tester);
    fake.current.add(TextEvent(content: 'Non, aucun bronze attesté chez les Confluents.'));
    fake.current.add(DoneEvent(sessionId: 's1', sessionName: 'Bronze', sessionTags: const []));
    await fake.current.close();
    await _settle(tester);

    // The resolved tool call rendered as a card (its manage_search icon).
    expect(find.byIcon(Icons.manage_search), findsOneWidget,
        reason: 'a resolved tool call must render a tool card');
    // The assistant answer rendered (Markdown → RichText).
    expect(_assistantText('aucun bronze attesté'), findsWidgets,
        reason: 'the final answer must render in an assistant bubble');
    // Turn finished → loading indicator gone.
    expect(find.byType(LinearProgressIndicator), findsNothing,
        reason: 'DoneEvent must clear the loading state');
  });

  testWidgets('a tool in flight shows the pending spinner and loading bar',
      (tester) async {
    final fake = await _bootChat(tester);
    await _type(tester, 'question');
    await tester.tap(_sendBtn);
    await _settle(tester);

    // Tool started but not resolved → pending chip spinner + loading bar visible.
    fake.current.add(ToolStartEvent(name: 'timeline', inputSummary: 'T1..T3'));
    await _settle(tester);
    expect(find.byType(CircularProgressIndicator), findsWidgets,
        reason: 'an unresolved tool must show a pending spinner');
    expect(find.byType(LinearProgressIndicator), findsOneWidget,
        reason: 'the turn is still loading');

    // Resolving it removes the pending chip and leaves the tool card.
    fake.current.add(ToolResultEvent(
      toolCall: const ToolCallInfo(
        name: 'timeline',
        inputSummary: 'T1..T3',
        resultSummary: '3 tours',
      ),
    ));
    fake.current.add(DoneEvent(sessionId: 's1'));
    await fake.current.close();
    await _settle(tester);
    expect(find.byType(CircularProgressIndicator), findsNothing,
        reason: 'the pending spinner must clear once the tool resolves');
    expect(find.byIcon(Icons.manage_search), findsOneWidget);
  });

  testWidgets('Escape cancels an in-flight turn', (tester) async {
    final fake = await _bootChat(tester);
    await _type(tester, 'question longue');
    await tester.tap(_sendBtn);
    await _settle(tester);

    // Turn is in flight (a tool started, no answer yet).
    fake.current.add(ToolStartEvent(name: 'deepExplore', inputSummary: '...'));
    await _settle(tester);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);

    // Press Escape → the notifier cancels, drops the partial, shows "annulée".
    await tester.sendKeyEvent(LogicalKeyboardKey.escape);
    await _settle(tester);

    expect(_assistantText('annulée'), findsWidgets,
        reason: 'cancelling must post the "_Action annulée._" indicator');
    expect(find.byType(LinearProgressIndicator), findsNothing,
        reason: 'cancel must clear the loading state');

    // Close the (cancelled) stream while the notifier is still mounted, so its
    // dangling `await for` doesn't resume and touch state after dispose.
    await fake.current.close();
    await _settle(tester);
  });

  testWidgets('typing while busy queues the message, then it is sent after',
      (tester) async {
    final fake = await _bootChat(tester);
    await _type(tester, 'première question');
    await tester.tap(_sendBtn);
    await _settle(tester);

    // First turn is busy (open stream). Type + send a second message → it queues.
    fake.current.add(ToolStartEvent(name: 'searchLore', inputSummary: 'x'));
    await _settle(tester);
    await _type(tester, 'deuxième question');
    await tester.tap(_sendBtn);
    await _settle(tester);

    // Only the first message has been dispatched; the second is a faded queue bubble.
    expect(fake.sent, ['première question'],
        reason: 'a message typed while busy must NOT be sent immediately');
    expect(find.text('deuxième question'), findsOneWidget,
        reason: 'the queued message must render as a (faded) bubble');

    // Finish the first turn → the queue drains and the second message is sent.
    fake.current.add(TextEvent(content: 'réponse une'));
    fake.current.add(DoneEvent(sessionId: 's1'));
    await fake.current.close();
    await _settle(tester);

    expect(fake.sent, ['première question', 'deuxième question'],
        reason: 'the queued message must be dispatched once the turn finishes');

    // The drain opened a SECOND stream (now `current`); close it while mounted.
    fake.current.add(DoneEvent(sessionId: 's1'));
    await fake.current.close();
    await _settle(tester);
  });
}
