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
///
/// The two branches build their OWN MaterialApp on purpose: the configured app needs
/// `MaterialApp.router` for GoRouter, while the wizard is a plain `home:`. Wrapping a
/// Router inside a MaterialApp's home instead was clever and wrong — it broke
/// navigation and turned the boot E2E red.
class AurelmApp extends ConsumerWidget {
  const AurelmApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final setup = ref.watch(setupCompleteProvider);

    return setup.when(
      // A secure-storage read, so this is a frame or two — not a real wait.
      loading: () => const _PlainApp(child: _Splash()),
      // Storage unreadable: treat as "not set up" rather than blocking forever.
      // Re-running the wizard is recoverable; a permanently blank window isn't.
      error: (_, __) => const _PlainApp(child: SetupWizard()),
      data: (complete) =>
          complete ? const _MainApp() : const _PlainApp(child: SetupWizard()),
    );
  }
}

/// The real application: router, navigation shell, and a running bot.
class _MainApp extends ConsumerWidget {
  const _MainApp();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Only now is it safe to spawn the bot: a key exists for it to use.
    ref.watch(autoStartBotProvider);
    final router = ref.watch(routerProvider);
    final themeMode = ref.watch(themeModeProvider);

    return MaterialApp.router(
      title: 'Aurelm',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: themeMode,
      routerConfig: router,
    );
  }
}

/// Themed MaterialApp for the pre-setup screens, which have no routes yet.
class _PlainApp extends ConsumerWidget {
  final Widget child;
  const _PlainApp({required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'Aurelm',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ref.watch(themeModeProvider),
      home: child,
    );
  }
}

class _Splash extends StatelessWidget {
  const _Splash();

  @override
  Widget build(BuildContext context) =>
      const Scaffold(body: Center(child: CircularProgressIndicator()));
}
