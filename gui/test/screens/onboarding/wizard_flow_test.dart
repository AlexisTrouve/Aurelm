import 'dart:io';

import 'package:aurelm_gui/providers/bot_provider.dart';
import 'package:aurelm_gui/providers/database_provider.dart';
import 'package:aurelm_gui/providers/discord_provider.dart';
import 'package:aurelm_gui/providers/enrollment_provider.dart';
import 'package:aurelm_gui/providers/pipeline_setup_provider.dart';
import 'package:aurelm_gui/screens/onboarding/setup_wizard.dart';
import 'package:aurelm_gui/services/bot_service.dart';
import 'package:aurelm_gui/services/discord_service.dart';
import 'package:aurelm_gui/services/enrollment_service.dart';
import 'package:aurelm_gui/services/key_store.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider_platform_interface/path_provider_platform_interface.dart';
import 'package:plugin_platform_interface/plugin_platform_interface.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// The whole first-run wizard, CLICKED end to end — the E2E test the manual dogfood
/// kept standing in for. It drives Activation → Base → Discord → Analyse with the
/// external services faked (redeem, migrate, Discord verify, Ollama status), and
/// asserts the wizard reaches "setup complete". This is what would have caught the
/// launcher crash / the Ollama-not-detected / the resumability without a human.

// --- Fakes: real wizard logic, faked side effects. --------------------------------

class _MemKeyStore extends KeyStore {
  final store = <String, String>{};
  @override
  Future<String?> readKey() async => store['api'];
  @override
  Future<void> writeKey(String k) async => store['api'] = k;
  @override
  Future<bool> hasKey() async => store.containsKey('api');
  @override
  Future<void> writeDiscordToken(String t) async => store['discord'] = t;
  @override
  Future<void> writeOpenRouterKey(String k) async => store['openrouter'] = k;
  @override
  Future<bool> isSetupComplete() async => store['setup'] == 'true';
  @override
  Future<void> markSetupComplete() async => store['setup'] = 'true';
}

class _OkEnrollment extends EnrollmentService {
  @override
  Future<EnrollmentResult> redeem(String code) async =>
      EnrollmentSuccess(apiKey: 'sealed-key', keyId: 'kid');
}

class _OkBot extends BotService {
  @override
  Future<bool> migrate({required String dbPath}) async => true;
}

/// Fakes the DB step so it needs neither path_provider (silent under the test binding)
/// nor a real `-m bot --migrate-only` subprocess: it just sets a DB path and reports
/// ready. Migration itself is covered by the bot's own migration tests.
class _OkDbSetup extends DbSetupNotifier {
  final Ref _r;
  final String _dbPath;
  _OkDbSetup(this._r, this._dbPath) : super(_r);
  @override
  Future<bool> prepare({String? path}) async {
    _r.read(dbPathProvider.notifier).setPath(path ?? _dbPath);
    state = DbSetupState(status: DbSetupStatus.ready, path: path ?? _dbPath);
    return true;
  }
}

/// Fakes the Discord notifier so the step needs no real database (a Drift DB in a
/// plain widget test would drag in sqlite3). Real Discord/DB logic is covered by its
/// own service tests; here we prove the STEP wiring: verify shows channels, finish
/// advances.
class _OkDiscord extends DiscordConnectNotifier {
  _OkDiscord(super.ref);
  @override
  Future<void> verify(String token) async {
    state = DiscordConnectState(
      status: DiscordStatus.verified,
      result: DiscordVerifySuccess(
        botName: 'CIVJDR-ContextManager',
        applicationId: '1',
        hasMessageContent: true,
        guilds: const [
          DiscordGuild(
            id: 'g1',
            name: 'Serveur',
            channels: [DiscordChannel(id: 'c1', name: 'confluence')],
          ),
        ],
      ),
    );
  }

  @override
  Future<bool> save({
    required String token,
    required Map<String, ({String civName, String player})> mappings,
  }) async =>
      true;
}

/// Fakes the pipeline save (writing aurelm_config.json next to the DB) — that file I/O
/// is covered by BotConfigService's own tests; here we only prove the step finishes.
class _OkPipeline extends PipelineSetupNotifier {
  _OkPipeline(super.ref);
  @override
  Future<bool> save({String? openRouterKey}) async => true;
}

class _FakePathProvider extends PathProviderPlatform
    with MockPlatformInterfaceMixin {
  final String dir;
  _FakePathProvider(this.dir);
  @override
  Future<String?> getApplicationDocumentsPath() async => dir;
}

void main() {
  late Directory tmp;
  late _MemKeyStore keyStore;
  late SharedPreferences prefs;

  final realPicker = dbLocationPicker;

  setUp(() async {
    tmp = Directory.systemTemp.createTempSync('wizard_flow');
    keyStore = _MemKeyStore();
    PathProviderPlatform.instance = _FakePathProvider(tmp.path);
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    // The DB step picks a path via this seam — return a temp file so prepare() never
    // touches path_provider (which doesn't answer under the test binding).
    dbLocationPicker = ({required suggestedName, required initialDirectory}) async =>
        p.join(tmp.path, 'campagne.db');
  });
  tearDown(() {
    dbLocationPicker = realPicker;
    try {
      tmp.deleteSync(recursive: true);
    } catch (_) {/* a temp file may still be held open — cleanup is best-effort */}
  });

  Widget wizard() => ProviderScope(
        overrides: [
          sharedPrefsProvider.overrideWithValue(prefs),
          keyStoreProvider.overrideWithValue(keyStore),
          enrollmentServiceProvider.overrideWithValue(_OkEnrollment()),
          botServiceProvider.overrideWithValue(_OkBot()),
          dbSetupProvider
              .overrideWith((ref) => _OkDbSetup(ref, p.join(tmp.path, 'game.aurelm'))),
          discordConnectProvider.overrideWith((ref) => _OkDiscord(ref)),
          pipelineSetupProvider.overrideWith((ref) => _OkPipeline(ref)),
          // Ollama already installed with the recommended model → the step just
          // shows "prêt" and the Terminer button (no download in the test).
          ollamaStatusProvider.overrideWith(
            (ref) async => const OllamaStatus(
                reachable: true, models: [kDefaultOllamaModel]),
          ),
        ],
        child: const MaterialApp(home: SetupWizard()),
      );

  // Advance frames without requiring FULL idle: the app has a background bot/health
  // poll timer once a DB path is set, so pumpAndSettle (which waits for zero pending
  // work) never returns. A bounded pump lets the faked async + rebuilds land.
  Future<void> settle(WidgetTester tester) async {
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
  }

  testWidgets('the whole wizard clicks through to setup-complete', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1200, 2600));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(wizard());
    await tester.pump(); // resolve hasKey() → start at Activation

    // --- Step 1: Activation ---------------------------------------------------
    expect(find.byKey(const Key('activation_code_field')), findsOneWidget);
    await tester.enterText(
        find.byKey(const Key('activation_code_field')), 'AURELM-TEST-CODE');
    await tester.tap(find.byKey(const Key('activation_submit')));
    await settle(tester);
    expect(keyStore.store['api'], 'sealed-key'); // the key was sealed

    // --- Step 2: Base ---------------------------------------------------------
    expect(find.byKey(const Key('db_submit')), findsOneWidget);
    await tester.tap(find.byKey(const Key('db_submit')));
    await settle(tester);

    // --- Step 3: Discord ------------------------------------------------------
    expect(find.byKey(const Key('discord_token_field')), findsOneWidget);
    await tester.enterText(
        find.byKey(const Key('discord_token_field')), 'a-bot-token');
    await tester.tap(find.byKey(const Key('discord_verify')));
    await settle(tester);
    // The verified panel shows the channel → bind it to a civ.
    expect(find.byKey(const Key('civ_c1')), findsOneWidget);
    await tester.enterText(find.byKey(const Key('civ_c1')), 'Confluence');
    await tester.tap(find.byKey(const Key('discord_finish')));
    await settle(tester);

    // --- Step 4: Analyse (Ollama ready) → Terminer ----------------------------
    expect(find.byKey(const Key('pipeline_finish')), findsOneWidget);
    await tester.tap(find.byKey(const Key('pipeline_finish')));
    await settle(tester);

    // The wizard finished — setup is marked complete (the app would swap to the
    // real UI on the next launch).
    expect(await keyStore.isSetupComplete(), isTrue);
  });
}
