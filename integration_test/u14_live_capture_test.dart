// U14 live emulator rehearsal: drives the real app against the Firebase
// emulators (seeded by tools/seed_parent_dashboard_live.js), signs in as the
// linked parent, asserts the state seeded via U14_STATE, and captures a
// text-accurate screenshot through flutter drive.
//
// Run per state (after seeding):
//   flutter drive --driver=test_driver/u14_live_capture.dart \
//     --target=integration_test/u14_live_capture_test.dart \
//     --dart-define=USE_FIREBASE_EMULATORS=true \
//     --dart-define=U14_STATE=full -d emulator-5554
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:logic_oasis/main.dart' as app;
import 'package:logic_oasis/shared/services/firebase_emulator_config.dart';

const parentEmail = 'parent-live@example.test';
const parentPassword = 'parent-dashboard-test-password';
const state = String.fromEnvironment('U14_STATE', defaultValue: 'full');

Future<void> pumpUntilFound(
  WidgetTester tester,
  Finder finder, {
  Duration timeout = const Duration(seconds: 90),
}) async {
  final deadline = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(deadline)) {
    // Real delay lets the app's timers/animations progress in live mode;
    // tester.pump(duration) alone does not advance real time.
    await Future<void>.delayed(const Duration(milliseconds: 400));
    await tester.pump();
    if (finder.evaluate().isNotEmpty) return;
  }
  throw StateError('Timed out waiting for: $finder');
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('U14 live capture: $state', (tester) async {
    debugPrint(
      'U14 diagnostics: enabled=${FirebaseEmulatorConfig.enabled} '
      'host=${FirebaseEmulatorConfig.resolveHost()} state=$state',
    );
    app.main();

    await tester.pump(const Duration(seconds: 5));
    final texts = find
        .byType(Text)
        .evaluate()
        .map((e) => (e.widget as Text).data)
        .whereType<String>()
        .toList();
    debugPrint('U14 texts after 5s: $texts');

    // Opening animation auto-advances; wait for the login page button.
    await pumpUntilFound(tester, find.text('Parent Dashboard'));
    await tester.tap(find.text('Parent Dashboard'));
    await pumpUntilFound(tester, find.text('Private parent access'));
    await tester.pump(const Duration(seconds: 1));

    final fields = find.byType(TextFormField);
    await tester.enterText(fields.at(0), parentEmail);
    await tester.enterText(fields.at(1), parentPassword);
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('Secure parent sign in'));

    final ready = state == 'revoked'
        ? find.textContaining('No active linked learner')
        : find.textContaining('Safe learning updates for Aiman');
    await pumpUntilFound(tester, ready);
    // Let all three cards finish painting before the capture.
    await tester.pump(const Duration(seconds: 3));

    switch (state) {
      case 'full':
        expect(find.textContaining('A steady week with a clear focus'), findsWidgets);
        expect(find.textContaining('Learning snapshot'), findsWidgets);
        expect(find.textContaining('3 practices completed this week'), findsWidgets);
        expect(find.textContaining('Compared with'), findsWidgets);
        expect(find.textContaining('1 question asked'), findsWidgets);
        expect(find.textContaining('2 replies'), findsWidgets);
        break;
      case 'partial':
        expect(find.textContaining('Learning snapshot'), findsWidgets);
        expect(find.textContaining('3 practices completed this week'), findsWidgets);
        expect(find.textContaining('Compared with'), findsNothing);
        expect(find.textContaining('No practice completed yet this week'), findsNothing);
        break;
      case 'zero':
        expect(
          find.textContaining('No practice completed yet this week'),
          findsWidgets,
        );
        expect(
          find.textContaining('No Mutual Aid moments yet this week'),
          findsWidgets,
        );
        expect(
          find.textContaining('More recent learning evidence is needed'),
          findsWidgets,
        );
        break;
      case 'insufficient':
        expect(
          find.textContaining('More recent learning evidence is needed'),
          findsWidgets,
        );
        expect(
          find.textContaining('Practice effort is unavailable this week'),
          findsWidgets,
        );
        expect(
          find.textContaining('Participation summary is unavailable this week'),
          findsWidgets,
        );
        break;
      case 'card-missing':
        expect(find.textContaining('Learning snapshot'), findsWidgets);
        expect(find.textContaining('3 practices completed this week'), findsWidgets);
        expect(
          find.textContaining('Participation summary is unavailable this week'),
          findsWidgets,
        );
        break;
      case 'revoked':
        expect(find.textContaining('No active linked learner'), findsWidgets);
        break;
    }

    // Android requires converting the Flutter surface to an image first.
    await binding.convertFlutterSurfaceToImage();
    await tester.pump();
    await binding.takeScreenshot('live-$state');
  });
}
