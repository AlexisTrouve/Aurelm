import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

/// Why a redeem attempt failed, in the only granularity the server actually
/// exposes.
///
/// WHY so coarse: the redeem endpoint is unauthenticated, so it answers unknown /
/// expired / already-consumed codes with one identical 400 (anti-enumeration).
/// Modelling finer states would be inventing information we don't have — the UI
/// shows a single message and tells the user to ask for a new code.
enum EnrollmentFailure {
  /// Unknown, expired, or already consumed — indistinguishable by design.
  invalidCode,

  /// 429 — more than 10 attempts a minute from this IP.
  rateLimited,

  /// Could not reach the proxy at all (offline, DNS, TLS).
  network,

  /// Reachable but answered something unexpected (5xx, malformed body).
  server,
}

/// Result of a redeem: either the key, or why it failed.
sealed class EnrollmentResult {}

class EnrollmentSuccess extends EnrollmentResult {
  final String apiKey;
  final String keyId;
  EnrollmentSuccess({required this.apiKey, required this.keyId});
}

class EnrollmentError extends EnrollmentResult {
  final EnrollmentFailure failure;
  EnrollmentError(this.failure);
}

/// Exchanges a one-time activation code for an etheryale API key.
///
/// WHAT: the client half of the enrollment flow — `POST /api/enrollment/redeem`,
/// the only unauthenticated endpoint in the management API (the code *is* the
/// bearer). Verified live against prod before this was written.
///
/// WHY it lives in Flutter and not the bot: the app owns the secret. It redeems
/// once during the wizard, seals the key with [KeyStore], then injects it into the
/// bot subprocess environment — the Python side never touches secure storage.
///
/// COMMENT: this is the ONE moment the app requires the network. Nothing here is
/// ever called again on later launches (no re-validation — see the design doc).
class EnrollmentService {
  final String baseUrl;
  final http.Client _client;

  EnrollmentService({
    this.baseUrl = 'https://ai.etheryale.com',
    http.Client? client,
  }) : _client = client ?? http.Client();

  /// Trade [code] for an API key.
  ///
  /// The code is sent as typed apart from trimming: the server normalises case
  /// and whitespace itself. We deliberately do NOT length- or regex-validate it —
  /// the format is ~41 chars today and a client-side rule would break the day the
  /// server changes it, rejecting a perfectly good code offline.
  Future<EnrollmentResult> redeem(String code) async {
    final trimmed = code.trim();
    if (trimmed.isEmpty) return EnrollmentError(EnrollmentFailure.invalidCode);

    try {
      final resp = await _client
          .post(
            Uri.parse('$baseUrl/api/enrollment/redeem'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'code': trimmed}),
          )
          .timeout(const Duration(seconds: 30));

      switch (resp.statusCode) {
        case 200:
          final json = jsonDecode(resp.body) as Map<String, dynamic>;
          final apiKey = json['apiKey'] as String?;
          if (apiKey == null || apiKey.isEmpty) {
            // 200 without a key should not happen; treat as server fault rather
            // than sealing an empty string and "succeeding" into a broken state.
            return EnrollmentError(EnrollmentFailure.server);
          }
          return EnrollmentSuccess(
            apiKey: apiKey,
            keyId: json['key_id'] as String? ?? '',
          );
        case 400:
          return EnrollmentError(EnrollmentFailure.invalidCode);
        case 429:
          return EnrollmentError(EnrollmentFailure.rateLimited);
        default:
          return EnrollmentError(EnrollmentFailure.server);
      }
    } on TimeoutException {
      return EnrollmentError(EnrollmentFailure.network);
    } catch (_) {
      // SocketException, TLS failure, malformed JSON — all "we didn't get a
      // usable answer", which the user can only act on by retrying.
      return EnrollmentError(EnrollmentFailure.network);
    }
  }

  /// User-facing French message for a failure.
  ///
  /// Single message for [EnrollmentFailure.invalidCode] on purpose: the server
  /// cannot tell us whether the code was wrong, expired, or already used, and a
  /// code is single-use — so the only useful instruction is "ask for a new one".
  static String messageFor(EnrollmentFailure failure) => switch (failure) {
        EnrollmentFailure.invalidCode =>
          'Code invalide ou déjà utilisé — demande un nouveau code.',
        EnrollmentFailure.rateLimited =>
          'Trop de tentatives. Réessaie dans une minute.',
        EnrollmentFailure.network =>
          'Impossible de joindre le serveur. Vérifie ta connexion et réessaie.',
        EnrollmentFailure.server =>
          'Le serveur a répondu de façon inattendue. Réessaie dans un moment.',
      };
}
