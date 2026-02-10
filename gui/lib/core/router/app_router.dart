import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../screens/dashboard/dashboard_screen.dart';
import '../../screens/civilization/civ_detail_screen.dart';
import '../../screens/entities/entity_browser_screen.dart';
import '../../screens/entities/entity_detail_screen.dart';
import '../../screens/timeline/timeline_screen.dart';
import '../../screens/graph/graph_screen.dart';
import '../../screens/settings/settings_screen.dart';
import '../navigation/app_shell.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/',
    routes: [
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(
            path: '/',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: DashboardScreen(),
            ),
          ),
          GoRoute(
            path: '/civs/:id',
            pageBuilder: (context, state) {
              final id = int.parse(state.pathParameters['id']!);
              return NoTransitionPage(child: CivDetailScreen(civId: id));
            },
          ),
          GoRoute(
            path: '/entities',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: EntityBrowserScreen(),
            ),
          ),
          GoRoute(
            path: '/entities/:id',
            pageBuilder: (context, state) {
              final id = int.parse(state.pathParameters['id']!);
              return NoTransitionPage(child: EntityDetailScreen(entityId: id));
            },
          ),
          GoRoute(
            path: '/timeline',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: TimelineScreen(),
            ),
          ),
          GoRoute(
            path: '/graph',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: GraphScreen(),
            ),
          ),
          GoRoute(
            path: '/settings',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: SettingsScreen(),
            ),
          ),
        ],
      ),
    ],
  );
});
