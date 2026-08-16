// Durable four-state layout captures for the U14 evidence record. Text renders
// with the test font; these are reproducible emulator-independent captures and
// are supplemented by the live emulator rehearsal screenshots.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/forum_participation_summary.dart';
import 'package:logic_oasis/shared/models/linked_child_context.dart';
import 'package:logic_oasis/shared/models/parent_dashboard_snapshot.dart';
import 'package:logic_oasis/shared/models/parent_practice_summary.dart';
import 'package:logic_oasis/shared/models/trusted_subtopic_progress.dart';
import 'package:logic_oasis/shared/services/parent_link_context_service.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

final fixedNow = DateTime.utc(2026, 8, 12, 4);

const child = LinkedChildContext(
  studentId: 'student_safe',
  displayName: 'Aiman',
  yearLevel: 4,
);

class _Gateway implements ParentLinkedChildrenGateway {
  const _Gateway(this.children);

  final List<LinkedChildContext> children;

  @override
  Future<List<LinkedChildContext>> loadLinkedChildren() async => children;
}

TrustedSubtopicProgress masteryRecord(String subtopicId, double probability) {
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
    masteryProbability: probability,
    evidenceLevel: 'established',
    observationCount: 2,
    updatedAt: DateTime.utc(2026, 8, 1, 8),
  );
}

ParentPracticeSummary practiceSummary({
  List<int> daily = const [1, 0, 1, 0, 1, 0, 0],
  int? previousWeek,
}) {
  return ParentPracticeSummary(
    schemaVersion: parentPracticeSummarySchemaVersion,
    studentId: 'student_safe',
    timezone: parentPracticeTimezone,
    weekStart: DateTime.utc(2026, 8, 9, 16),
    dailyCompletionCounts: daily,
    completedPracticeCount: daily.fold(0, (sum, value) => sum + value),
    activeDayCount: daily.where((value) => value > 0).length,
    previousWeekCompletedPracticeCount: previousWeek,
    updatedAt: DateTime.utc(2026, 8, 11, 4),
  );
}

ForumParticipationSummary mutualAidSummary({
  int questions = 1,
  int answers = 2,
  int accepted = 1,
  int helpful = 0,
}) {
  return ForumParticipationSummary(
    studentId: 'student_safe',
    questionsPostedCount: questions,
    answersSubmittedCount: answers,
    acceptedAnswersCount: accepted,
    helpfulReceivedCount: helpful,
    weekStart: DateTime.utc(2026, 8, 9, 16),
    updatedAt: DateTime.utc(2026, 8, 10, 3),
  );
}

Future<void> pumpState(
  WidgetTester tester,
  ParentDashboardSnapshot snapshot,
  String key,
) async {
  await tester.binding.setSurfaceSize(const Size(430, 1800));
  addTearDown(() => tester.binding.setSurfaceSize(null));
  await tester.pumpWidget(
    MaterialApp(theme: LogicOasisTheme.light(),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: ParentDashboardPage(
        key: ValueKey<String>(key),
        state: AppState(persistQuizResults: false),
        linkedChildrenGateway: const _Gateway([child]),
        dashboardLoader: (_) async => snapshot,
        clock: () => fixedNow,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('captures full, partial, zero, and insufficient states', (
    tester,
  ) async {
    await pumpState(
      tester,
      ParentDashboardSnapshot(
        mastery: [
          masteryRecord('read_write_numbers', 0.4),
          masteryRecord('place_digit_value', 0.9),
        ],
        practiceSummary: practiceSummary(previousWeek: 1),
        forumParticipationSummary: mutualAidSummary(),
      ),
      'full',
    );
    await expectLater(
      find.byType(Material).first,
      matchesGoldenFile('../docs/evidence/2026-08-15-u14-screenshots/full.png'),
    );

    await pumpState(
      tester,
      ParentDashboardSnapshot(
        mastery: [
          masteryRecord('read_write_numbers', 0.4),
          masteryRecord('place_digit_value', 0.9),
        ],
        practiceSummary: practiceSummary(),
        forumParticipationSummary: mutualAidSummary(),
      ),
      'partial',
    );
    await expectLater(
      find.byType(Material).first,
      matchesGoldenFile(
        '../docs/evidence/2026-08-15-u14-screenshots/partial.png',
      ),
    );

    await pumpState(
      tester,
      ParentDashboardSnapshot(
        mastery: const [],
        practiceSummary: practiceSummary(daily: const [0, 0, 0, 0, 0, 0, 0]),
        forumParticipationSummary: mutualAidSummary(
          questions: 0,
          answers: 0,
          accepted: 0,
          helpful: 0,
        ),
      ),
      'zero',
    );
    await expectLater(
      find.byType(Material).first,
      matchesGoldenFile('../docs/evidence/2026-08-15-u14-screenshots/zero.png'),
    );

    await pumpState(
      tester,
      const ParentDashboardSnapshot(
        mastery: <TrustedSubtopicProgress>[],
        practiceSummary: null,
        forumParticipationSummary: null,
      ),
      'insufficient',
    );
    await expectLater(
      find.byType(Material).first,
      matchesGoldenFile(
        '../docs/evidence/2026-08-15-u14-screenshots/insufficient.png',
      ),
    );
  });
}
