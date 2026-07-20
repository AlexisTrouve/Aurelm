import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme/app_theme.dart';
import 'core/router/app_router.dart';
import 'providers/bot_provider.dart';
import 'providers/enrollment_provider.dart';
import 'providers/settings_provider.dart';
import 'screens/onboarding/setup_wizard.dart';

/// Root widget — gates the whole app behind first-run setup.
///
/// WHY the gate lives here and not in the router: until activation has produced an
/// API key there is no bot, so every routed screen would sit on a dead backend. It
/// also keeps [autoStartBotProvider] from running key-less, which would spawn a bot
/// whose agent is disabled (/chat answering 503) and leave the user confused.
///
/// COMMENT: the check is a local secure-storage read — never a network call — so a
/// normal launch is offline-tolerant and instant (see the "Behavioral rules" section
/// of docs/enrollment-client-design.md).
class AurelmApp extends ConsumerWidget {
  const AurelmApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final setup = ref.watch(setupCompleteProvider);
    final themeMode = ref.watch(themeModeProvider);

    return MaterialApp(
      title: 'Aurelm',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: themeMode,
      home: setup.when(
        // A secure-storage read, so this is a frame or two — not a real wait.
        loading: () => const _Splash(),
        // Storage unreadable: treat as "not set up" rather than blocking forever.
        // Re-running the wizard is recoverable; a permanently blank window isn't.
        error: (_, __) => const SetupWizard(),
        data: (complete) => complete ? const _MainApp() : const SetupWizard(),
      ),
    );
  }
}

/// The real application, mounted only once setup is complete.
class _MainApp extends ConsumerWidget {
  const _MainApp();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Only now is it safe to spawn the bot: a key exists for it to use.
    ref.watch(autoStartBotProvider);
    final router = ref.watch(routerProvider);

    return Router.withConfig(config: router);
  }
}

class _Splash extends StatelessWidget {
  const _Splash();

  @override
  Widget build(BuildContext context) =>
      const Scaffold(body: Center(child: CircularProgressIndicator()));
}
