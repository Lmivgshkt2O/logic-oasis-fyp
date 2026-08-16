import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_core_platform_interface/test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/onboarding/login_page.dart';
import 'package:logic_oasis/features/onboarding/plot_intro_page.dart';
import 'package:logic_oasis/features/onboarding/register_page.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setupFirebaseCoreMocks();

  setUpAll(Firebase.initializeApp);

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('plot intro can auto-finish without user click', (tester) async {
    var finished = false;

    await tester.pumpWidget(
      MaterialApp(
        home: PlotIntroPage(
          onFinished: () {
            finished = true;
          },
        ),
      ),
    );

    expect(find.text('Skip'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 17000));
    await tester.pumpAndSettle();

    expect(finished, isTrue);
  });

  testWidgets('register page shows student account fields', (tester) async {
    await tester.pumpWidget(
      MaterialApp(theme: LogicOasisTheme.light(), home: const RegisterPage()),
    );

    expect(find.text('New student account'), findsOneWidget);
    expect(find.text('Student name'), findsOneWidget);
    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.text('Remember this student profile'), findsOneWidget);
  });

  testWidgets('login page exposes student, provider, and parent entry controls', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: LogicOasisTheme.light(),
        home: LoginPage(onLogin: (_) {}, onParentAccess: () {}),
      ),
    );
    await tester.pump();

    expect(find.text('Log in'), findsOneWidget);
    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.text('Remember this student profile'), findsOneWidget);
    expect(find.byTooltip('Show password'), findsOneWidget);
    expect(find.text('Log In'), findsOneWidget);
    expect(find.text('Create new student profile'), findsOneWidget);
    expect(find.text('Google'), findsOneWidget);
    expect(find.text('Facebook'), findsOneWidget);

    await tester.dragUntilVisible(
      find.text('Parent Dashboard'),
      find.byType(ListView),
      const Offset(0, -160),
    );
    expect(
      find.textContaining('Parents can sign in separately'),
      findsOneWidget,
    );
    expect(find.text('Parent Dashboard'), findsOneWidget);
  });

  testWidgets('login account creation opens the registration form', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(theme: LogicOasisTheme.light(), home: LoginPage(onLogin: (_) {})),
    );
    await tester.pump();

    await tester.tap(find.text('Create new student profile'));
    await tester.pumpAndSettle();

    expect(find.text('New student account'), findsOneWidget);
    expect(find.text('Year level'), findsOneWidget);
  });

  testWidgets('login password visibility toggle reveals then hides the password', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(theme: LogicOasisTheme.light(), home: LoginPage(onLogin: (_) {})),
    );
    await tester.pump();

    TextField passwordField() {
      return tester.widget<TextField>(
        find.descendant(
          of: find
              .ancestor(
                of: find.text('Password'),
                matching: find.byType(TextFormField),
              )
              .first,
          matching: find.byType(TextField),
        ),
      );
    }

    expect(passwordField().obscureText, isTrue);

    await tester.tap(find.byTooltip('Show password'));
    await tester.pump();
    expect(passwordField().obscureText, isFalse);

    await tester.tap(find.byTooltip('Hide password'));
    await tester.pump();
    expect(passwordField().obscureText, isTrue);
  });

  testWidgets('register page exposes year selection, safety guidance, and back navigation', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(theme: LogicOasisTheme.light(), home: const RegisterPage()),
    );

    expect(find.text('Year level'), findsOneWidget);
    expect(find.text('Year 4'), findsOneWidget);
    expect(find.text('Year 5'), findsOneWidget);
    expect(find.text('Year 6'), findsOneWidget);

    final segmented = tester.widget<SegmentedButton<int>>(
      find.byType(SegmentedButton<int>),
    );
    expect(segmented.selected, {4});

    await tester.dragUntilVisible(
      find.text('Back to Login'),
      find.byType(ListView),
      const Offset(0, -160),
    );
    expect(find.text('Back to Login'), findsOneWidget);

    await tester.dragUntilVisible(
      find.textContaining('For safety, the password is handled by Firebase Auth'),
      find.byType(ListView),
      const Offset(0, -160),
    );
    expect(
      find.textContaining('For safety, the password is handled by Firebase Auth'),
      findsOneWidget,
    );
  });
}
