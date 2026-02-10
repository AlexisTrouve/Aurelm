import 'package:drift/drift.dart';

@DataClassName('CivRow')
class CivCivilizations extends Table {
  @override
  String get tableName => 'civ_civilizations';

  IntColumn get id => integer().autoIncrement()();
  TextColumn get name => text().unique()();
  TextColumn get playerName => text().named('player_name').nullable()();
  TextColumn get discordChannelId =>
      text().named('discord_channel_id').nullable()();
  TextColumn get createdAt => text().named('created_at')();
  TextColumn get updatedAt => text().named('updated_at')();
}
