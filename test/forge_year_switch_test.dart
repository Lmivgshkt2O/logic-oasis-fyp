import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/formula_forge/formula_forge_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('year selector switches the forge topic list per year', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    final state = AppState();

    await tester.pumpWidget(
      MaterialApp(theme: LogicOasisTheme.light(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: FormulaForgePage(state: state),
      ),
    );

    expect(state.yearLevel, 4);
    expect(find.text('Numbers and Operations'), findsOneWidget);
    expect(find.text('Whole Numbers and Operations'), findsNothing);

    await tester.tap(find.text('Year 5'));
    await tester.pumpAndSettle();

    expect(state.yearLevel, 5);
    expect(find.text('Whole Numbers and Operations'), findsOneWidget);
    expect(find.text('Numbers and Operations'), findsNothing);
    expect(
      state.topics.where((topic) => topic.yearLevel == 5),
      hasLength(8),
    );

    await tester.tap(find.text('Year 6'));
    await tester.pumpAndSettle();

    expect(state.yearLevel, 6);
    expect(find.text('Whole Numbers and Operations'), findsOneWidget);
    expect(
      state.topics.where((topic) => topic.yearLevel == 6),
      hasLength(8),
    );
  });

  testWidgets('Forge stays scrollable at small width with enlarged text', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1.0;
    tester.platformDispatcher.textScaleFactorTestValue = 1.3;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      tester.platformDispatcher.clearTextScaleFactorTestValue();
    });

    final state = AppState();
    await tester.pumpWidget(
      MaterialApp(theme: LogicOasisTheme.light(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: FormulaForgePage(state: state),
      ),
    );

    expect(find.text('Year 4'), findsOneWidget);
    expect(find.text('Numbers and Operations'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
