import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/app_constants.dart';
import '../services/update_service.dart';
import 'bot_provider.dart';

/// Everything the two update surfaces (the shell banner and the Settings card)
/// need to render. One controller, two views — the download/verify/install flow
/// exists once.
class UpdateState {
  final UpdateInfo? available;
  final bool busy;
  final double? progress;
  final String? status;
  final String? error;
  final bool dismissed;

  const UpdateState({
    this.available,
    this.busy = false,
    this.progress,
    this.status,
    this.error,
    this.dismissed = false,
  });

  /// Show the banner only when there is something to install and the user has not
  /// waved it away for this session.
  bool get showBanner => available != null && !dismissed;

  UpdateState copyWith({
    UpdateInfo? available,
    bool? busy,
    double? progress,
    String? status,
    String? error,
    bool? dismissed,
    bool clearProgress = false,
    bool clearError = false,
    bool clearStatus = false,
  }) =>
      UpdateState(
        available: available ?? this.available,
        busy: busy ?? this.busy,
        progress: clearProgress ? null : (progress ?? this.progress),
        status: clearStatus ? null : (status ?? this.status),
        error: clearError ? null : (error ?? this.error),
        dismissed: dismissed ?? this.dismissed,
      );
}

class UpdateController extends StateNotifier<UpdateState> {
  final Ref _ref;
  final UpdateService _service;

  UpdateController(this._ref, this._service) : super(const UpdateState()) {
    // Auto-check once, at creation (the shell watches this provider, so that is
    // app startup). Deliberately fire-and-forget: `check` swallows every failure,
    // so a slow or dead update host can never delay or break the launch.
    checkSilently();
  }

  /// Startup check — reports nothing when there is no update or the host is down.
  Future<void> checkSilently() async {
    final info = await _service.check(currentVersion: AppConstants.appVersion);
    if (!mounted) return;
    if (info != null) state = state.copyWith(available: info);
  }

  /// Manual check from Settings — reports the outcome either way.
  Future<void> check() async {
    state = state.copyWith(busy: true, clearError: true, status: 'Vérification…');
    final info = await _service.check(currentVersion: AppConstants.appVersion);
    if (!mounted) return;
    state = UpdateState(
      available: info,
      busy: false,
      status: info == null
          ? 'Aucune mise à jour (ou serveur injoignable).'
          : 'Version ${info.version} disponible.',
    );
  }

  void dismiss() => state = state.copyWith(dismissed: true);

  /// Download, verify, then hand over to the installer and quit.
  Future<void> install() async {
    final info = state.available;
    if (info == null || state.busy) return;
    state = state.copyWith(
        busy: true, progress: 0, status: 'Téléchargement…', clearError: true);
    try {
      final file = await _service.download(info, onProgress: (received, total) {
        if (!mounted || total == null || total <= 0) return;
        state = state.copyWith(progress: received / total);
      });
      if (!mounted) return;
      state = state.copyWith(status: 'Installation — l\'application va se fermer…');
      // Stopping the bot releases the embedded python's handles inside the install
      // directory; without it the installer cannot replace those files.
      await _service.installAndExit(
        file,
        onBeforeExit: () async => _ref.read(botServiceProvider).stop(),
        launcher: _ref.read(installerLauncherProvider),
        quit: _ref.read(appQuitProvider),
      );
    } catch (e) {
      if (!mounted) return;
      state = state.copyWith(
        busy: false,
        clearProgress: true,
        clearStatus: true,
        error: e is UpdateIntegrityError ? e.message : 'Échec : $e',
      );
    }
  }
}

final updateServiceProvider = Provider<UpdateService>((ref) => UpdateService());

/// Injection seams for the FINAL, irreversible step. In production both are null and
/// the service does the real thing (Process.start + exit). An E2E that clicks
/// "Installer" overrides them, otherwise the test harness would launch a real
/// installer and then kill itself with exit(0) — so the one action that matters most
/// could never be covered.
final installerLauncherProvider =
    Provider<Future<void> Function(String path)?>((ref) => null);
final appQuitProvider = Provider<void Function()?>((ref) => null);

final updateControllerProvider =
    StateNotifierProvider<UpdateController, UpdateState>(
        (ref) => UpdateController(ref, ref.watch(updateServiceProvider)));
