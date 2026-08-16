import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/app/theme.dart';
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
    final pager = _ShellPager()
      ..gate = Completer<void>()
      ..error = FirebaseException(
        plugin: 'cloud_firestore',
        code: 'permission-denied',
      );
    final state = AppState()..changeTab(2);
    await _pumpShell(
      tester,
      state,
      forumPageBuilder: (_) => QaForumPage(
        state: state,
        questionPager: pager.call,
        latestQuestionsStream: Stream.value(const <ForumQuestion>[]),
        blockedStudentIdsStream: Stream.value(const <String>{}),
      ),
    );

    expect(find.byType(BottomNavBar), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text('Q&A Forum'), findsNWidgets(2));
    expect(find.text('Ask a question'), findsOneWidget);

    pager.gate!.complete();
    pager.gate = null;
    await tester.pump();
    await tester.pump();

    expect(
      find.textContaining('Forum access is unavailable for this account'),
      findsOneWidget,
    );
  });

  testWidgets('navigation labels stay visible at small width and enlarged text', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1.0;
    tester.platformDispatcher.textScaleFactorTestValue = 1.3;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      tester.platformDispatcher.clearTextScaleFactorTestValue();
    });

    final state = AppState();
    await _pumpShell(tester, state);

    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Forge'), findsOneWidget);
    expect(find.text('Q&A Forum'), findsOneWidget);
    expect(find.text('Settings'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('selected navigation uses forest plus a non-colour cue', (
    tester,
  ) async {
    final semanticsHandle = tester.ensureSemantics();

    final state = AppState();
    await _pumpShell(tester, state);

    final selectedHome = tester.widget<Text>(find.text('Home'));
    expect(selectedHome.style?.color, LogicOasisDesign.forestAction);

    final homeNode = tester.getSemantics(find.text('Home'));
    expect(homeNode.label, 'Home');
    expect(homeNode.flagsCollection.hasSelectedState, isTrue);

    await tester.tap(find.text('Forge'));
    await tester.pump();
    final selectedForge = tester.widget<Text>(find.text('Forge'));
    expect(selectedForge.style?.color, LogicOasisDesign.forestAction);
    semanticsHandle.dispose();
  });
}

class _ShellPager {
  Completer<void>? gate;
  Object? error;

  Future<ForumQuestionPage> call({
    required int limit,
    String? cursor,
  }) async {
    final pendingGate = gate;
    if (pendingGate != null) await pendingGate.future;
    final failure = error;
    if (failure != null) throw failure;
    return const ForumQuestionPage(
      questions: [],
      nextCursor: null,
      hasMore: false,
    );
  }
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
        theme: LogicOasisTheme.light(),
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
