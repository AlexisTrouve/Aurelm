import 'package:flutter/material.dart';

class AppColors {
  static const Color seed = Color(0xFFB8860B); // Dark goldenrod

  // Entity type colors
  static const Map<String, Color> entityTypeColors = {
    'person': Color(0xFF42A5F5),
    'place': Color(0xFF66BB6A),
    'technology': Color(0xFFFFCA28),
    'institution': Color(0xFFAB47BC),
    'resource': Color(0xFF8D6E63),
    'creature': Color(0xFFEF5350),
    'event': Color(0xFF26C6DA),
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
