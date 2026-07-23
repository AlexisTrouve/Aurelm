import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

/// One published release, as described by the distribution manifest.
class UpdateInfo {
  final String version;
  final String url;
  final String sha256;
  final String notes;
  final String publishedAt;

  const UpdateInfo({
    required this.version,
    required this.url,
    required this.sha256,
    this.notes = '',
    this.publishedAt = '',
  });

  static UpdateInfo? fromJson(Map<String, dynamic> j) {
    final v = (j['version'] ?? '').toString();
    final u = (j['url'] ?? '').toString();
    final h = (j['sha256'] ?? '').toString();
    // A release without a hash is unusable: we refuse to execute an unverified
    // binary, so treat a hashless manifest as "no update" rather than half-trust it.
    if (v.isEmpty || u.isEmpty || h.isEmpty) return null;
    return UpdateInfo(
      version: v,
      url: u,
      sha256: h.toLowerCase(),
      notes: (j['notes'] ?? '').toString(),
      publishedAt: (j['published'] ?? '').toString(),
    );
  }
}

/// Checks the distribution server for a newer Aurelm and installs it.
///
/// WHY a server manifest rather than a store/auto-updater: the app is a per-user
/// Inno install on Arthur's machine; re-running a newer installer upgrades in place
/// (stable AppId), the DB is outside the install dir and the activation lives in the
/// Windows credential store — so an upgrade preserves everything.
///
/// Two rules this class exists to enforce:
///  1. **Never block the app.** The check is best-effort with a short timeout and
///     swallows every failure — the update host is on a VPS that does flake, and an
///     unreachable update server is not an application error.
///  2. **Never execute an unverified binary.** The downloaded installer is checked
///     against the manifest's sha256 before it is launched. HTTPS protects transport;
///     the hash also catches truncation and is a second gate before running code.
class UpdateService {
  static const String manifestUrl =
      'https://dist.etheryale.com/aurelm/latest.json';

  final http.Client _client;
  final String _manifestUrl;

  /// Where the installer is downloaded. Injectable because `getTemporaryDirectory`
  /// is a plugin call with no platform behind it under `flutter test` — the download
  /// path has to stay testable without spinning up a device.
  final Future<Directory> Function() _tempDir;

  UpdateService({
    http.Client? client,
    String? manifestUrl,
    Future<Directory> Function()? tempDirProvider,
  })  : _client = client ?? http.Client(),
        _manifestUrl = manifestUrl ?? UpdateService.manifestUrl,
        _tempDir = tempDirProvider ?? getTemporaryDirectory;

  /// Compare two dotted versions numerically. Returns <0, 0, >0.
  ///
  /// String comparison is wrong here ("0.10.0" < "0.9.0" lexically), which would
  /// silently stop offering updates after the 9th minor.
  static int compareVersions(String a, String b) {
    List<int> parts(String v) => v
        .split(RegExp(r'[-+]'))
        .first
        .split('.')
        .map((p) => int.tryParse(p.trim()) ?? 0)
        .toList();
    final pa = parts(a), pb = parts(b);
    for (var i = 0; i < (pa.length > pb.length ? pa.length : pb.length); i++) {
      final x = i < pa.length ? pa[i] : 0;
      final y = i < pb.length ? pb[i] : 0;
      if (x != y) return x - y;
    }
    return 0;
  }

  /// Returns the release to offer, or null when up to date / unreachable / malformed.
  Future<UpdateInfo?> check({
    required String currentVersion,
    Duration timeout = const Duration(seconds: 5),
  }) async {
    try {
      final res = await _client.get(Uri.parse(_manifestUrl)).timeout(timeout);
      if (res.statusCode != 200) return null;
      final decoded = jsonDecode(utf8.decode(res.bodyBytes));
      if (decoded is! Map<String, dynamic>) return null;
      final info = UpdateInfo.fromJson(decoded);
      if (info == null) return null;
      return compareVersions(info.version, currentVersion) > 0 ? info : null;
    } catch (_) {
      return null; // offline, DNS down, VPS hiccup, bad JSON — never surface as an error
    }
  }

  /// Download the installer to a temp file and verify its sha256.
  ///
  /// Throws [UpdateIntegrityError] on mismatch, after deleting the bad file — a
  /// failed hash means we must not keep, and never run, that binary.
  Future<File> download(UpdateInfo info, {void Function(int, int?)? onProgress}) async {
    final dir = await _tempDir();
    final file = File('${dir.path}${Platform.pathSeparator}${info.url.split('/').last}');

    final req = http.Request('GET', Uri.parse(info.url));
    final res = await _client.send(req);
    if (res.statusCode != 200) {
      throw UpdateIntegrityError('téléchargement échoué (HTTP ${res.statusCode})');
    }

    final sink = file.openWrite();
    var received = 0;
    try {
      await for (final chunk in res.stream) {
        received += chunk.length;
        sink.add(chunk);
        onProgress?.call(received, res.contentLength);
      }
    } finally {
      await sink.close();
    }

    final digest = sha256.convert(await file.readAsBytes()).toString();
    if (digest != info.sha256) {
      try {
        await file.delete();
      } catch (_) {}
      throw UpdateIntegrityError(
          'empreinte sha256 invalide — binaire rejeté (attendu ${info.sha256.substring(0, 12)}…, obtenu ${digest.substring(0, 12)}…)');
    }
    return file;
  }

  /// Launch the verified installer and quit, so Windows releases the files the
  /// running app (and its bot subprocess) hold inside the install directory.
  ///
  /// [onBeforeExit] is where the caller stops the bot subprocess; without that the
  /// embedded python.exe keeps a handle on {app}\python and the upgrade half-applies.
  Future<void> installAndExit(File installer, {Future<void> Function()? onBeforeExit}) async {
    if (onBeforeExit != null) {
      try {
        await onBeforeExit();
      } catch (_) {}
    }
    await Process.start(installer.path, const [], mode: ProcessStartMode.detached);
    await Future<void>.delayed(const Duration(milliseconds: 300));
    exit(0);
  }
}

class UpdateIntegrityError implements Exception {
  final String message;
  UpdateIntegrityError(this.message);
  @override
  String toString() => message;
}
