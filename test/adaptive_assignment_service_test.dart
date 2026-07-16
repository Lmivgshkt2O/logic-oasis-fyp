import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/models/question_bank.dart';
import 'package:logic_oasis/shared/services/adaptive_assignment_service.dart';

void main() {
  const service = AdaptiveAssignmentService();

  test('parses server-owned assignment and exposes a supportive state', () {
    final assignment = service.parseLatest('assignment-1', <Object?, Object?>{
      'subtopicId': 'read_write_numbers',
      'bankId': 'moderate-bank',
      'difficultyLevel': 'Moderate',
      'policyVersion': 'adaptive-policy-v1',
      'reasonCode': 'move_up_mastery',
      'reasonText': 'You are ready for a gentle new challenge.',
      'evidenceCount': 3,
      'masteryProbability': 0.8,
      'supportRisk': 0.2,
      'usedBktFallback': false,
    });

    expect(assignment, isNotNull);
    expect(assignment!.difficulty, QuestionDifficulty.moderate);
    expect(service.studentPracticeState(assignment), 'Practising');
  });

  test('invalid server data is unavailable rather than becoming an assignment', () {
    expect(
      service.parseLatest('bad', <Object?, Object?>{'difficultyLevel': 'Mixed'}),
      isNull,
    );
  });

  test('missing fallback state or negative evidence is unavailable', () {
    final incomplete = <Object?, Object?>{
      'subtopicId': 'read_write_numbers',
      'bankId': 'easy-bank',
      'difficultyLevel': 'Easy',
      'policyVersion': 'adaptive-policy-v1',
      'reasonCode': 'cold_start_easy',
      'reasonText': 'Let us begin.',
      'evidenceCount': 0,
    };

    expect(service.parseLatest('missing', incomplete), isNull);
    expect(
      service.parseLatest('negative', <Object?, Object?>{
        ...incomplete,
        'evidenceCount': -1,
        'usedBktFallback': true,
      }),
      isNull,
    );
  });
}
