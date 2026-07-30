import 'package:aurelm_gui/providers/enrollment_provider.dart';
import 'package:aurelm_gui/screens/onboarding/setup_wizard.dart';
import 'package:aurelm_gui/services/key_store.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// A KeyStore double: reports whether a key is already sealed, without touching
/// DPAPI. `const FlutterSecureStorage()` in the super ctor is inert (no platform
/// call at construction) and is never used because we override the readers.
class _FakeKeyStore extends KeyStore {
  final bool _has;
  _FakeKeyStore(this._has);

  @override
  Future<bool> hasKey() async => _has;

  @override
  Future<String?> readKey() async => _has ? 'sealed-key' : null;
}

Widget _wizard(bool hasKey) => ProviderScope(
      overrides: [
        keyStoreProvider.overrideWithValue(_FakeKeyStore(hasKey)),
      ],
      child: const MaterialApp(home: SetupWizard()),
    );

void main() {
  group('SetupWizard resumability — the single-use activation code is not re-asked', () {
    testWidgets('a sealed key skips the activation step (resumes at the DB step)',
        (tester) async {
      await tester.pumpWidget(_wizard(true));
      await tester.pump(); // let initState resolve hasKey() and rebuild past the spinner

      // The interrupted-setup lock-out: the burned code must NOT be asked again.
      expect(find.byKey(const Key('activation_code_field')), findsNothing);
      // It resumes on the next (idempotent) step instead.
      expect(find.byKey(const Key('db_submit')), findsOneWidget);
    });

    testWidgets('no key → the activation step is shown as before (fresh install)',
        (tester) async {
      await tester.pumpWidget(_wizard(false));
      await tester.pump();

      expect(find.byKey(const Key('activation_code_field')), findsOneWidget);
      expect(find.byKey(const Key('db_submit')), findsNothing);
    });
  });
}
