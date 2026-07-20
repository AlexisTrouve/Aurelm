import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Durable, OS-sealed storage for the etheryale API key + the first-run flag.
///
/// WHAT: wraps `flutter_secure_storage` behind the two questions the app actually
/// asks — "is this instance set up?" and "what key do I launch the bot with?".
///
/// WHY not a plain file: on Windows the backing store is DPAPI, which seals the
/// ciphertext to the user's Windows account. The app therefore carries **no**
/// decryption key of its own — copying the stored blob to another machine or
/// account yields nothing. A hand-rolled encrypted file would have had to embed a
/// key in the binary, which is obfuscation, not encryption (see
/// `docs/enrollment-client-design.md`).
///
/// COMMENT: the key is written exactly once, at the end of the activation step,
/// and read on every launch to spawn the bot. `setupComplete` is deliberately a
/// separate entry rather than being inferred from "a key exists": the wizard also
/// collects Discord and pipeline settings, so it is only finished when *it* says
/// so — inferring it from the key would skip the remaining steps.
class KeyStore {
  /// Injectable so tests can pass an in-memory double instead of touching DPAPI.
  final FlutterSecureStorage _storage;

  KeyStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const _keyApiKey = 'etheryale_api_key';
  static const _keyDiscordToken = 'discord_bot_token';
  static const _keyOpenRouterKey = 'openrouter_api_key';
  static const _keySetupComplete = 'setup_complete';

  /// The etheryale API key, or null when this instance was never activated.
  Future<String?> readKey() async => _storage.read(key: _keyApiKey);

  /// Seal the key. Called once, immediately after a successful redeem — the code
  /// is consumed by then, so losing the key here means needing a brand new code.
  Future<void> writeKey(String key) =>
      _storage.write(key: _keyApiKey, value: key);

  Future<bool> hasKey() async => (await readKey()) != null;

  /// The Discord bot token, or null when Discord was never configured. Sealed the
  /// same way as the API key (DPAPI) — it is just as much a secret and is handed to
  /// the bot the same way, through the subprocess environment.
  Future<String?> readDiscordToken() async => _storage.read(key: _keyDiscordToken);

  Future<void> writeDiscordToken(String token) =>
      _storage.write(key: _keyDiscordToken, value: token);

  /// The OpenRouter API key, or null when the pipeline uses Ollama (which needs
  /// none). Sealed and injected like every other secret — the pipeline provider
  /// reads it from OPENROUTER_API_KEY in the bot's environment.
  Future<String?> readOpenRouterKey() async => _storage.read(key: _keyOpenRouterKey);

  Future<void> writeOpenRouterKey(String key) =>
      _storage.write(key: _keyOpenRouterKey, value: key);

  /// True once the first-run wizard finished. Read on every launch to decide
  /// whether to show the wizard — a purely LOCAL check, never a network call, so
  /// a normal launch works offline (see "Behavioral rules" in the design doc).
  Future<bool> isSetupComplete() async {
    final v = await _storage.read(key: _keySetupComplete);
    return v == 'true';
  }

  /// Marks the wizard done. Only the wizard's final step calls this.
  Future<void> markSetupComplete() =>
      _storage.write(key: _keySetupComplete, value: 'true');

  /// Wipe every entry — used by "re-activate" (key lost, revoked, or rotated),
  /// which sends the user back through the wizard with a fresh code.
  Future<void> clear() async {
    await _storage.delete(key: _keyApiKey);
    await _storage.delete(key: _keyDiscordToken);
    await _storage.delete(key: _keyOpenRouterKey);
    await _storage.delete(key: _keySetupComplete);
  }
}
