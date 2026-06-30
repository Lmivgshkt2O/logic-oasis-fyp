import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/onboarding/plot_intro_page.dart';
import 'package:logic_oasis/features/onboarding/register_page.dart';

void main() {
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
    await tester.pumpWidget(const MaterialApp(home: RegisterPage()));

    expect(find.text('New student account'), findsOneWidget);
    expect(find.text('Student name'), findsOneWidget);
    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.text('Remember this student profile'), findsOneWidget);
  });
}
