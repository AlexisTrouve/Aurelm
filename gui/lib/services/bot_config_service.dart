// Reads/writes aurelm_config.json located next to the DB file, and probes Ollama.

import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../models/bot_config.dart';

class BotConfigService {
  /// Load config from disk. Returns defaults if file missing or corrupt.
  static Future<BotConfig> load(String dbPath) async {
    final file = _configFile(dbPath);
    if (!file.existsSync()) return const BotConfig();
    try {
      final raw = await file.readAsString();
      return BotConfig.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return const BotConfig();
    }
  }

  /// Persist config to disk. Merges with existing file to preserve
  /// unknown fields (e.g. extraction_version used by the pipeline).
  static Future<void> save(String dbPath, BotConfig config) async {
    final file = _configFile(dbPath);
    Map<String, dynamic> existing = {};
    if (file.existsSync()) {
      try {
        existing = jsonDecode(await file.readAsString()) as Map<String, dynamic>;
      } catch (_) {}
    }
    // Merge: our known fields overwrite, unknown fields preserved
    final merged = {...existing, ...config.toJson()};
    const encoder = JsonEncoder.withIndent('  ');
    await file.writeAsString(encoder.convert(merged));
  }

  /// Query the bot's /discord/channels endpoint.
  /// Returns a list of {id, name, guild_id, guild_name} or null on error.
  static Future<List<Map<String, dynamic>>?> fetchDiscordChannels(
      {int port = 8473}) async {
    try {
      final resp = await http
          .get(Uri.parse('http://127.0.0.1:$port/discord/channels'))
          .timeout(const Duration(seconds: 5));
      if (resp.statusCode != 200) return null;
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      return List<Map<String, dynamic>>.from(body['channels'] as List);
    } catch (_) {
      return null;
    }
  }

  /// Query locally running Ollama for installed models.
  static Future<List<String>> fetchOllamaModels() async {
    return (await probeOllama()).models;
  }

  /// Probe Ollama, distinguishing "not running" from "running with no models".
  ///
  /// WHY separate from the model list: a fresh Ollama install has ZERO models by
  /// definition, so inferring reachability from a non-empty list would report a
  /// working Ollama as "not detected" — and hide the in-app download UI in exactly
  /// the state (fresh install) it exists for. Reachability is whether /api/tags
  /// actually answered 200; the model list is a separate fact.
  static Future<({bool reachable, List<String> models})> probeOllama() async {
    try {
      final resp = await http
          .get(Uri.parse('http://localhost:11434/api/tags'))
          .timeout(const Duration(seconds: 3));
      if (resp.statusCode != 200) return (reachable: false, models: <String>[]);
      final body = jsonDecode(resp.body) as Map<String, dynamic>;
      final models = (body['models'] as List?) ?? [];
      final names = models
          .map((m) => (m as Map<String, dynamic>)['name'] as String? ?? '')
          .where((n) => n.isNotEmpty)
          .toList()
        ..sort();
      // 200 answered → reachable, even if the list is empty.
      return (reachable: true, models: names);
    } catch (_) {
      return (reachable: false, models: <String>[]);
    }
  }

  static File _configFile(String dbPath) {
    final dir = File(dbPath).parent;
    return File('${dir.path}/aurelm_config.json');
  }
}
