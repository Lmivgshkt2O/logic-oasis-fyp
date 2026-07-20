import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/models/quiz_attempt.dart';
import 'package:logic_oasis/shared/repositories/learning_repository.dart';

void main() {
  final createdAt = DateTime(2026, 7, 2, 14, 5);

  QuizAttempt attempt({
    required String id,
    required int score,
    required int correctCount,
    required DateTime createdAt,
    String topicId = 'fractions_y4',
    String? subtopicId,
    String? subtopicTitle,
    int yearLevel = 4,
  }) {
    return QuizAttempt(
      id: id,
      topicId: topicId,
      topicTitle: 'Fractions',
      subtopicId: subtopicId,
      subtopicTitle: subtopicTitle,
      yearLevel: yearLevel,
      score: score,
      correctCount: correctCount,
      totalQuestions: 5,
      earnedCrystals: 30,
      mastery: score >= 80
          ? 'Strong'
          : score >= 50
          ? 'Moderate'
          : 'Weak',
      createdAt: createdAt,
    );
  }

  test('quiz attempt payload stores the AI pipeline source fields', () {
    final payload = LearningRepository.buildQuizAttemptData(
      studentId: 'student_aiman_y4',
      attempt: attempt(
        id: 'attempt_001',
        score: 60,
        correctCount: 3,
        createdAt: createdAt,
      ),
      timeTakenSeconds: 125,
      retryCount: 1,
      difficultyLevel: 'Mixed',
    );

    expect(payload['studentId'], 'student_aiman_y4');
    expect(payload['topicId'], 'fractions_y4');
    expect(payload['score'], 60);
    expect(payload['correctRate'], 0.6);
    expect(payload['timeTakenSeconds'], 125);
    expect(payload['yearLevel'], 4);
    expect(payload['createdAt'], isA<Timestamp>());
    expect(payload['correctCount'], 3);
    expect(payload['totalQuestions'], 5);
    expect(payload['wrongCount'], 2);
    expect(payload['retryCount'], 1);
    expect(payload['difficultyLevel'], 'Mixed');
  });

  test('quiz attempt payload clamps invalid counts and timing', () {
    final payload = LearningRepository.buildQuizAttemptData(
      studentId: 'student_aiman_y4',
      attempt: attempt(
        id: 'attempt_002',
        score: 140,
        correctCount: 8,
        createdAt: createdAt,
      ),
      timeTakenSeconds: -4,
      retryCount: -1,
      difficultyLevel: 'Mixed',
    );

    expect(payload['score'], 100);
    expect(payload['correctRate'], 1.0);
    expect(payload['correctCount'], 5);
    expect(payload['wrongCount'], 0);
    expect(payload['timeTakenSeconds'], 0);
    expect(payload['retryCount'], 0);
  });

  test('quiz attempt payload includes subtopic data when present', () {
    final payload = LearningRepository.buildQuizAttemptData(
      studentId: 'student_aiman_y4',
      attempt: attempt(
        id: 'attempt_subtopic',
        score: 80,
        correctCount: 4,
        createdAt: createdAt,
        subtopicId: 'equivalent_fractions',
        subtopicTitle: 'Equivalent Fractions',
      ),
      timeTakenSeconds: 45,
      retryCount: 0,
      difficultyLevel: 'Easy',
    );

    expect(payload['subtopicId'], 'equivalent_fractions');
    expect(payload['subtopicTitle'], 'Equivalent Fractions');
  });

  test('subtopic mastery payload marks correct rate above 50 percent complete', () {
    final payload = LearningRepository.buildSubtopicMasteryData(
      studentId: 'student_aiman_y4',
      attempt: attempt(
        id: 'attempt_percentages',
        topicId: 'percentages_y4',
        subtopicId: 'percentage_meaning',
        subtopicTitle: 'Meaning of Percentage',
        score: 60,
        correctCount: 3,
        createdAt: createdAt,
      ),
    );

    expect(payload['subtopicId'], 'percentage_meaning');
    expect(payload['bestCorrectRate'], 0.6);
    expect(payload['completed'], isTrue);
  });

  test('subtopic mastery payload keeps best completion after weaker retry', () {
    final passed = attempt(
      id: 'attempt_subtopic_passed',
      topicId: 'whole_numbers_y4',
      subtopicId: 'read_write_numbers',
      subtopicTitle: 'Read and Write Numbers',
      score: 60,
      correctCount: 3,
      createdAt: createdAt,
    );
    final retry = attempt(
      id: 'attempt_subtopic_retry',
      topicId: 'whole_numbers_y4',
      subtopicId: 'read_write_numbers',
      subtopicTitle: 'Read and Write Numbers',
      score: 20,
      correctCount: 1,
      createdAt: createdAt.add(const Duration(minutes: 8)),
    );

    final payload = LearningRepository.buildSubtopicMasteryData(
      studentId: 'student_aiman_y4',
      attempt: retry,
      subtopicAttempts: [passed, retry],
    );

    expect(payload['masteryLevel'], 'Weak');
    expect(payload['averageScore'], 40);
    expect(payload['bestCorrectRate'], 0.6);
    expect(payload['recentTrend'], 'declining');
    expect(payload['attemptsCount'], 2);
    expect(payload['completed'], isTrue);
  });

  test('topic mastery payload updates after first and repeated attempts', () {
    final first = attempt(
      id: 'attempt_001',
      score: 40,
      correctCount: 2,
      createdAt: createdAt,
    );
    final retry = attempt(
      id: 'attempt_002',
      score: 80,
      correctCount: 4,
      createdAt: createdAt.add(const Duration(minutes: 8)),
    );

    final firstPayload = LearningRepository.buildTopicMasteryData(
      studentId: 'student_aiman_y4',
      attempt: first,
      topicAttempts: [first],
    );
    final retryPayload = LearningRepository.buildTopicMasteryData(
      studentId: 'student_aiman_y4',
      attempt: retry,
      topicAttempts: [first, retry],
    );

    expect(firstPayload['masteryLevel'], 'Weak');
    expect(firstPayload['averageScore'], 40);
    expect(firstPayload['completedSubtopicCount'], 0);
    expect(firstPayload['totalSubtopicCount'], 0);
    expect(firstPayload['progress'], 0.4);
    expect(firstPayload['recentTrend'], 'stable');
    expect(firstPayload['attemptsCount'], 1);

    expect(retryPayload['masteryLevel'], 'Moderate');
    expect(retryPayload['averageScore'], 60);
    expect(retryPayload['completedSubtopicCount'], 0);
    expect(retryPayload['totalSubtopicCount'], 0);
    expect(retryPayload['progress'], 0.6);
    expect(retryPayload['recentTrend'], 'improving');
    expect(retryPayload['attemptsCount'], 2);
    expect(retryPayload.containsKey('aiModelRuns'), isFalse);
    expect(retryPayload.containsKey('bktMasteryProbability'), isFalse);
    expect(retryPayload['updatedAt'], isA<FieldValue>());
  });

  test('topic mastery payload is isolated per switched topic', () {
    final fractions = attempt(
      id: 'attempt_fractions',
      score: 80,
      correctCount: 4,
      createdAt: createdAt,
    );
    final decimals = attempt(
      id: 'attempt_decimals',
      score: 20,
      correctCount: 1,
      createdAt: createdAt.add(const Duration(minutes: 5)),
      topicId: 'decimals_y4',
    );

    final payload = LearningRepository.buildTopicMasteryData(
      studentId: 'student_aiman_y4',
      attempt: decimals,
      topicAttempts: [decimals],
    );

    expect(fractions.topicId, 'fractions_y4');
    expect(payload['topicId'], 'decimals_y4');
    expect(payload['averageScore'], 20);
    expect(payload['masteryLevel'], 'Weak');
  });

  test('topic mastery payload rolls up completed subtopics', () {
    final readWrite = attempt(
      id: 'attempt_read_write',
      topicId: 'whole_numbers_y4',
      subtopicId: 'read_write_numbers',
      score: 60,
      correctCount: 3,
      createdAt: createdAt,
    );
    final placeValue = attempt(
      id: 'attempt_place_value',
      topicId: 'whole_numbers_y4',
      subtopicId: 'place_digit_value',
      score: 40,
      correctCount: 2,
      createdAt: createdAt.add(const Duration(minutes: 5)),
    );
    final retryReadWrite = attempt(
      id: 'attempt_read_write_retry',
      topicId: 'whole_numbers_y4',
      subtopicId: 'read_write_numbers',
      score: 20,
      correctCount: 1,
      createdAt: createdAt.add(const Duration(minutes: 10)),
    );

    final payload = LearningRepository.buildTopicMasteryData(
      studentId: 'student_aiman_y4',
      attempt: retryReadWrite,
      topicAttempts: [readWrite, placeValue, retryReadWrite],
      totalSubtopicCount: 5,
    );

    expect(payload['latestSubtopicId'], 'read_write_numbers');
    expect(payload['completedSubtopicCount'], 1);
    expect(payload['totalSubtopicCount'], 5);
    expect(payload['progress'], 0.2);
    expect(payload['attemptsCount'], 3);
    expect(payload['recentTrend'], 'declining');
  });
}
