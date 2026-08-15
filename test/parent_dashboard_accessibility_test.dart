import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
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
  return ForumParticipationSummary(
    studentId: 'student_safe',
    questionsPostedCount: 1,
    answersSubmittedCount: 2,
    acceptedAnswersCount: 1,
    helpfulReceivedCount: 0,
    weekStart: DateTime.utc(2026, 8, 9, 16),
    updatedAt: DateTime.utc(2026, 8, 10, 3),
  );
}

ParentDashboardSnapshot fullSnapshot() {
  return ParentDashboardSnapshot(
    mastery: [
      masteryRecord('read_write_numbers', 0.4),
      masteryRecord('place_digit_value', 0.9),
    ],
    practiceSummary: practiceSummary(),
    forumParticipationSummary: mutualAidSummary(),
  );
}

List<String> _flattenLabels(SemanticsNode node) {
  final labels = <String>[];
  bool visit(SemanticsNode current) {
    if (current.label.trim().isNotEmpty) {
      labels.add(current.label);
    }
    current.visitChildren(visit);
    return true;
  }

  visit(node);
  return labels;
}

Future<void> _pumpFullMap(WidgetTester tester) async {
  await tester.pumpWidget(
    MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: ParentDashboardPage(
        state: AppState(persistQuizResults: false),
        linkedChildrenGateway: const _Gateway([child]),
        dashboardLoader: (_) async => fullSnapshot(),
        clock: () => fixedNow,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('screen reader order is title, glance, Understanding, Practice, '
      'Mutual Aid, then the conversation starter', (tester) async {
    final handle = tester.ensureSemantics();
    await _pumpFullMap(tester);

    final labels = _flattenLabels(
      tester.getSemantics(find.byType(Material).first),
    );
    int indexOf(String part) =>
        labels.indexWhere((label) => label.contains(part));

    final title = indexOf('Parent Dashboard');
    final glance = indexOf('This week at a glance');
    final understanding = indexOf('Understanding');
    final practice = indexOf('Practice Effort');
    // The Mutual Aid card is anchored on its own count-only timeline row so
    // the glance sentence mentioning "Mutual Aid activity" cannot match.
    final mutualAid = indexOf('1 question asked');
    final starter = indexOf('A gentle question to ask');
    expect(glance, greaterThan(title));
    expect(understanding, greaterThan(glance));
    expect(practice, greaterThan(understanding));
    expect(mutualAid, greaterThan(practice));
    expect(starter, greaterThan(mutualAid));
    handle.dispose();
  });

  testWidgets('daily and timeline counts are announced without colour', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    await _pumpFullMap(tester);

    final labels = _flattenLabels(
      tester.getSemantics(find.byType(Material).first),
    );
    expect(labels.any((label) => label.contains('Mon: 1')), isTrue);
    expect(labels.any((label) => label.contains('Fri: 2')), isTrue);
    expect(labels.any((label) => label.contains('1 question asked')), isTrue);
    expect(labels.any((label) => label.contains('2 replies')), isTrue);
    expect(labels.any((label) => label.contains('1 accepted')), isTrue);
    // Status is text plus icon, never colour alone.
    expect(labels.any((label) => label.contains('Growing')), isTrue);
    handle.dispose();
  });

  test('parent localization carries no forbidden technical copy', () {
    final en =
        jsonDecode(File('lib/l10n/app_en.arb').readAsStringSync())
            as Map<String, dynamic>;
    final ms =
        jsonDecode(File('lib/l10n/app_ms.arb').readAsStringSync())
            as Map<String, dynamic>;

    const keys = <String>[
      'parentDashboardCaption',
      'parentDashboardUpdated',
      'glanceFull',
      'glanceFullSupport',
      'glanceFocusPractice',
      'glanceFocusPracticeSupport',
      'glanceFocusPracticeNoMutualAidYet',
      'glanceFocusPracticeNoMutualAidYetSupport',
      'glanceFocusNoPracticeYetMutualAid',
      'glanceFocusNoPracticeYetMutualAidSupport',
      'glanceFocusNoPracticeYet',
      'glanceFocusNoPracticeYetSupport',
      'glanceFocusNoPracticeYetNoMutualAidYet',
      'glanceFocusNoPracticeYetNoMutualAidYetSupport',
      'glanceFocusMutualAid',
      'glanceFocusMutualAidSupport',
      'glanceFocusNoMutualAidYet',
      'glanceFocusNoMutualAidYetSupport',
      'glanceFocusOnly',
      'glanceFocusOnlySupport',
      'glancePracticeRecorded',
      'glancePracticeRecordedSupport',
      'glanceNoPracticeYet',
      'glanceNoPracticeYetSupport',
      'glanceMutualAidRecorded',
      'glanceMutualAidRecordedSupport',
      'glanceNoMutualAidYet',
      'glanceNoMutualAidYetSupport',
      'glanceNoDataYet',
      'glanceNoDataYetSupport',
      'understandingCardTitle',
      'learningSnapshotLabel',
      'practiceCardTitle',
      'mutualAidCardTitle',
      'conversationStarterTitle',
      'focusStatusNeedsGuidedPractice',
      'focusStatusGrowing',
      'focusStatusCurrentStrength',
      'focusTopic',
      'focusSubtopic',
      'focusObservationSentence',
      'focusStrength',
      'understandingInsufficient',
      'understandingUnavailable',
      'parentNextStep',
      'actionUnderstandingFocus',
      'actionMaintainStrength',
      'actionPracticeRoutine',
      'actionMutualAidInvitation',
      'actionNeedsMoreActivity',
      'practiceWeekly',
      'practiceActiveDays',
      'practiceUnavailable',
      'practiceComparison',
      'practiceImproved',
      'dayMonday',
      'dayTuesday',
      'dayWednesday',
      'dayThursday',
      'dayFriday',
      'daySaturday',
      'daySunday',
      'mutualAidQuestions',
      'mutualAidReplies',
      'mutualAidAccepted',
      'mutualAidHelpfulMarks',
      'mutualAidZero',
      'mutualAidUnavailable',
      'conversationUnderstandingFocus',
      'conversationMaintainStrength',
      'conversationPracticeRoutine',
      'conversationMutualAidInvitation',
      'conversationNeedsMoreActivity',
    ];
    const forbidden = <String>[
      'model',
      'server',
      'shap',
      'evidence level',
      'controlled',
      'demonstration',
      'private reason',
      'confidence',
      'personality',
      'weakest',
      'artificial intelligence',
    ];

    for (final file in [en, ms]) {
      for (final key in keys) {
        final value = file[key];
        expect(value, isNotNull, reason: 'missing localized key $key');
        final lowered = (value! as String).toLowerCase();
        for (final term in forbidden) {
          expect(
            lowered.contains(term),
            isFalse,
            reason: 'key "$key" must not contain forbidden copy "$term"',
          );
        }
      }
    }
  });
}
