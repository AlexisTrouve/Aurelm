import 'dart:convert';
import 'package:http/http.dart' as http;

import '../core/constants/app_constants.dart';

class SyncService {
  final int port;
  late final String _baseUrl;

  SyncService({this.port = AppConstants.botDefaultPort}) {
    _baseUrl = 'http://127.0.0.1:$port';
  }

  Future<bool> healthCheck() async {
    try {
      final response = await http
          .get(Uri.parse('$_baseUrl${AppConstants.botHealthEndpoint}'))
          .timeout(const Duration(seconds: 3));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['ok'] == true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> getStatus() async {
    final response = await http
        .get(Uri.parse('$_baseUrl${AppConstants.botStatusEndpoint}'))
        .timeout(const Duration(seconds: 5));
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception('Status request failed: ${response.statusCode}');
  }

  Future<Map<String, dynamic>> triggerSync() async {
    final response = await http
        .post(Uri.parse('$_baseUrl${AppConstants.botSyncEndpoint}'))
        .timeout(const Duration(minutes: 10));
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode == 200) {
      return data;
    }
    throw Exception(data['error'] ?? 'Sync failed: ${response.statusCode}');
  }
}
