import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/forum_participation_summary.dart';
import 'package:logic_oasis/shared/models/linked_child_context.dart';
import 'package:logic_oasis/shared/models/parent_dashboard_snapshot.dart';
import 'package:logic_oasis/shared/models/parent_practice_summary.dart';
import 'package:logic_oasis/shared/models/trusted_subtopic_progress.dart';
import 'package:logic_oasis/shared/services/parent_link_context_service.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class _LinkedChildrenGateway implements ParentLinkedChildrenGateway {
  const _LinkedChildrenGateway(this.children);

  final List<LinkedChildContext> children;

  @override
  Future<List<LinkedChildContext>> loadLinkedChildren() async => children;
}

TrustedSubtopicProgress masteryRecord(String subtopicId) {
  return TrustedSubtopicProgress(
    studentId: 'student_safe',
    topicId: 'whole_numbers_y4',
    subtopicId: subtopicId,
    yearLevel: 4,
    completed: true,
    masteryLevel: 'Moderate',
    bestCorrectRate: 0.6,
    attempted: true,
    accessUnlocked: true,
    masteryProbability: 0.55,
    evidenceLevel: 'established',
    observationCount: 2,
    updatedAt: DateTime.utc(2026, 8, 1, 8),
  );
}

ParentPracticeSummary practiceSummary() {
  return ParentPracticeSummary(
    schemaVersion: parentPracticeSummarySchemaVersion,
    studentId: 'student_safe',
    timezone: parentPracticeTimezone,
    weekStart: DateTime.utc(2026, 8, 9, 16),
    dailyCompletionCounts: const [1, 0, 0, 0, 2, 0, 0],
    completedPracticeCount: 3,
    activeDayCount: 2,
    updatedAt: DateTime.utc(2026, 8, 11, 4),
  );
}

ForumParticipationSummary mutualAidSummary() {
  return const ForumParticipationSummary(
    studentId: 'student_safe',
    questionsPostedCount: 1,
    answersSubmittedCount: 2,
    acceptedAnswersCount: 1,
    helpfulReceivedCount: 0,
  );
}

void main() {
  testWidgets('parent dashboard renders only safe typed card inputs', (
    tester,
  ) async {
    const child = LinkedChildContext(
      studentId: 'student_safe',
      displayName: 'Aiman',
      yearLevel: 4,
    );
    final snapshot = ParentDashboardSnapshot(
      mastery: [
        masteryRecord('read_write_numbers'),
        masteryRecord('place_digit_value'),
      ],
      practiceSummary: practiceSummary(),
      forumParticipationSummary: mutualAidSummary(),
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
    expect(find.text('2 learning records are ready.'), findsOneWidget);
    expect(
      find.text('This week: 3 completed practices across 2 active days.'),
      findsOneWidget,
    );
    expect(
      find.text(
        'This week: 1 questions, 2 replies, 1 accepted answers, '
        '0 helpful marks.',
      ),
      findsOneWidget,
    );
    // No technical AI/model/server copy may reach the parent view.
    expect(find.textContaining('controlled demonstration'), findsNothing);
    expect(find.textContaining('Safe analysis'), findsNothing);
    expect(find.textContaining('Server status'), findsNothing);
    expect(find.textContaining('Fallback advice'), findsNothing);
  });

  testWidgets('unavailable cards stay distinct from recorded evidence', (
    tester,
  ) async {
    const child = LinkedChildContext(
      studentId: 'student_fallback',
      displayName: 'Bela',
      yearLevel: 5,
    );
    const snapshot = ParentDashboardSnapshot(
      mastery: <TrustedSubtopicProgress>[],
      practiceSummary: null,
      forumParticipationSummary: null,
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

    expect(
      find.text(
        'More learning evidence is needed before a focus can be named.',
      ),
      findsOneWidget,
    );
    expect(
      find.text('Practice effort is unavailable this week.'),
      findsOneWidget,
    );
    expect(
      find.text('Participation summary is unavailable this week.'),
      findsOneWidget,
    );
    expect(find.textContaining('Fallback advice'), findsNothing);
    expect(find.textContaining('controlled demonstration'), findsNothing);
  });

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
    expect(find.text('Learning map'), findsNothing);
    expect(find.textContaining('Safe analysis'), findsNothing);
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
    const belaSnapshot = ParentDashboardSnapshot(
      mastery: <TrustedSubtopicProgress>[],
    );

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ParentDashboardPage(
          state: AppState(persistQuizResults: false),
          linkedChildrenGateway: const _LinkedChildrenGateway([childA, childB]),
          dashboardLoader: (child) => child.studentId == childA.studentId
              ? firstLoad.future
              : Future.value(belaSnapshot),
        ),
      ),
    );
    await tester.pump();

    final childSelector = find.byType(
      DropdownButtonFormField<LinkedChildContext>,
    );
    await tester.ensureVisible(childSelector);
    await tester.tap(childSelector);
    // The first child's snapshot intentionally remains pending, so the loading
    // indicator never settles. Advance only the dropdown's entrance animation.
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('Bela (Year 5)').last);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    firstLoad.completeError(StateError('stale A request failed'));
    await tester.pump();

    expect(find.text('Safe learning updates for Bela.'), findsOneWidget);
    expect(
      find.text('Safe learner updates are temporarily unavailable.'),
      findsNothing,
    );
  });
}
