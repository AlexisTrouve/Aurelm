import 'package:flutter/material.dart';

class AppColors {
  static const Color seed = Color(0xFFB8860B); // Dark goldenrod

  // Entity type colors (full pipeline vocab)
  static const Map<String, Color> entityTypeColors = {
    'person': Color(0xFF42A5F5),
    'place': Color(0xFF66BB6A),
    'technology': Color(0xFFFFCA28),
    'institution': Color(0xFFAB47BC),
    'resource': Color(0xFF8D6E63),
    'creature': Color(0xFFEF5350),
    'event': Color(0xFF26C6DA),
    'civilization': Color(0xFFFF7043),
    'caste': Color(0xFF7E57C2),
    'belief': Color(0xFF29B6F6),
  };

  // Semantic entity tag colors — matches ENTITY_TAG_VOCAB in entity_profiler.py
  static Color entityTagColor(String tag) => switch (tag) {
        'militaire' => Colors.red,
        'religieux' => Colors.indigo,
        'politique' => Colors.purple,
        'economique' => Colors.green,
        'culturel' => Colors.amber,
        'diplomatique' => Colors.pink,
        'technologique' => Colors.blueGrey,
        'mythologique' => Colors.deepPurple,
        'actif' => Colors.teal,
        'disparu' => Colors.grey,
        'emergent' => Colors.cyan,
        'legendaire' => Colors.orange,
        _ => Colors.blueGrey,
      };

  // Segment type colors
  static const Map<String, Color> segmentTypeColors = {
    'narrative': Color(0xFF42A5F5),
    'choice': Color(0xFFFFCA28),
    'consequence': Color(0xFF66BB6A),
    'ooc': Color(0xFF9E9E9E),
    'description': Color(0xFFAB47BC),
  };

  // Turn type colors
  static const Map<String, Color> turnTypeColors = {
    'standard': Color(0xFF42A5F5),
    'event': Color(0xFFFFCA28),
    'first_contact': Color(0xFFAB47BC),
    'crisis': Color(0xFFEF5350),
  };

  // Status
  static const Color success = Color(0xFF66BB6A);
  static const Color warning = Color(0xFFFFCA28);
  static const Color error = Color(0xFFEF5350);

  static Color entityColor(String type) =>
      entityTypeColors[type] ?? const Color(0xFF9E9E9E);
}
