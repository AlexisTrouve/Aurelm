# Aurelm GUI — Flutter Desktop

## Overview

Desktop dashboard for the Game Master. Browse civilizations, entities, timeline, and an interactive entity relationship graph.

## Architecture

- **State management**: Riverpod 2.6 (StreamProvider for reactive DB, StateNotifier for filters)
- **Database**: Drift ORM (read-only, pipeline owns writes)
- **Navigation**: GoRouter + NavigationRail (desktop-first)
- **Graph**: graphview (force-directed, Fruchterman-Reingold)
- **Charts**: fl_chart (bar chart for entity breakdown)
- **Platform**: Windows Desktop (primary)

## Screens

| Screen | Route | Description |
|--------|-------|-------------|
| Dashboard | `/` | Civ grid, pipeline status, quick search |
| Civ Detail | `/civs/:id` | Stats, entity chart, top entities, recent turns |
| Entity Browser | `/entities` | Search, filter by type/civ, sorted by mentions |
| Entity Detail | `/entities/:id` | Aliases, relations, mention timeline |
| Timeline | `/timeline` | Chronological turns, per-civ/global filter |
| Graph | `/graph` | Force-directed entity graph, per-civ filter |
| Settings | `/settings` | DB path, theme toggle, about |

## Setup (Local)

1. Install Flutter SDK 3.24+
2. `flutter create --platforms=windows .`
3. `flutter pub get`
4. `dart run build_runner build --delete-conflicting-outputs`
5. `flutter run -d windows`

## Setup (CI)

GitHub Actions builds the Windows EXE automatically on push to `gui/**`. See `.github/workflows/build-gui-windows.yml`.

## Testing

```bash
flutter test
```

6 tests: widget tests (EntityTypeBadge, StatCard, EmptyState) + model tests (FilterState, GraphData, AppConstants).
