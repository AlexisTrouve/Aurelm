// E2E harness — boot + per-screen navigation smoke.
//
// WHAT: boots the real AurelmApp headless (Windows desktop) against a fixture
// SQLite DB, then verifies each E2E-friendly screen renders when navigated to
// via the real NavigationRail. One test PER screen so a broken screen surfaces
// individually instead of aborting the whole journey (a pass/fail matrix = "what
// works vs what's broken", the actual goal of E2E-verifying this UI).
//
// WHY these two overrides and nothing else (verified via the seam map):
//  - sharedPrefsProvider: the app throws without it; we feed a MOCK whose only
//    seeded key is the DB path, so DbPathNotifier._init() (env → this pref key,
//    both synchronous) resolves the fixture with no env-var propagation risk.
//  - autoStartBotProvider: the ONLY hard startup blocker — watched at app.dart:15,
//    it would Process.start('py -3.12 -m bot') and block ~15s. Neutralized.
// The DB is NOT overridden: the real dbPathProvider/databaseProvider open the
// fixture file (in-memory is a trap — the core tables are Python-owned).
//
// COMMENT: we pump fixed frames, never pumpAndSettle — the shell watches a 5s
// bot-health poll (a periodic timer), so the tree never fully "settles".
//
// SKIPPED (rewrite candidates per the seam map): Chat/Sessions (live-bot HTTP +
// 2114-line monolith) and Map (CustomPainter, no test hooks).
//
// FIXTURE: Phase 1 points at a machine-local copy of a real dev DB to prove the
// screens render on realistic data. Phase 2 swaps _fixtureDb for a small,
// committable, deterministically-seeded fixture so tests can assert known rows.
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:aurelm_gui/app.dart';
import 'package:aurelm_gui/providers/bot_provider.dart';
import 'package:aurelm_gui/providers/database_provider.dart';
import 'package:aurelm_gui/screens/dashboard/dashboard_screen.dart';
import 'package:aurelm_gui/screens/entities/entity_browser_screen.dart';
import 'package:aurelm_gui/screens/timeline/timeline_screen.dart';
import 'package:aurelm_gui/screens/graph/graph_screen.dart';
import 'package:aurelm_gui/screens/graph/widgets/ego_painter.dart';
import 'package:aurelm_gui/screens/subjects/subject_browser_screen.dart';
import 'package:aurelm_gui/screens/settings/settings_screen.dart';
import 'package:aurelm_gui/screens/settings/agent_memory_screen.dart';
import 'package:aurelm_gui/screens/civilization/civ_relations_screen.dart';
import 'package:aurelm_gui/providers/enrollment_provider.dart';
import 'package:aurelm_gui/screens/onboarding/setup_wizard.dart';

/// Deterministic fixture DB, built by `integration_test/fixtures/build_fixture.py`.
/// Resolved from the current directory (flutter test runs with cwd = gui/), so
/// the suite is portable — no machine-specific absolute path. Run the builder
/// once before the tests (CI does this as a pre-step).
final _fixtureDb =
    '${Directory.current.path}/integration_test/fixtures/e2e.db';

/// Pump N fixed frames — avoids pumpAndSettle hanging on the 5s health poll.
Future<void> _pumpFor(WidgetTester tester, {int frames = 20}) async {
  for (var i = 0; i < frames; i++) {
    await tester.pump(const Duration(milliseconds: 300));
  }
}

/// Boot the real app headless with the fixture DB and no bot subprocess.
///
/// setupCompleteProvider is forced true: these tests exercise an ALREADY-ACTIVATED
/// instance. Without it the first-run wizard legitimately takes over the screen and
/// every screen assertion below fails — which is exactly how this suite caught the
/// gate being added.
Future<void> _bootApp(WidgetTester tester) async {
  SharedPreferences.setMockInitialValues({'aurelm_db_path': _fixtureDb});
  final prefs = await SharedPreferences.getInstance();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        sharedPrefsProvider.overrideWithValue(prefs),
        autoStartBotProvider.overrideWith((ref) async {}),
        setupCompleteProvider.overrideWith((ref) async => true),
      ],
      child: const AurelmApp(),
    ),
  );
  await _pumpFor(tester);
}

/// Tap a NavigationRail destination by its (unselected) icon, scoped to the rail
/// so a same icon elsewhere on screen can't be hit by mistake.
Future<void> _tapNav(WidgetTester tester, IconData icon) async {
  final navIcon = find.descendant(
    of: find.byType(NavigationRail),
    matching: find.byIcon(icon),
  );
  expect(navIcon, findsOneWidget, reason: 'nav destination for $icon must exist');
  await tester.tap(navIcon);
  await _pumpFor(tester, frames: 16);
}

/// One navigable screen: its rail icon + the widget that proves it rendered.
typedef _Screen = ({String name, IconData icon, Finder finder});

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  // Boot proof: the app comes up on the fixture DB (initialLocation '/entities').
  // The gate itself: an instance that was never activated must land on the wizard,
  // not on a shell backed by a bot it has no key for. Locks both directions —
  // _bootApp above proves an activated instance still reaches the app.
  testWidgets('an un-activated instance shows the setup wizard, not the shell',
      (tester) async {
    SharedPreferences.setMockInitialValues({'aurelm_db_path': _fixtureDb});
    final prefs = await SharedPreferences.getInstance();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPrefsProvider.overrideWithValue(prefs),
          autoStartBotProvider.overrideWith((ref) async {}),
          setupCompleteProvider.overrideWith((ref) async => false),
        ],
        child: const AurelmApp(),
      ),
    );
    await _pumpFor(tester, frames: 12);

    expect(find.byType(SetupWizard), findsOneWidget);
    expect(find.byType(NavigationRail), findsNothing,
        reason: 'the app shell must not be reachable before activation');
  });

  testWidgets('boots headless on a fixture DB and renders the Entities shell',
      (tester) async {
    await _bootApp(tester);
    expect(find.text('No database configured'), findsNothing,
        reason: 'fixture DB should have loaded via the prefs seam');
    expect(find.byType(EntityBrowserScreen), findsOneWidget);
  });

  // Per-screen navigation: tap each E2E-friendly destination from the initial
  // Entities screen and assert the target screen renders (no build throw).
  final screens = <_Screen>[
    (name: 'Dashboard', icon: Icons.dashboard_outlined, finder: find.byType(DashboardScreen)),
    (name: 'Timeline', icon: Icons.timeline_outlined, finder: find.byType(TimelineScreen)),
    (name: 'Relations', icon: Icons.hub_outlined, finder: find.byType(CivRelationsScreen)),
    (name: 'Graph', icon: Icons.scatter_plot_outlined, finder: find.byType(GraphScreen)),
    (name: 'Sujets', icon: Icons.task_alt_outlined, finder: find.byType(SubjectBrowserScreen)),
    (name: 'Settings', icon: Icons.settings_outlined, finder: find.byType(SettingsScreen)),
  ];

  for (final s in screens) {
    testWidgets('navigates to and renders ${s.name}', (tester) async {
      await _bootApp(tester);
      await _tapNav(tester, s.icon);
      expect(s.finder, findsOneWidget,
          reason: '${s.name} screen should render on real fixture data');
    });
  }

  // Graph happy-path: the per-screen loop only proves the empty GraphScreen
  // mounts (no ego center picked). This clicks a real entity in the left list
  // and proves the ego graph actually PAINTS — the CustomPaint replaces the
  // "pick an entity" empty state. Rubanc has relations in the fixture
  // (member_of / located_in, + a depth-2 worships), so its ego is non-empty.
  testWidgets('selecting an entity paints the ego graph', (tester) async {
    await _bootApp(tester);
    await _tapNav(tester, Icons.scatter_plot_outlined);
    expect(find.byType(GraphScreen), findsOneWidget);
    // Before selection: the empty-state prompt is shown, no graph canvas.
    expect(find.text('Sélectionne une entité'), findsOneWidget);

    // Tap "Rubanc" in the left entity list to make it the ego center.
    final rubanc = find.text('Rubanc');
    expect(rubanc, findsWidgets, reason: 'fixture entity must appear in the list');
    await tester.tap(rubanc.first);
    await _pumpFor(tester, frames: 16);

    // After selection: the ego renders — empty state gone, the EgoPainter drawn.
    expect(find.text('Sélectionne une entité'), findsNothing,
        reason: 'picking an entity must dismiss the empty state');
    expect(find.text('Aucune relation'), findsNothing,
        reason: 'Rubanc has relations — must not fall to the no-relations state');
    final egoPaint = find.byWidgetPredicate(
        (w) => w is CustomPaint && w.painter is EgoPainter);
    expect(egoPaint, findsOneWidget,
        reason: 'the ego graph must actually paint on the selected entity');
  });

  // Agent-memory review — a Settings sub-route (no rail icon). Opens it via the
  // Settings entry and asserts the fixture's two memories render.
  testWidgets('Settings opens the agent-memory review with its memories',
      (tester) async {
    // Tall viewport so the settings ListView (lazy) builds the Agent entry that
    // sits below the fold; reset after so other tests keep the default size.
    await tester.binding.setSurfaceSize(const Size(1200, 2600));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await _bootApp(tester);
    await _tapNav(tester, Icons.settings_outlined);
    final entry = find.text('Mémoire de l\'agent');
    expect(entry, findsWidgets, reason: 'Settings must list the agent-memory entry');
    await tester.ensureVisible(entry.first);
    await _pumpFor(tester, frames: 4);
    await tester.tap(entry.first);
    await _pumpFor(tester, frames: 16);

    expect(find.byType(AgentMemoryScreen), findsOneWidget);
    expect(find.textContaining('bronze'), findsWidgets,
        reason: 'the fixture fact memory must render');
    expect(find.textContaining('citer le tour'), findsWidgets,
        reason: 'the fixture preference memory must render');
    expect(find.text('dès T2'), findsOneWidget,
        reason: 'the anchored fact must show its "as of turn" chip');
    expect(find.textContaining('Argile Vivante'), findsWidgets,
        reason: 'the linked database article must render as a chip');
  });

  // Real destructive interaction, on a COPY of the fixture so the shared e2e.db
  // stays byte-stable: delete a memory through the confirm dialog and prove the
  // row leaves the list (repo.delete + provider invalidation actually wired).
  testWidgets('deleting a memory removes it from the list', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1200, 2600));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final tmp =
        '${Directory.systemTemp.path}/aurelm_memdel_${DateTime.now().microsecondsSinceEpoch}.db';
    File(_fixtureDb).copySync(tmp);
    SharedPreferences.setMockInitialValues({'aurelm_db_path': tmp});
    final prefs = await SharedPreferences.getInstance();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPrefsProvider.overrideWithValue(prefs),
          autoStartBotProvider.overrideWith((ref) async {}),
          setupCompleteProvider.overrideWith((ref) async => true),
        ],
        child: const AurelmApp(),
      ),
    );
    await _pumpFor(tester);

    await _tapNav(tester, Icons.settings_outlined);
    final entry = find.text('Mémoire de l\'agent');
    await tester.ensureVisible(entry.first);
    await _pumpFor(tester, frames: 4);
    await tester.tap(entry.first);
    await _pumpFor(tester, frames: 16);

    // Two memories → two delete buttons.
    expect(find.byIcon(Icons.delete_outline), findsNWidgets(2));
    await tester.tap(find.byIcon(Icons.delete_outline).first);
    await _pumpFor(tester, frames: 6);
    expect(find.text('Supprimer cette mémoire ?'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, 'Supprimer'));
    await _pumpFor(tester, frames: 16);

    // One memory removed → one delete button remains.
    expect(find.byIcon(Icons.delete_outline), findsOneWidget,
        reason: 'the deleted memory must leave the list after invalidation');
    // Best-effort cleanup — Drift still holds the copy open on Windows (file
    // lock), so a failed delete here is not a test failure; OS temp cleanup handles it.
    try {
      File(tmp).deleteSync();
    } catch (_) {}
  });
}
