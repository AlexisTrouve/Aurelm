class AppConstants {
  static const String appName = 'Aurelm';
  static const String appVersion = '0.1.0';

  static const List<String> entityTypes = [
    'person',
    'place',
    'technology',
    'institution',
    'resource',
    'creature',
    'event',
    'civilization',
    'caste',
    'belief',
  ];

  // Relation types — from entity_profiler.py + pipeline DB (entity_relations)
  static const List<String> relationTypes = [
    'located_in',
    'member_of',
    'part_of',
    'allied_with',
    'enemy_of',
    'controls',
    'trades_with',
    'produces',
    'worships',
    'created_by',
  ];

  static const List<String> segmentTypes = [
    'narrative',
    'choice',
    'consequence',
    'ooc',
    'description',
  ];

  static const List<String> turnTypes = [
    'standard',
    'event',
    'first_contact',
    'crisis',
  ];

  static const int graphDefaultEntityLimit = 50;
  static const int recentTurnsLimit = 5;
  static const int mentionPreviewLimit = 20;
  static const int topEntitiesLimit = 10;

  static const String envDbPathKey = 'AURELM_DB_PATH';

  // Bot HTTP API
  static const int botDefaultPort = 8473;
  static const String botHealthEndpoint = '/health';
  static const String botStatusEndpoint = '/status';
  static const String botSyncEndpoint = '/sync';
  static const String botChatEndpoint = '/chat';
}
