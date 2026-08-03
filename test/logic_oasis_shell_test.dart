import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/app/logic_oasis_shell.dart';
import 'package:logic_oasis/features/collaboration/qa_forum/qa_forum_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/forum_question.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/state/app_state_scope.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      'logic_oasis_navigation_schema_version': 2,
    });
  });

  testWidgets('shell exposes Home, Forge, Forum, Settings in order', (
    tester,
  ) async {
    final state = AppState();
    await _pumpShell(tester, state);

    final navigation = tester.widget<BottomNavBar>(find.byType(BottomNavBar));
    expect(
      navigation.items.map((item) => item.label),
      orderedEquals(['Home', 'Forge', 'Q&A Forum', 'Settings']),
    );

    for (final selection in <(String, int)>[
      ('Home', 0),
      ('Forge', 1),
      ('Q&A Forum', 2),
      ('Settings', 3),
    ]) {
      await tester.tap(find.text(selection.$1));
      await tester.pump();
      expect(state.selectedTab, selection.$2);
    }
  });

  testWidgets('Home settings control selects index 3 without a forum route', (
    tester,
  ) async {
    final state = AppState();
    await _pumpShell(tester, state);

    expect(find.text('Ask and help in the Q&A Forum'), findsNothing);
    await tester.tap(find.byType(SoftIconButton).last);
    await tester.pump();

    expect(state.selectedTab, 3);
    expect(find.byKey(const Key('forum-page-in-shell')), findsNothing);
  });

  testWidgets('Forum loading and denied states render inside the shell', (
    tester,
  ) async {
    final questions = StreamController<List<ForumQuestion>>();
    addTearDown(questions.close);
    final state = AppState()..changeTab(2);
    await _pumpShell(
      tester,
      state,
      forumPageBuilder: (_) => QaForumPage(
        state: state,
        questionsStream: questions.stream,
        blockedStudentIdsStream: Stream.value(const <String>{}),
      ),
    );

    expect(find.byType(BottomNavBar), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text('Q&A Forum'), findsNWidgets(2));
    expect(find.text('Ask a question'), findsOneWidget);

    questions.addError(
      FirebaseException(plugin: 'cloud_firestore', code: 'permission-denied'),
    );
    await tester.pump();

    expect(
      find.textContaining('Forum access is unavailable for this account'),
      findsOneWidget,
    );
  });
}

Future<void> _pumpShell(
  WidgetTester tester,
  AppState state, {
  Widget Function(AppState state)? forumPageBuilder,
}) async {
  await tester.pumpWidget(
    AppStateScope(
      state: state,
      child: MaterialApp(
        supportedLocales: AppLocalizations.supportedLocales,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
        ],
        home: LogicOasisShell(
          onLogout: () {},
          forumPageBuilder:
              forumPageBuilder ??
              (_) => Scaffold(
                key: const Key('forum-page-in-shell'),
                appBar: AppBar(title: const Text('Forum page')),
                body: const Center(child: Text('Forum content')),
              ),
        ),
      ),
    ),
  );
  await tester.pump();
}
