import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/chat_provider.dart';

class AppShell extends ConsumerWidget {
  final Widget child;

  const AppShell({super.key, required this.child});

  static const _destinations = [
    NavigationRailDestination(
      icon: Icon(Icons.dashboard_outlined),
      selectedIcon: Icon(Icons.dashboard),
      label: Text('Dashboard'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.category_outlined),
      selectedIcon: Icon(Icons.category),
      label: Text('Entities'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.timeline_outlined),
      selectedIcon: Icon(Icons.timeline),
      label: Text('Timeline'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.hub_outlined),
      selectedIcon: Icon(Icons.hub),
      label: Text('Relations'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.scatter_plot_outlined),
      selectedIcon: Icon(Icons.scatter_plot),
      label: Text('Graph'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.task_alt_outlined),
      selectedIcon: Icon(Icons.task_alt),
      label: Text('Sujets'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.map_outlined),
      selectedIcon: Icon(Icons.map),
      label: Text('Cartes'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.chat_outlined),
      selectedIcon: Icon(Icons.chat),
      label: Text('Sessions'),
    ),
    NavigationRailDestination(
      icon: Icon(Icons.settings_outlined),
      selectedIcon: Icon(Icons.settings),
      label: Text('Settings'),
    ),
  ];

  static const _routes = [
    '/',
    '/entities',
    '/timeline',
    '/civs/relations',
    '/graph',
    '/subjects',
    '/map',
    '/chat/sessions',
    '/settings',
  ];

  int _selectedIndex(BuildContext context) {
    final location = GoRouterState.of(context).uri.toString();
    if (location.startsWith('/entities')) return 1;
    if (location.startsWith('/timeline')) return 2;
    if (location.startsWith('/civs/relations')) return 3;
    if (location.startsWith('/graph')) return 4;
    if (location.startsWith('/subjects')) return 5;
    if (location.startsWith('/map')) return 6;
    if (location.startsWith('/chat')) return 7;
    if (location.startsWith('/settings')) return 8;
    return 0; // dashboard + /civs/:id
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedIndex = _selectedIndex(context);
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: selectedIndex,
            onDestinationSelected: (index) {
              // Chat tab (index 7): go directly to active session if one is open
              if (index == 7) {
                final hasSession = ref.read(chatProvider).sessionId != null;
                context.go(hasSession ? '/chat' : '/chat/sessions');
              } else {
                context.go(_routes[index]);
              }
            },
            destinations: _destinations,
            extended: false,
            backgroundColor: colorScheme.surface,
            leading: Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Icon(
                Icons.auto_stories,
                size: 32,
                color: colorScheme.primary,
              ),
            ),
          ),
          const VerticalDivider(thickness: 1, width: 1),
          Expanded(child: child),
        ],
      ),
    );
  }
}
