import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/models/adaptive_assignment.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/question_bank.dart';

void main() {
  const assignment = AdaptiveAssignment(
    id: 'student_aiman_read_write',
    subtopicId: 'read_write_numbers',
    bankId: 'whole_numbers_read_write_easy_v1',
    difficulty: QuestionDifficulty.easy,
    policyVersion: 'adaptive-policy-v1',
    reasonCode: 'low_evidence_support',
    reasonText: 'Try one short guided practice next.',
    evidenceCount: 2,
    usedBktFallback: true,
    masteryProbability: 0.4,
  );

  test('composes only safe U8 status, mastery, and assignment fields', () {
    final diagnosis = AiDiagnosis.fromSafeProjection(
      'attempt_001',
      {
        'studentId': 'student_aiman_y4',
        'sourceAttemptSequence': 2,
        'analysisState': 'fallback',
        'displayCode': 'analysis_fallback',
      },
      mastery: {
        'topicId': 'whole_numbers_y4',
        'yearLevel': 4,
        'masteryProbability': 0.4,
        'weakTopicPriorityScore': 0.3,
        'evidenceLevel': 'preliminary',
        'observationCount': 2,
        'rankingVersion': 'weak-topic-ranking-v1',
      },
      assignment: assignment,
    );

    expect(diagnosis, isNotNull);
    expect(diagnosis!.isFallback, isTrue);
    expect(diagnosis.topicId, 'whole_numbers_y4');
    expect(diagnosis.supportingReason, 'Try one short guided practice next.');
    expect(diagnosis.childFacingStatus, contains('quiz progress'));
    expect(diagnosis.hasCompatibleRanking, isTrue);
  });

  test('rejects malformed safe status instead of inventing advice', () {
    expect(
      AiDiagnosis.fromSafeProjection('attempt_bad', {
        'studentId': 'student_aiman_y4',
        'sourceAttemptSequence': 0,
        'analysisState': 'completed',
        'displayCode': 'analysis_completed',
      }),
      isNull,
    );
  });

  test('newer source sequence wins even when a delayed status arrives later', () {
    final earlier = AiDiagnosis.fromSafeProjection('attempt_001', {
      'studentId': 'student_aiman_y4',
      'sourceAttemptSequence': 1,
      'analysisState': 'completed',
      'displayCode': 'analysis_completed',
    })!;
    final later = AiDiagnosis.fromSafeProjection('attempt_002', {
      'studentId': 'student_aiman_y4',
      'sourceAttemptSequence': 2,
      'analysisState': 'completed',
      'displayCode': 'analysis_completed',
    })!;

    expect(later.isNewerThan(earlier), isTrue);
    expect(earlier.isNewerThan(later), isFalse);
  });
}
