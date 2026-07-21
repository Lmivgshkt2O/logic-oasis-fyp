import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/settings/parent_access_page.dart';
import 'package:logic_oasis/shared/repositories/auth_repository.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

void main() {
  testWidgets(
    'parent access starts with a Firebase sign-in gate, not registration',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: ParentAccessPage(
            state: AppState(persistQuizResults: false),
            onReturnToStudentLogin: () {},
            authGateway: _ParentAuthGateway(),
          ),
        ),
      );

      expect(find.text('Parent sign in'), findsOneWidget);
      expect(find.text('Secure parent sign in'), findsOneWidget);
      expect(find.text('Parent email'), findsOneWidget);
      expect(
        find.textContaining('student sends an invitation'),
        findsOneWidget,
      );
      expect(find.text('Forgot password? Reset it securely'), findsOneWidget);
      expect(find.textContaining('Register'), findsNothing);
    },
  );

  testWidgets('parent session is signed out after dashboard exit', (
    tester,
  ) async {
    final gateway = _ParentAuthGateway();
    var returnedToStudentLogin = false;

    await tester.pumpWidget(
      MaterialApp(
        home: ParentAccessPage(
          state: AppState(persistQuizResults: false),
          onReturnToStudentLogin: () => returnedToStudentLogin = true,
          authGateway: gateway,
          dashboardBuilder: (_) => Builder(
            builder: (context) => FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Leave parent dashboard'),
            ),
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextFormField).at(0), 'parent@test.com');
    await tester.enterText(find.byType(TextFormField).at(1), 'secret');
    await tester.tap(find.text('Secure parent sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Leave parent dashboard'), findsOneWidget);

    await tester.tap(find.text('Leave parent dashboard'));
    await tester.pumpAndSettle();

    expect(gateway.signInCalls, 1);
    expect(gateway.signOutCalls, 1);
    expect(returnedToStudentLogin, isTrue);
  });

  testWidgets('failed parent sign-out remains locked until a retry succeeds', (
    tester,
  ) async {
    final gateway = _ParentAuthGateway()..failSignOut = true;
    var returnedToStudentLogin = false;

    await tester.pumpWidget(
      MaterialApp(
        home: ParentAccessPage(
          state: AppState(persistQuizResults: false),
          onReturnToStudentLogin: () => returnedToStudentLogin = true,
          authGateway: gateway,
          dashboardBuilder: (_) => Builder(
            builder: (context) => FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Leave parent dashboard'),
            ),
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextFormField).at(0), 'parent@test.com');
    await tester.enterText(find.byType(TextFormField).at(1), 'secret');
    await tester.tap(find.text('Secure parent sign in'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Leave parent dashboard'));
    await tester.pumpAndSettle();

    expect(find.text('Retry secure sign out'), findsOneWidget);
    expect(returnedToStudentLogin, isFalse);

    gateway.failSignOut = false;
    await tester.tap(find.text('Retry secure sign out'));
    await tester.pumpAndSettle();
    expect(returnedToStudentLogin, isTrue);
  });
}

class _ParentAuthGateway implements ParentAuthenticationGateway {
  int signInCalls = 0;
  int signOutCalls = 0;
  bool failSignOut = false;

  @override
  Future<void> signIn({required String email, required String password}) async {
    signInCalls += 1;
  }

  @override
  Future<void> signOut() async {
    signOutCalls += 1;
    if (failSignOut) {
      throw const AuthFailure('Temporary sign-out failure.');
    }
  }

  @override
  Future<void> sendPasswordReset({required String email}) async {}
}
