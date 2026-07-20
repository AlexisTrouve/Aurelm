import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/enrollment_service.dart';
import '../services/key_store.dart';

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
        // Persist first — the code is already spent.
        await _keyStore.writeKey(apiKey);
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
