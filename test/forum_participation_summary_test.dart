import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/models/forum_participation_summary.dart';

void main() {
  Map<String, dynamic> baseData() => {
    'studentId': 'student_a',
    'weekStart': Timestamp.fromDate(DateTime.utc(2026, 8, 9, 16)),
    'questionsPostedCount': 1,
    'answersSubmittedCount': 2,
    'acceptedAnswersCount': 1,
    'helpfulReceivedCount': 0,
    'lastParticipationAt': Timestamp.fromDate(DateTime.utc(2026, 8, 10, 3)),
    'updatedAt': Timestamp.fromDate(DateTime.utc(2026, 8, 10, 3)),
  };

  test('parses a valid count-only summary', () {
    final summary = ForumParticipationSummary.fromFirestore(
      'student_a',
      baseData(),
    );

    expect(summary.studentId, 'student_a');
    expect(summary.questionsPostedCount, 1);
    expect(summary.answersSubmittedCount, 2);
    expect(summary.acceptedAnswersCount, 1);
    expect(summary.helpfulReceivedCount, 0);
    expect(summary.weekStart, DateTime.utc(2026, 8, 9, 16));
  });

  test('accepts a zero current-week summary', () {
    final data = baseData()
      ..['questionsPostedCount'] = 0
      ..['answersSubmittedCount'] = 0
      ..['acceptedAnswersCount'] = 0
      ..['helpfulReceivedCount'] = 0;

    final summary = ForumParticipationSummary.fromFirestore('student_a', data);

    expect(summary.questionsPostedCount, 0);
    expect(summary.answersSubmittedCount, 0);
    expect(summary.acceptedAnswersCount, 0);
    expect(summary.helpfulReceivedCount, 0);
  });

  test('malformed and negative counts are unavailable, not false zero', () {
    expect(
      () => ForumParticipationSummary.fromFirestore(
        'student_a',
        baseData()..['answersSubmittedCount'] = -1,
      ),
      throwsA(isA<FormatException>()),
    );
    expect(
      () => ForumParticipationSummary.fromFirestore(
        'student_a',
        baseData()..['helpfulReceivedCount'] = 1.5,
      ),
      throwsA(isA<FormatException>()),
    );
    expect(
      () => ForumParticipationSummary.fromFirestore(
        'student_a',
        baseData()..remove('questionsPostedCount'),
      ),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects a missing or mismatched student identity', () {
    expect(
      () => ForumParticipationSummary.fromFirestore(
        'student_a',
        baseData()..remove('studentId'),
      ),
      throwsA(isA<FormatException>()),
    );
    expect(
      () => ForumParticipationSummary.fromFirestore('student_b', baseData()),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects a missing weekStart', () {
    expect(
      () => ForumParticipationSummary.fromFirestore(
        'student_a',
        baseData()..remove('weekStart'),
      ),
      throwsA(isA<FormatException>()),
    );
  });

  test('optional participation timestamps may be absent', () {
    final data = baseData()
      ..remove('lastParticipationAt')
      ..remove('updatedAt');

    final summary = ForumParticipationSummary.fromFirestore('student_a', data);

    expect(summary.lastParticipationAt, isNull);
    expect(summary.updatedAt, isNull);
  });
}
