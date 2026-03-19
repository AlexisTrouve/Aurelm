import 'package:drift/drift.dart';

/// Drift table for map_maps — hierarchical map layers (world → region → local).
@DataClassName('MapRow')
class MapMaps extends Table {
  @override
  String get tableName => 'map_maps';

  IntColumn get id => integer().autoIncrement()();
  TextColumn get name => text()();
  TextColumn get imagePath => text().named('image_path').nullable()();

  /// 'hex' (pointy-top) or 'square'
  TextColumn get gridType =>
      text().named('grid_type').withDefault(const Constant('hex'))();
  IntColumn get gridCols =>
      integer().named('grid_cols').withDefault(const Constant(20))();
  IntColumn get gridRows =>
      integer().named('grid_rows').withDefault(const Constant(15))();

  /// Self-reference: this map drills into a cell of parent_map_id.
  /// Plain IntColumn — Drift doesn't support typed self-referencing FKs.
  IntColumn get parentMapId => integer().named('parent_map_id').nullable()();
  IntColumn get parentCellQ => integer().named('parent_cell_q').nullable()();
  IntColumn get parentCellR => integer().named('parent_cell_r').nullable()();

  TextColumn get createdAt => text().named('created_at')();
}

/// Drift table for map_cells — one row per (map, q, r) coordinate.
@DataClassName('MapCellRow')
class MapCells extends Table {
  @override
  String get tableName => 'map_cells';

  // Composite primary key — no autoIncrement
  IntColumn get mapId => integer().named('map_id')();
  IntColumn get q => integer()();
  IntColumn get r => integer()();

  /// plain|forest|mountain|river|coast|sea|desert|swamp|ruins
  TextColumn get terrainType =>
      text().named('terrain_type').withDefault(const Constant('plain'))();
  IntColumn get controllingCivId =>
      integer().named('controlling_civ_id').nullable()();
  IntColumn get entityId => integer().named('entity_id').nullable()();
  TextColumn get label => text().nullable()();

  /// FK to a child map — clicking this cell drills into that map.
  IntColumn get childMapId => integer().named('child_map_id').nullable()();

  /// JSON blob for arbitrary extra data.
  TextColumn get metadata => text().nullable()();

  @override
  Set<Column> get primaryKey => {mapId, q, r};
}

/// Drift table for map_cell_events — historical events on a cell.
@DataClassName('MapCellEventRow')
class MapCellEvents extends Table {
  @override
  String get tableName => 'map_cell_events';

  IntColumn get id => integer().autoIncrement()();
  IntColumn get mapId => integer().named('map_id')();
  IntColumn get q => integer()();
  IntColumn get r => integer()();

  /// Optional FK to a game turn.
  IntColumn get turnId => integer().named('turn_id').nullable()();
  TextColumn get description => text()();

  /// settlement|battle|discovery|diplomatic|note|migration|disaster
  TextColumn get eventType =>
      text().named('event_type').withDefault(const Constant('note'))();
  TextColumn get createdAt => text().named('created_at')();
}
