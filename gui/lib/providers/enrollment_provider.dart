import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../services/enrollment_service.dart';
import '../services/key_store.dart';
import 'bot_provider.dart';
import 'database_provider.dart';

/// OS-sealed store for the API key + the first-run flag.
final keyStoreProvider = Provider<KeyStore>((ref) => KeyStore());

/// Redeems an activation code. Used once, during the wizard.
final enrollmentServiceProvider =
    Provider<EnrollmentService>((ref) => EnrollmentService());

/// Whether the first-run wizard already completed.
///
/// WHY this gates the whole app: a launch must be usable offline, so the check is
/// purely LOCAL (a secure-storage read) — we never ask the proxy whether the key is
/// still valid. A revoked key surfaces later, when a chat request actually fails,
/// not as a startup gate (see docs/enrollment-client-design.md, "Behavioral rules").
final setupCompleteProvider = FutureProvider<bool>((ref) async {
  return ref.watch(keyStoreProvider).isSetupComplete();
});

/// The sealed API key, read once per launch to hand to the bot subprocess.
///
/// Returns null before activation — callers must not start the bot without it, or
/// the agent comes up disabled and /chat answers 503.
final apiKeyProvider = FutureProvider<String?>((ref) async {
  return ref.watch(keyStoreProvider).readKey();
});

/// What the activation step is currently doing.
enum ActivationStatus { idle, submitting, success }

class ActivationState {
  final ActivationStatus status;

  /// User-facing failure message, or null when there's nothing to show.
  final String? error;

  const ActivationState({this.status = ActivationStatus.idle, this.error});

  bool get isSubmitting => status == ActivationStatus.submitting;
}

/// Drives the activation step: code in, sealed key out.
///
/// COMMENT: on success the key is written BEFORE anything else happens. The code is
/// consumed by the server at that point and can never be redeemed again, so losing
/// the key between the response and the write would strand the user on a dead code.
class ActivationNotifier extends StateNotifier<ActivationState> {
  final EnrollmentService _enrollment;
  final KeyStore _keyStore;

  ActivationNotifier(this._enrollment, this._keyStore)
      : super(const ActivationState());

  /// Redeem [code]. Returns true when the key is sealed and the step can advance.
  Future<bool> activate(String code) async {
    if (state.isSubmitting) return false; // ignore double-taps
    state = const ActivationState(status: ActivationStatus.submitting);

    final result = await _enrollment.redeem(code);

    switch (result) {
      case EnrollmentSuccess(:final apiKey):
        // Persist first — the code is already spent. A DPAPI write can throw
        // (storage locked/unavailable); if it does, don't leave the spinner hung
        // with the key lost — surface a recoverable error. We do NOT echo the key
        // into the message (leak-safety is the whole point of this store); the code
        // is spent, so the recovery is a new code.
        try {
          await _keyStore.writeKey(apiKey);
        } catch (e) {
          state = ActivationState(
            status: ActivationStatus.idle,
            error: 'La clé n\'a pas pu être sauvegardée ($e). Demande un nouveau code.',
          );
          return false;
        }
        state = const ActivationState(status: ActivationStatus.success);
        return true;
      case EnrollmentError(:final failure):
        state = ActivationState(
          status: ActivationStatus.idle,
          error: EnrollmentService.messageFor(failure),
        );
        return false;
    }
  }

  /// Clear the error when the user edits the field, so a stale message doesn't
  /// sit under a code they've already corrected.
  void clearError() {
    if (state.error != null) state = const ActivationState();
  }
}

final activationProvider =
    StateNotifierProvider<ActivationNotifier, ActivationState>((ref) {
  return ActivationNotifier(
    ref.watch(enrollmentServiceProvider),
    ref.watch(keyStoreProvider),
  );
});

// --------------------------------------------------------------------------- //
// Wizard step 2 — database
// --------------------------------------------------------------------------- //

/// The default database location: `<Documents>\Aurelm\aurelm.db`.
///
/// WHY a default rather than a folder picker: Arthur's premise is zero maintenance;
/// choosing a path is a decision he has no basis to make. The wizard still exposes
/// a "change location" affordance for the rare user who wants one.
Future<String> defaultDbPath() async {
  final docs = await getApplicationDocumentsDirectory();
  return p.join(docs.path, 'Aurelm', 'aurelm.db');
}

enum DbSetupStatus { idle, preparing, ready }

class DbSetupState {
  final DbSetupStatus status;
  final String? path;
  final String? error;
  const DbSetupState({this.status = DbSetupStatus.idle, this.path, this.error});
  bool get isPreparing => status == DbSetupStatus.preparing;
}

/// Creates the database at a chosen path and applies the full schema.
///
/// COMMENT: the schema is built by the bot's migrations (`--migrate-only`), not by
/// Flutter — Drift only creates its own few tables. We migrate here, synchronously
/// awaiting a clean exit, BEFORE calling setPath, so the moment the app mounts and
/// Drift opens the file every core table already exists. Doing it after setPath
/// would race the app's first queries against an empty database.
class DbSetupNotifier extends StateNotifier<DbSetupState> {
  final Ref _ref;
  DbSetupNotifier(this._ref) : super(const DbSetupState());

  /// Prepare the DB at [path] (or the default). Returns true when it's schema'd
  /// and now the active database.
  Future<bool> prepare({String? path}) async {
    if (state.isPreparing) return false;
    state = const DbSetupState(status: DbSetupStatus.preparing);

    final dbPath = path ?? await defaultDbPath();
    try {
      await Directory(p.dirname(dbPath)).create(recursive: true);
    } catch (e) {
      state = DbSetupState(
        status: DbSetupStatus.idle,
        error: 'Impossible de créer le dossier de la base : $e',
      );
      return false;
    }

    final ok = await _ref.read(botServiceProvider).migrate(dbPath: dbPath);
    if (!ok) {
      state = const DbSetupState(
        status: DbSetupStatus.idle,
        error: 'La préparation de la base a échoué. Réessaie.',
      );
      return false;
    }

    // Only now point the app at it — the schema is complete.
    _ref.read(dbPathProvider.notifier).setPath(dbPath);
    state = DbSetupState(status: DbSetupStatus.ready, path: dbPath);
    return true;
  }
}

final dbSetupProvider =
    StateNotifierProvider<DbSetupNotifier, DbSetupState>((ref) {
  return DbSetupNotifier(ref);
});
