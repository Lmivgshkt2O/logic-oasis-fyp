import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/models/parent_practice_summary.dart';

void main() {
  // Monday 2026-08-10 00:00 in Asia/Kuala_Lumpur (UTC+8).
  final mondayStart = DateTime.utc(2026, 8, 9, 16);

  Map<String, dynamic> baseData() => {
    'schemaVersion': parentPracticeSummarySchemaVersion,
    'studentId': 'student_a',
    'timezone': parentPracticeTimezone,
    'weekStart': Timestamp.fromDate(mondayStart),
    'dailyCompletionCounts': [1, 0, 0, 0, 2, 0, 0],
    'completedPracticeCount': 3,
    'activeDayCount': 2,
    'previousWeekCompletedPracticeCount': 1,
    'lastPracticeAt': Timestamp.fromDate(DateTime.utc(2026, 8, 11, 4)),
    'updatedAt': Timestamp.fromDate(DateTime.utc(2026, 8, 11, 4, 30)),
  };

  test('parses a valid current-week summary', () {
    final summary = ParentPracticeSummary.fromFirestore(
      'student_a',
      baseData(),
    );

    expect(summary.schemaVersion, parentPracticeSummarySchemaVersion);
    expect(summary.studentId, 'student_a');
    expect(summary.timezone, parentPracticeTimezone);
    expect(summary.weekStart, mondayStart);
    expect(summary.dailyCompletionCounts, [1, 0, 0, 0, 2, 0, 0]);
    expect(summary.completedPracticeCount, 3);
    expect(summary.activeDayCount, 2);
    expect(summary.previousWeekCompletedPracticeCount, 1);
    expect(summary.lastPracticeAt, DateTime.utc(2026, 8, 11, 4));
    expect(summary.updatedAt, DateTime.utc(2026, 8, 11, 4, 30));
  });

  test('accepts a zero current week and missing optional totals', () {
    final data = baseData()
      ..['dailyCompletionCounts'] = [0, 0, 0, 0, 0, 0, 0]
      ..['completedPracticeCount'] = 0
      ..['activeDayCount'] = 0
      ..remove('previousWeekCompletedPracticeCount')
      ..remove('lastPracticeAt');

    final summary = ParentPracticeSummary.fromFirestore('student_a', data);

    expect(summary.completedPracticeCount, 0);
    expect(summary.activeDayCount, 0);
    expect(summary.previousWeekCompletedPracticeCount, isNull);
    expect(summary.lastPracticeAt, isNull);
  });

  test('rejects an unknown schema version', () {
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..['schemaVersion'] = 'u13-legacy',
      ),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects a missing or mismatched student id', () {
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..remove('studentId'),
      ),
      throwsA(isA<FormatException>()),
    );
    expect(
      () => ParentPracticeSummary.fromFirestore('student_b', baseData()),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects a wrong timezone', () {
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..['timezone'] = 'UTC',
      ),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects a missing weekStart', () {
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..remove('weekStart'),
      ),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects daily counts that are not exactly seven whole values', () {
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..['dailyCompletionCounts'] = [1, 2],
      ),
      throwsA(isA<FormatException>()),
    );
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..['dailyCompletionCounts'] = [1, 0, 0, 0, 0, 0, 0, 1],
      ),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects negative or fractional daily counts', () {
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..['dailyCompletionCounts'] = [-1, 0, 0, 0, 0, 0, 0],
      ),
      throwsA(isA<FormatException>()),
    );
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..['dailyCompletionCounts'] = [0.5, 0, 0, 0, 0, 0, 0],
      ),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects a completedPracticeCount inconsistent with the day counts', () {
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..['completedPracticeCount'] = 4,
      ),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects an activeDayCount inconsistent with the day counts', () {
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..['activeDayCount'] = 3,
      ),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects a negative or fractional previous-week total', () {
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..['previousWeekCompletedPracticeCount'] = -1,
      ),
      throwsA(isA<FormatException>()),
    );
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..['previousWeekCompletedPracticeCount'] = 1.5,
      ),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects invalid lastPracticeAt or missing updatedAt', () {
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..['lastPracticeAt'] = '2026-08-11',
      ),
      throwsA(isA<FormatException>()),
    );
    expect(
      () => ParentPracticeSummary.fromFirestore(
        'student_a',
        baseData()..remove('updatedAt'),
      ),
      throwsA(isA<FormatException>()),
    );
  });
}
