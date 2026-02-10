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
}
