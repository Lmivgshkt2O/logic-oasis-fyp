import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/models/trusted_subtopic_progress.dart';

void main() {
  Map<String, dynamic> baseData() => {
    'studentId': 'student_a',
    'topicId': 'whole_numbers_y4',
    'subtopicId': 'read_write_numbers',
    'yearLevel': 4,
    'completed': true,
    'masteryLevel': 'Moderate',
    'bestCorrectRate': 0.6,
    'attempted': true,
    'accessUnlocked': true,
    'masteryProbability': 0.55,
    'evidenceLevel': 'established',
    'observationCount': 3,
    'updatedAt': Timestamp.fromDate(DateTime.utc(2026, 8, 1, 8)),
  };

  test('parses observation count and updatedAt when present', () {
    final record = TrustedSubtopicProgress.fromFirestore(baseData());

    expect(record.observationCount, 3);
    expect(record.updatedAt, DateTime.utc(2026, 8, 1, 8));
  });

  test('accepts a whole numeric observation count', () {
    final data = baseData()..['observationCount'] = 3.0;

    expect(TrustedSubtopicProgress.fromFirestore(data).observationCount, 3);
  });

  test(
    'missing observationCount and updatedAt stay null for older documents',
    () {
      final data = baseData()
        ..remove('observationCount')
        ..remove('updatedAt');

      final record = TrustedSubtopicProgress.fromFirestore(data);

      expect(record.observationCount, isNull);
      expect(record.updatedAt, isNull);
    },
  );

  test('rejects negative or fractional observation counts', () {
    expect(
      () => TrustedSubtopicProgress.fromFirestore(
        baseData()..['observationCount'] = -1,
      ),
      throwsA(isA<FormatException>()),
    );
    expect(
      () => TrustedSubtopicProgress.fromFirestore(
        baseData()..['observationCount'] = 2.5,
      ),
      throwsA(isA<FormatException>()),
    );
  });

  test('rejects a non-timestamp updatedAt value', () {
    expect(
      () => TrustedSubtopicProgress.fromFirestore(
        baseData()..['updatedAt'] = '2026-08-01',
      ),
      throwsA(isA<FormatException>()),
    );
  });

  test('keeps required-field strictness for the existing contract', () {
    expect(
      () => TrustedSubtopicProgress.fromFirestore(
        baseData()..['yearLevel'] = 4.5,
      ),
      throwsA(isA<FormatException>()),
    );
    expect(
      () => TrustedSubtopicProgress.fromFirestore(
        baseData()..remove('completed'),
      ),
      throwsA(isA<FormatException>()),
    );
    expect(
      () => TrustedSubtopicProgress.fromFirestore(
        baseData()..['masteryLevel'] = 'Expert',
      ),
      throwsA(isA<FormatException>()),
    );
  });
}
