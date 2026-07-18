import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/forum_participation_summary.dart';
import 'package:logic_oasis/shared/models/linked_child_context.dart';
import 'package:logic_oasis/shared/models/parent_dashboard_snapshot.dart';
import 'package:logic_oasis/shared/services/parent_link_context_service.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class _LinkedChildrenGateway implements ParentLinkedChildrenGateway {
  const _LinkedChildrenGateway(this.children);

  final List<LinkedChildContext> children;

  @override
  Future<List<LinkedChildContext>> loadLinkedChildren() async => children;
}

void main() {
  testWidgets(
    'parent dashboard renders only the selected linked child snapshot',
    (tester) async {
      const child = LinkedChildContext(
        studentId: 'student_safe',
        displayName: 'Aiman',
        yearLevel: 4,
      );
      final snapshot = ParentDashboardSnapshot(
        attempts: const [],
        masteryRecordCount: 1,
        aiDiagnoses: const [
          AiDiagnosis(
            attemptId: 'attempt_safe',
            studentId: 'student_safe',
            sourceAttemptSequence: 1,
            analysisState: 'completed',
            displayCode: 'analysis_complete',
            masteryProbability: .6,
            evidenceLevel: 'preliminary',
            observationCount: 1,
          ),
        ],
        forumParticipationSummary: const ForumParticipationSummary(
          studentId: 'student_safe',
          questionsPostedCount: 2,
          answersSubmittedCount: 1,
          acceptedAnswersCount: 0,
          helpfulReceivedCount: 3,
        ),
      );

      await tester.pumpWidget(
        MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: ParentDashboardPage(
            state: AppState(persistQuizResults: false),
            linkedChildrenGateway: const _LinkedChildrenGateway([child]),
            dashboardLoader: (_) async => snapshot,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Safe learning updates for Aiman.'), findsOneWidget);
      expect(find.text('Practice focus ready'), findsOneWidget);
      expect(
        find.textContaining('2 questions, 1 answers, and 3 helpful marks.'),
        findsOneWidget,
      );
      expect(find.textContaining('No quiz activity yet'), findsNothing);
    },
  );

  testWidgets('unlinked account cannot fall back to local learner data', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ParentDashboardPage(
          state: AppState(persistQuizResults: false),
          linkedChildrenGateway: const _LinkedChildrenGateway([]),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('No active linked learner is available for this account.'),
      findsOneWidget,
    );
    expect(
      find.textContaining('No safe analysis is available yet.'),
      findsOneWidget,
    );
  });

  testWidgets('a stale child-load failure cannot replace a newer selection', (
    tester,
  ) async {
    const childA = LinkedChildContext(
      studentId: 'student_a',
      displayName: 'Aiman',
      yearLevel: 4,
    );
    const childB = LinkedChildContext(
      studentId: 'student_b',
      displayName: 'Bela',
      yearLevel: 5,
    );
    final firstLoad = Completer<ParentDashboardSnapshot>();
    final belaSnapshot = ParentDashboardSnapshot(
      attempts: const [],
      masteryRecordCount: 2,
      aiDiagnoses: const [],
    );

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ParentDashboardPage(
          state: AppState(persistQuizResults: false),
          linkedChildrenGateway: const _LinkedChildrenGateway([childA, childB]),
          dashboardLoader: (child) =>
              child.studentId == childA.studentId ? firstLoad.future : Future.value(belaSnapshot),
        ),
      ),
    );
    await tester.pump();

    await tester.tap(find.byType(DropdownButtonFormField<LinkedChildContext>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Bela (Year 5)').last);
    await tester.pumpAndSettle();
    firstLoad.completeError(StateError('stale A request failed'));
    await tester.pump();

    expect(find.text('Safe learning updates for Bela.'), findsOneWidget);
    expect(find.text('Safe learner updates are temporarily unavailable.'), findsNothing);
  });
}
