import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/settings/settings_page.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

void main() {
  testWidgets('settings logout asks for confirmation before logging out', (
    tester,
  ) async {
    var loggedOut = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SettingsPage(
            state: AppState(),
            onLogout: () {
              loggedOut = true;
            },
          ),
        ),
      ),
    );

    await tester.scrollUntilVisible(
      find.text('Log out'),
      240,
      scrollable: find.byType(Scrollable),
    );
    await tester.ensureVisible(find.text('Log out'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Log out'));
    await tester.pumpAndSettle();

    expect(find.text('Confirm to log out?'), findsOneWidget);
    expect(loggedOut, isFalse);

    await tester.tap(find.widgetWithText(FilledButton, 'Log out'));
    await tester.pumpAndSettle();

    expect(loggedOut, isTrue);
  });
}
