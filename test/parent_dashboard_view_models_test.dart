import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_time.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_view_models.dart';
import 'package:logic_oasis/shared/models/forum_participation_summary.dart';
import 'package:logic_oasis/shared/models/parent_practice_summary.dart';
import 'package:logic_oasis/shared/models/subtopic.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/models/trusted_subtopic_progress.dart';

const studentId = 'student_a';
const yearLevel = 4;
const Object _unset = 'unset-marker';

// Wednesday 2026-08-12 12:00 MYT.
final now = DateTime.utc(2026, 8, 12, 4);
final currentWeekStart = malaysiaWeekStartUtc(now);
final previousWeekStart = currentWeekStart.subtract(const Duration(days: 7));

Subtopic subtopic(String id, String title, String titleBm) =>
    Subtopic(id: id, title: title, titleBm: titleBm, order: 1);

Topic topic(
  String id,
  String title,
  String titleBm,
  List<Subtopic> subtopics,
) => Topic(
  id: id,
  title: title,
  titleBm: titleBm,
  area: 'Number and Operations',
  areaBm: 'Nombor dan Operasi',
  yearLevel: yearLevel,
  progress: 0,
  mastery: 'New',
  subtopics: subtopics,
);

final curriculum = [
  topic('whole_numbers_y4', 'Whole Numbers', 'Nombor Bulat', [
    subtopic(
      'read_write_numbers',
      'Read and Write Numbers',
      'Membaca dan Menulis Nombor',
    ),
    subtopic(
      'place_digit_value',
      'Place and Digit Value',
      'Nilai Tempat dan Digit',
    ),
    subtopic(
      'compare_order_numbers',
      'Compare and Order Numbers',
      'Banding dan Susun Nombor',
    ),
  ]),
  topic('fractions_y4', 'Fractions', 'Pecahan', [
    subtopic('equivalent_fractions', 'Equivalent Fractions', 'Pecahan Setara'),
  ]),
];

TrustedSubtopicProgress masteryRecord({
  String recordStudentId = studentId,
  int recordYearLevel = yearLevel,
  String topicId = 'whole_numbers_y4',
  String subtopicId = 'read_write_numbers',
  String evidenceLevel = 'established',
  Object? observationCount = 2,
  Object? masteryProbability = 0.5,
  Object? updatedAt = _unset,
}) {
  return TrustedSubtopicProgress(
    studentId: recordStudentId,
    topicId: topicId,
    subtopicId: subtopicId,
    yearLevel: recordYearLevel,
    completed: true,
    masteryLevel: 'Moderate',
    bestCorrectRate: 0.6,
    attempted: true,
    accessUnlocked: true,
    masteryProbability: masteryProbability == _unset
        ? null
        : masteryProbability as double?,
    evidenceLevel: evidenceLevel,
    observationCount: observationCount == _unset
        ? null
        : observationCount as int?,
    updatedAt: updatedAt == _unset
        ? now.subtract(const Duration(days: 3))
        : updatedAt as DateTime?,
  );
}

ParentPracticeSummary practiceSummary({
  List<int> daily = const [0, 0, 0, 0, 0, 0, 0],
  int? previousWeek,
  DateTime? weekStart,
}) {
  return ParentPracticeSummary(
    schemaVersion: parentPracticeSummarySchemaVersion,
    studentId: studentId,
    timezone: parentPracticeTimezone,
    weekStart: weekStart ?? currentWeekStart,
    dailyCompletionCounts: daily,
    completedPracticeCount: daily.fold(0, (sum, value) => sum + value),
    activeDayCount: daily.where((value) => value > 0).length,
    previousWeekCompletedPracticeCount: previousWeek,
    lastPracticeAt: now,
    updatedAt: now,
  );
}

ForumParticipationSummary mutualAidSummary({
  int questions = 0,
  int answers = 0,
  int accepted = 0,
  int helpful = 0,
  String? childId,
  DateTime? weekStart,
}) {
  return ForumParticipationSummary(
    studentId: childId ?? studentId,
    questionsPostedCount: questions,
    answersSubmittedCount: answers,
    acceptedAnswersCount: accepted,
    helpfulReceivedCount: helpful,
    weekStart: weekStart ?? currentWeekStart,
    lastParticipationAt: now,
    updatedAt: now,
  );
}

ParentProgressMapViewModel derive({
  List<TrustedSubtopicProgress>? mastery,
  ParentPracticeSummary? practice,
  ForumParticipationSummary? mutualAid,
  DateTime? at,
}) {
  return deriveParentProgressMap(
    now: at ?? now,
    studentId: studentId,
    yearLevel: yearLevel,
    mastery: mastery ?? const [],
    practice: practice,
    mutualAid: mutualAid,
    curriculum: curriculum,
  );
}

void main() {
  group('Understanding eligibility', () {
    test('an eligible established record becomes the focus', () {
      final view = derive(mastery: [masteryRecord()]);

      expect(view.understanding.status, ParentUnderstandingStatus.ready);
      expect(view.understanding.topicId, 'whole_numbers_y4');
      expect(view.understanding.topicTitle, 'Whole Numbers');
      expect(view.understanding.topicTitleBm, 'Nombor Bulat');
      expect(view.understanding.focusSubtopicId, 'read_write_numbers');
      expect(view.understanding.focusSubtopicTitle, 'Read and Write Numbers');
      expect(
        view.understanding.focusSubtopicTitleBm,
        'Membaca dan Menulis Nombor',
      );
    });

    test('preliminary, unavailable, zero, and missing-evidence records do not '
        'become a focus', () {
      final preliminary = derive(
        mastery: [masteryRecord(evidenceLevel: 'preliminary')],
      );
      final unavailable = derive(
        mastery: [masteryRecord(evidenceLevel: 'unavailable')],
      );
      final zeroObservations = derive(
        mastery: [masteryRecord(observationCount: 0)],
      );
      final missingObservations = derive(
        mastery: [masteryRecord(observationCount: null)],
      );
      final missingProbability = derive(
        mastery: [masteryRecord(masteryProbability: null)],
      );
      final missingTime = derive(mastery: [masteryRecord(updatedAt: null)]);

      for (final view in [
        preliminary,
        unavailable,
        zeroObservations,
        missingObservations,
        missingProbability,
        missingTime,
      ]) {
        expect(
          view.understanding.status,
          ParentUnderstandingStatus.insufficientEvidence,
          reason: 'every ineligible record must stay insufficient',
        );
      }
    });

    test('stale records are rejected and the 14-day boundary is accepted', () {
      final stale = derive(
        mastery: [
          masteryRecord(updatedAt: now.subtract(const Duration(days: 15))),
        ],
      );
      final boundary = derive(
        mastery: [
          masteryRecord(updatedAt: now.subtract(const Duration(days: 14))),
        ],
      );
      final future = derive(
        mastery: [masteryRecord(updatedAt: now.add(const Duration(hours: 1)))],
      );

      expect(
        stale.understanding.status,
        ParentUnderstandingStatus.insufficientEvidence,
      );
      expect(boundary.understanding.status, ParentUnderstandingStatus.ready);
      expect(
        future.understanding.status,
        ParentUnderstandingStatus.insufficientEvidence,
      );
    });

    test('wrong child, wrong year, and unknown curriculum IDs are rejected '
        'before label mapping', () {
      final wrongChild = derive(
        mastery: [masteryRecord(recordStudentId: 'other_student')],
      );
      final wrongYear = derive(mastery: [masteryRecord(recordYearLevel: 5)]);
      final unknownTopic = derive(
        mastery: [masteryRecord(topicId: 'unknown_topic_y4')],
      );
      final unknownSubtopic = derive(
        mastery: [masteryRecord(subtopicId: 'unknown_subtopic')],
      );

      for (final view in [
        wrongChild,
        wrongYear,
        unknownTopic,
        unknownSubtopic,
      ]) {
        expect(
          view.understanding.status,
          ParentUnderstandingStatus.insufficientEvidence,
        );
      }
    });
  });

  group('Deterministic focus and comparator selection', () {
    test('lowest mastery probability wins', () {
      final view = derive(
        mastery: [
          masteryRecord(
            subtopicId: 'read_write_numbers',
            masteryProbability: 0.5,
          ),
          masteryRecord(
            subtopicId: 'place_digit_value',
            masteryProbability: 0.3,
          ),
          masteryRecord(
            subtopicId: 'compare_order_numbers',
            masteryProbability: 0.7,
          ),
        ],
      );

      expect(view.understanding.focusSubtopicId, 'place_digit_value');
    });

    test(
      'exact probability ties use newest updatedAt then stable subtopic id',
      () {
        final newer = now.subtract(const Duration(days: 1));
        final older = now.subtract(const Duration(days: 4));
        final byTime = derive(
          mastery: [
            masteryRecord(
              subtopicId: 'read_write_numbers',
              masteryProbability: 0.5,
              updatedAt: older,
            ),
            masteryRecord(
              subtopicId: 'place_digit_value',
              masteryProbability: 0.5,
              updatedAt: newer,
            ),
          ],
        );
        final byId = derive(
          mastery: [
            masteryRecord(
              subtopicId: 'read_write_numbers',
              masteryProbability: 0.5,
              updatedAt: older,
            ),
            masteryRecord(
              subtopicId: 'place_digit_value',
              masteryProbability: 0.5,
              updatedAt: older,
            ),
          ],
        );

        expect(byTime.understanding.focusSubtopicId, 'place_digit_value');
        expect(byId.understanding.focusSubtopicId, 'place_digit_value');
      },
    );

    test('the strongest same-topic eligible comparator is selected once', () {
      final view = derive(
        mastery: [
          masteryRecord(
            subtopicId: 'read_write_numbers',
            masteryProbability: 0.3,
          ),
          masteryRecord(
            subtopicId: 'place_digit_value',
            masteryProbability: 0.9,
          ),
          masteryRecord(
            subtopicId: 'compare_order_numbers',
            masteryProbability: 0.85,
          ),
          // Cross-topic and stronger: must never appear as the comparator.
          masteryRecord(
            topicId: 'fractions_y4',
            subtopicId: 'equivalent_fractions',
            masteryProbability: 0.99,
          ),
        ],
      );

      expect(view.understanding.focusSubtopicId, 'read_write_numbers');
      expect(view.understanding.positiveSubtopicId, 'place_digit_value');
      expect(view.understanding.positiveMasteryProbability, 0.9);
      expect(
        view.understanding.positiveSubtopicId,
        isNot('equivalent_fractions'),
      );
    });

    test(
      'the comparator is omitted when no other eligible subtopic exists',
      () {
        final view = derive(
          mastery: [
            masteryRecord(
              subtopicId: 'read_write_numbers',
              masteryProbability: 0.3,
            ),
          ],
        );

        expect(view.understanding.focusSubtopicId, 'read_write_numbers');
        expect(view.understanding.positiveSubtopicId, isNull);
      },
    );
  });

  group('Practice Effort availability', () {
    test('current zero is a ready state, distinct from missing', () {
      final zero = derive(practice: practiceSummary());
      final missing = derive(practice: null);
      final stale = derive(
        practice: practiceSummary(weekStart: previousWeekStart),
      );
      final notMondayMidnight = derive(
        practice: practiceSummary(weekStart: DateTime.utc(2026, 8, 10, 2)),
      );

      expect(zero.practice.status, ParentPracticeStatus.ready);
      expect(zero.practice.weeklyTotal, 0);
      expect(zero.practice.activeDayCount, 0);
      expect(missing.practice.status, ParentPracticeStatus.unavailable);
      expect(stale.practice.status, ParentPracticeStatus.unavailable);
      expect(
        notMondayMidnight.practice.status,
        ParentPracticeStatus.unavailable,
      );
    });

    test('a valid nonzero week reports total, active days, and day counts', () {
      final view = derive(
        practice: practiceSummary(
          daily: [1, 0, 0, 0, 2, 0, 1],
          previousWeek: 2,
        ),
      );

      expect(view.practice.status, ParentPracticeStatus.ready);
      expect(view.practice.weeklyTotal, 4);
      expect(view.practice.activeDayCount, 3);
      expect(view.practice.dailyCounts, [1, 0, 0, 0, 2, 0, 1]);
    });
  });

  group('Mutual Aid availability', () {
    test('malformed models never reach the deriver; zero is distinct from '
        'missing, stale, and wrong-child', () {
      final zero = derive(mutualAid: mutualAidSummary());
      final missing = derive(mutualAid: null);
      final stale = derive(
        mutualAid: mutualAidSummary(weekStart: previousWeekStart),
      );
      final wrongChild = derive(
        mutualAid: mutualAidSummary(childId: 'other_student'),
      );
      final activity = derive(
        mutualAid: mutualAidSummary(questions: 1, answers: 2, accepted: 1),
      );

      expect(zero.mutualAid.status, ParentMutualAidStatus.ready);
      expect(zero.mutualAid.totalActivity, 0);
      expect(zero.mutualAid.hasActivity, isFalse);
      expect(missing.mutualAid.status, ParentMutualAidStatus.unavailable);
      expect(stale.mutualAid.status, ParentMutualAidStatus.unavailable);
      expect(wrongChild.mutualAid.status, ParentMutualAidStatus.unavailable);
      expect(activity.mutualAid.status, ParentMutualAidStatus.ready);
      expect(activity.mutualAid.totalActivity, 4);
      expect(activity.mutualAid.hasActivity, isTrue);
    });
  });

  group('Mastery bands', () {
    test('0.40 and 0.70 are the exact band boundaries', () {
      expect(parentMasteryBand(0.39), ParentMasteryBand.needsGuidedPractice);
      expect(parentMasteryBand(0.40), ParentMasteryBand.growing);
      expect(parentMasteryBand(0.69), ParentMasteryBand.growing);
      expect(parentMasteryBand(0.70), ParentMasteryBand.currentStrength);
      expect(parentMasteryBand(1.0), ParentMasteryBand.currentStrength);
    });
  });

  group('Action, conversation starter, and glance policy', () {
    test('full evidence selects the Understanding focus action and matching '
        'conversation starter', () {
      final view = derive(
        mastery: [
          masteryRecord(
            subtopicId: 'read_write_numbers',
            masteryProbability: 0.35,
          ),
        ],
        practice: practiceSummary(daily: [1, 0, 1, 0, 1, 0, 0]),
        mutualAid: mutualAidSummary(questions: 1, answers: 2, accepted: 1),
      );

      expect(view.action?.kind, ParentActionKind.understandingFocus);
      expect(view.action?.masteryBand, ParentMasteryBand.needsGuidedPractice);
      expect(view.action?.focusSubtopicId, 'read_write_numbers');
      expect(
        view.conversationStarter?.actionKind,
        ParentActionKind.understandingFocus,
      );
      expect(view.conversationStarter?.templateKey, isNotEmpty);
      expect(view.glance.hasFocus, isTrue);
      expect(view.glance.hasPracticeActivity, isTrue);
      expect(view.glance.hasMutualAidActivity, isTrue);
      expect(view.glance.key, 'glance_focus_practice_mutual_aid');
    });

    test(
      'a current strength uses a maintain action and never calls it weak',
      () {
        final view = derive(
          mastery: [
            masteryRecord(
              subtopicId: 'read_write_numbers',
              masteryProbability: 0.85,
            ),
          ],
        );

        expect(view.action?.kind, ParentActionKind.maintainStrength);
        expect(view.action?.masteryBand, ParentMasteryBand.currentStrength);
        expect(
          view.conversationStarter?.actionKind,
          ParentActionKind.maintainStrength,
        );
      },
    );

    test('no eligible Understanding with zero practice selects the practice '
        'routine action', () {
      final view = derive(practice: practiceSummary());

      expect(view.action?.kind, ParentActionKind.practiceRoutine);
      expect(view.glance.key, 'glance_no_practice_yet');
    });

    test('recorded practice without Understanding continues to Mutual Aid '
        'evaluation', () {
      final zeroMutualAid = derive(
        practice: practiceSummary(daily: [1, 0, 0, 0, 0, 0, 0]),
        mutualAid: mutualAidSummary(),
      );
      final activeMutualAid = derive(
        practice: practiceSummary(daily: [1, 0, 0, 0, 0, 0, 0]),
        mutualAid: mutualAidSummary(answers: 1),
      );

      expect(zeroMutualAid.action?.kind, ParentActionKind.mutualAidInvitation);
      expect(activeMutualAid.action?.kind, ParentActionKind.needsMoreActivity);
    });

    test('unavailable evidence never produces an action from that source', () {
      final allUnavailable = derive();
      final practiceOnlyUnavailable = derive(
        mutualAid: mutualAidSummary(questions: 1),
      );
      final mutualAidOnlyUnavailable = derive(
        practice: practiceSummary(daily: [1, 0, 0, 0, 0, 0, 0]),
      );

      expect(allUnavailable.action, isNull);
      expect(allUnavailable.conversationStarter, isNull);
      expect(allUnavailable.glance.key, 'glance_no_data_yet');
      expect(
        practiceOnlyUnavailable.action?.kind,
        ParentActionKind.needsMoreActivity,
      );
      expect(mutualAidOnlyUnavailable.action, isNull);
    });

    test('improvement language requires a valid prior-week comparison', () {
      final improved = derive(
        practice: practiceSummary(
          daily: [1, 0, 1, 0, 1, 0, 0],
          previousWeek: 1,
        ),
      );
      final noPrior = derive(
        practice: practiceSummary(daily: [1, 0, 1, 0, 1, 0, 0]),
      );
      final declined = derive(
        practice: practiceSummary(
          daily: [1, 0, 0, 0, 0, 0, 0],
          previousWeek: 5,
        ),
      );

      expect(improved.practice.improvedOverPreviousWeek, isTrue);
      expect(improved.practice.supportedDifference, 2);
      expect(improved.glance.improvedOverPreviousWeek, isTrue);
      expect(noPrior.practice.improvedOverPreviousWeek, isFalse);
      expect(noPrior.practice.supportedDifference, isNull);
      expect(declined.practice.improvedOverPreviousWeek, isFalse);
      expect(declined.practice.supportedDifference, -4);
    });

    test('every derived glance and conversation key stays free of forbidden '
        'technical copy', () {
      const forbidden = [
        'model',
        'server',
        ' ai',
        'shap',
        'evidence',
        'controlled',
        'demonstration',
        'reason',
        'confidence',
        'personality',
        'skill snapshot',
      ];
      final keys = <String>{};
      final practices = [
        null,
        practiceSummary(),
        practiceSummary(daily: [1, 0, 0, 0, 0, 0, 0]),
        practiceSummary(weekStart: previousWeekStart),
      ];
      final mutualAids = [
        null,
        mutualAidSummary(),
        mutualAidSummary(answers: 1),
        mutualAidSummary(weekStart: previousWeekStart),
      ];
      for (final focus in [false, true]) {
        for (final practice in practices) {
          for (final mutualAid in mutualAids) {
            final view = derive(
              mastery: focus ? [masteryRecord()] : const [],
              practice: practice,
              mutualAid: mutualAid,
            );
            keys.add(view.glance.key);
            final starter = view.conversationStarter;
            if (starter != null) keys.add(starter.templateKey);
          }
        }
      }

      for (final key in keys) {
        final lowered = key.toLowerCase();
        for (final term in forbidden) {
          expect(
            lowered.contains(term),
            isFalse,
            reason: 'key "$key" must not contain forbidden copy "$term"',
          );
        }
      }
    });
  });
}
