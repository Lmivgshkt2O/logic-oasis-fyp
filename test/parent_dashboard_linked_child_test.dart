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

/// Wednesday 2026-08-12 12:00 MYT, inside the same Malaysia week as the
/// practice/forum fixtures (Monday 2026-08-10).
final fixedNow = DateTime.utc(2026, 8, 12, 4);

class _LinkedChildrenGateway implements ParentLinkedChildrenGateway {
  const _LinkedChildrenGateway(this.children);

  final List<LinkedChildContext> children;

  @override
  Future<List<LinkedChildContext>> loadLinkedChildren() async => children;
}

class _DelayedGateway implements ParentLinkedChildrenGateway {
  _DelayedGateway(this.children);

  final List<LinkedChildContext> children;
  final Completer<void> _gate = Completer<void>();

  void complete() => _gate.complete();

  @override
  Future<List<LinkedChildContext>> loadLinkedChildren() async {
    await _gate.future;
    return children;
  }
}

class _MutableGateway implements ParentLinkedChildrenGateway {
  _MutableGateway(this.load);

  Future<List<LinkedChildContext>> Function() load;

  @override
  Future<List<LinkedChildContext>> loadLinkedChildren() => load();
}

TrustedSubtopicProgress masteryRecord(
  String subtopicId, {
  double probability = 0.55,
}) {
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
  List<int> daily = const [1, 0, 0, 0, 2, 0, 0],
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
    lastParticipationAt: DateTime.utc(2026, 8, 10, 3),
    updatedAt: DateTime.utc(2026, 8, 10, 3),
  );
}

ParentDashboardSnapshot fullSnapshot() {
  return ParentDashboardSnapshot(
    mastery: [
      masteryRecord('read_write_numbers', probability: 0.4),
      masteryRecord('place_digit_value', probability: 0.9),
    ],
    practiceSummary: practiceSummary(),
    forumParticipationSummary: mutualAidSummary(),
  );
}

String demoSubtopicTitle(String subtopicId, {bool isBahasaMelayu = false}) {
  final state = AppState(persistQuizResults: false);
  final topic = state.topics.firstWhere(
    (topic) => topic.id == 'whole_numbers_y4',
  );
  final subtopic = topic.subtopics.firstWhere(
    (subtopic) => subtopic.id == subtopicId,
  );
  return isBahasaMelayu ? subtopic.titleBm : subtopic.title;
}

String demoTopicTitle({bool isBahasaMelayu = false}) {
  final state = AppState(persistQuizResults: false);
  final topic = state.topics.firstWhere(
    (topic) => topic.id == 'whole_numbers_y4',
  );
  return isBahasaMelayu ? topic.titleBm : topic.title;
}

void main() {
  testWidgets('parent dashboard renders the approved Progress Map', (
    tester,
  ) async {
    const child = LinkedChildContext(
      studentId: 'student_safe',
      displayName: 'Aiman',
      yearLevel: 4,
    );

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ParentDashboardPage(
          state: AppState(persistQuizResults: false),
          linkedChildrenGateway: const _LinkedChildrenGateway([child]),
          dashboardLoader: (_) async => fullSnapshot(),
          clock: () => fixedNow,
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Header identifies the child and the protected-activity boundary.
    expect(find.text('Safe learning updates for Aiman.'), findsOneWidget);
    expect(find.textContaining('Updated: 11/8/2026'), findsOneWidget);

    // Weekly glance truthfully mentions focus, practice, and Mutual Aid.
    expect(find.text('A steady week with a clear focus.'), findsOneWidget);
    expect(
      find.text(
        '${demoSubtopicTitle('read_write_numbers')} is the focus, with '
        'practice and Mutual Aid activity this week.',
      ),
      findsOneWidget,
    );

    // Understanding card: focus, qualitative status, evidence, strength, step.
    expect(find.text('Understanding'), findsOneWidget);
    expect(find.text('Learning snapshot'), findsOneWidget);
    expect(find.text('Topic: ${demoTopicTitle()}'), findsOneWidget);
    expect(
      find.text('Focus: ${demoSubtopicTitle('read_write_numbers')}'),
      findsOneWidget,
    );
    expect(find.text('Growing'), findsOneWidget);
    expect(
      find.text('Based on 2 trusted learning observations.'),
      findsOneWidget,
    );
    expect(
      find.text('Strength: ${demoSubtopicTitle('place_digit_value')}'),
      findsOneWidget,
    );
    expect(find.text('Parent next step'), findsOneWidget);
    expect(
      find.text(
        'Practise ${demoSubtopicTitle('read_write_numbers')} together this '
        'week.',
      ),
      findsOneWidget,
    );

    // Practice Effort: weekly total, active days, Mon-Sun rhythm.
    expect(find.text('Practice Effort'), findsOneWidget);
    expect(
      find.text('3 practices completed this week across 2 active days'),
      findsOneWidget,
    );
    expect(find.text('Mon'), findsOneWidget);
    expect(find.text('Fri'), findsOneWidget);

    // Mutual Aid: count-only timeline rows for nonzero events.
    expect(find.text('Mutual Aid'), findsOneWidget);
    expect(find.text('1 question asked'), findsOneWidget);
    expect(find.text('2 replies · 1 accepted'), findsOneWidget);
    expect(find.textContaining('helpful marks'), findsNothing);

    // One action and its matching conversation starter.
    expect(find.text('A gentle question to ask'), findsOneWidget);
    expect(
      find.text(
        'What part of ${demoSubtopicTitle('read_write_numbers')} should we '
        'look at together?',
      ),
      findsOneWidget,
    );

    // No technical AI/model/server copy may reach the parent view.
    expect(find.textContaining('controlled demonstration'), findsNothing);
    expect(find.textContaining('Safe analysis'), findsNothing);
    expect(find.textContaining('Server status'), findsNothing);
  });

  testWidgets(
    'insufficient Understanding, unavailable cards, and zero activity are '
    'distinct states',
    (tester) async {
      const child = LinkedChildContext(
        studentId: 'student_safe',
        displayName: 'Aiman',
        yearLevel: 4,
      );

      await tester.pumpWidget(
        MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: ParentDashboardPage(
            state: AppState(persistQuizResults: false),
            linkedChildrenGateway: const _LinkedChildrenGateway([child]),
            dashboardLoader: (_) async => const ParentDashboardSnapshot(
              mastery: <TrustedSubtopicProgress>[],
              practiceSummary: null,
              forumParticipationSummary: null,
            ),
            clock: () => fixedNow,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.text(
          'More recent learning evidence is needed before a focus can be '
          'named.',
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
      expect(
        find.text('Learning evidence is still being collected.'),
        findsOneWidget,
      );
      // No supported action or conversation starter without evidence.
      expect(find.text('A gentle question to ask'), findsNothing);
    },
  );

  testWidgets('recorded zero activity stays distinct from unavailable', (
    tester,
  ) async {
    const child = LinkedChildContext(
      studentId: 'student_safe',
      displayName: 'Aiman',
      yearLevel: 4,
    );

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ParentDashboardPage(
          state: AppState(persistQuizResults: false),
          linkedChildrenGateway: const _LinkedChildrenGateway([child]),
          dashboardLoader: (_) async => ParentDashboardSnapshot(
            mastery: const [],
            practiceSummary: practiceSummary(
              daily: const [0, 0, 0, 0, 0, 0, 0],
            ),
            forumParticipationSummary: mutualAidSummary(
              questions: 0,
              answers: 0,
              accepted: 0,
              helpful: 0,
            ),
          ),
          clock: () => fixedNow,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('No practice completed yet this week across 0 active days'),
      findsOneWidget,
    );
    expect(find.text('No Mutual Aid moments yet this week.'), findsOneWidget);
    expect(
      find.text('Shall we do one short practice together this week?'),
      findsOneWidget,
    );
  });

  testWidgets('prior-week comparison appears only with a valid prior total', (
    tester,
  ) async {
    const child = LinkedChildContext(
      studentId: 'student_safe',
      displayName: 'Aiman',
      yearLevel: 4,
    );

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ParentDashboardPage(
          state: AppState(persistQuizResults: false),
          linkedChildrenGateway: const _LinkedChildrenGateway([child]),
          dashboardLoader: (_) async => ParentDashboardSnapshot(
            mastery: const [],
            practiceSummary: practiceSummary(previousWeek: 1),
          ),
          clock: () => fixedNow,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Compared with 1 practice last week.'), findsOneWidget);
    expect(find.text('Practice improved by 2 this week.'), findsOneWidget);
    expect(find.text('Compared with 2 practices last week.'), findsNothing);
  });

  testWidgets('Bahasa Melayu renders titles, plurals, and day labels', (
    tester,
  ) async {
    const child = LinkedChildContext(
      studentId: 'student_safe',
      displayName: 'Aiman',
      yearLevel: 4,
    );
    final state = AppState(persistQuizResults: false)
      ..language = 'Bahasa Melayu';

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('ms'),
        home: ParentDashboardPage(
          state: state,
          linkedChildrenGateway: const _LinkedChildrenGateway([child]),
          dashboardLoader: (_) async => fullSnapshot(),
          clock: () => fixedNow,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Pemahaman'), findsOneWidget);
    expect(find.text('Usaha Latihan'), findsOneWidget);
    expect(find.text('Saling Membantu'), findsOneWidget);
    expect(
      find.text('3 latihan disiapkan minggu ini sepanjang 2 hari aktif'),
      findsOneWidget,
    );
    expect(find.text('Isn'), findsOneWidget);
    expect(find.text('Soalan ringkas untuk ditanya'), findsOneWidget);
    expect(
      find.text(
        'Fokus: ${demoSubtopicTitle('read_write_numbers', isBahasaMelayu: true)}',
      ),
      findsOneWidget,
    );
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
    expect(find.text('Understanding'), findsNothing);
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
          clock: () => fixedNow,
        ),
      ),
    );
    await tester.pump();

    final childSelector = find.byType(
      DropdownButtonFormField<LinkedChildContext>,
    );
    await tester.ensureVisible(childSelector);
    await tester.tap(childSelector);
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

  testWidgets('a stale child-load success cannot replace a newer selection', (
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
    final aimanSnapshot = ParentDashboardSnapshot(
      mastery: [masteryRecord('read_write_numbers', probability: 0.4)],
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
          clock: () => fixedNow,
        ),
      ),
    );
    await tester.pump();

    final childSelector = find.byType(
      DropdownButtonFormField<LinkedChildContext>,
    );
    await tester.ensureVisible(childSelector);
    await tester.tap(childSelector);
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.text('Bela (Year 5)').last);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    firstLoad.complete(aimanSnapshot);
    await tester.pump();

    expect(find.text('Safe learning updates for Bela.'), findsOneWidget);
    expect(
      find.text('Focus: ${demoSubtopicTitle('read_write_numbers')}'),
      findsNothing,
    );
    expect(
      find.text(
        'More recent learning evidence is needed before a focus can be '
        'named.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('initial links loading banner is distinct from child loading', (
    tester,
  ) async {
    const child = LinkedChildContext(
      studentId: 'student_safe',
      displayName: 'Aiman',
      yearLevel: 4,
    );
    final gate = _DelayedGateway(const [child]);

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ParentDashboardPage(
          state: AppState(persistQuizResults: false),
          linkedChildrenGateway: gate,
          dashboardLoader: (_) async => fullSnapshot(),
          clock: () => fixedNow,
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Loading linked learners…'), findsOneWidget);

    gate.complete();
    await tester.pumpAndSettle();

    expect(find.text('Loading linked learners…'), findsNothing);
    expect(find.text('Understanding'), findsOneWidget);
  });

  testWidgets('link error is distinct and retry reloads linked children', (
    tester,
  ) async {
    const child = LinkedChildContext(
      studentId: 'student_safe',
      displayName: 'Aiman',
      yearLevel: 4,
    );
    var fail = true;
    final gate = _MutableGateway(() async {
      if (fail) {
        throw const ParentLinkContextException('Link context unavailable.');
      }
      return const [child];
    });

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ParentDashboardPage(
          state: AppState(persistQuizResults: false),
          linkedChildrenGateway: gate,
          dashboardLoader: (_) async => fullSnapshot(),
          clock: () => fixedNow,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Link context unavailable.'), findsOneWidget);
    expect(find.text('Understanding'), findsNothing);

    fail = false;
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();

    expect(find.text('Safe learning updates for Aiman.'), findsOneWidget);
    expect(find.text('Understanding'), findsOneWidget);
  });

  testWidgets('revocation clears the child view with a reconnect message', (
    tester,
  ) async {
    const child = LinkedChildContext(
      studentId: 'student_safe',
      displayName: 'Aiman',
      yearLevel: 4,
    );

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ParentDashboardPage(
          state: AppState(persistQuizResults: false),
          linkedChildrenGateway: const _LinkedChildrenGateway([child]),
          dashboardLoader: (_) async =>
              throw const ParentDashboardAuthException('revoked'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('This learner link is no longer active. Please reconnect.'),
      findsOneWidget,
    );
    expect(find.text('Understanding'), findsNothing);
    expect(find.text('Safe learning updates for Aiman.'), findsOneWidget);
  });

  testWidgets('card retry reloads only the retried card', (tester) async {
    const child = LinkedChildContext(
      studentId: 'student_safe',
      displayName: 'Aiman',
      yearLevel: 4,
    );
    var calls = 0;
    final retryLoader = Completer<ParentDashboardSnapshot>();
    final partial = ParentDashboardSnapshot(
      mastery: [masteryRecord('read_write_numbers', probability: 0.4)],
    );
    final full = fullSnapshot();

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ParentDashboardPage(
          state: AppState(persistQuizResults: false),
          linkedChildrenGateway: const _LinkedChildrenGateway([child]),
          dashboardLoader: (child) =>
              calls++ == 0 ? Future.value(partial) : retryLoader.future,
          clock: () => fixedNow,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Practice effort is unavailable this week.'),
      findsOneWidget,
    );
    expect(find.text('Retry'), findsNWidgets(2));

    await tester.tap(find.widgetWithText(TextButton, 'Retry').first);
    await tester.pump();
    expect(find.byType(CircularProgressIndicator), findsWidgets);

    retryLoader.complete(full);
    await tester.pumpAndSettle();

    expect(
      find.text('3 practices completed this week across 2 active days'),
      findsOneWidget,
    );
    expect(
      find.text('Practice effort is unavailable this week.'),
      findsNothing,
    );
    expect(find.text('Retry'), findsNothing);
  });
}
