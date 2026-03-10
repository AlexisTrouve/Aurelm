import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../screens/dashboard/dashboard_screen.dart';
import '../../screens/civilization/civ_detail_screen.dart';
import '../../screens/entities/entity_browser_screen.dart';
import '../../screens/entities/entity_detail_screen.dart';
import '../../screens/entities/disabled_entities_screen.dart';
import '../../screens/timeline/timeline_screen.dart';
import '../../screens/timeline/turn_detail_screen.dart';
import '../../screens/graph/graph_screen.dart';
import '../../screens/settings/settings_screen.dart';
import '../../screens/subjects/subject_browser_screen.dart';
import '../../screens/subjects/subject_detail_screen.dart';
import '../navigation/app_shell.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/entities', // DEV: start on entities for faster testing
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
            path: '/entities/disabled',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: DisabledEntitiesScreen(),
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
            path: '/turns/:id',
            pageBuilder: (context, state) {
              final id = int.parse(state.pathParameters['id']!);
              // Optional highlight param: passed via context.push extra {'highlight': 'EntityName'}
              final extra = state.extra as Map<String, dynamic>?;
              final highlight = extra?['highlight'] as String?;
              return NoTransitionPage(
                child: TurnDetailScreen(turnId: id, highlightText: highlight),
              );
            },
          ),
          GoRoute(
            path: '/graph',
            pageBuilder: (context, state) {
              final extra = state.extra as Map<String, dynamic>?;
              final entityId = extra?['entityId'] as int?;
              return NoTransitionPage(child: GraphScreen(initialEntityId: entityId));
            },
          ),
          GoRoute(
            path: '/subjects',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: SubjectBrowserScreen(),
            ),
          ),
          GoRoute(
            path: '/subjects/:id',
            pageBuilder: (context, state) {
              final id = int.parse(state.pathParameters['id']!);
              return NoTransitionPage(child: SubjectDetailScreen(subjectId: id));
            },
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
