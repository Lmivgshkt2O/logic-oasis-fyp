import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/models/forum_participation_summary.dart';
import 'package:logic_oasis/shared/models/parent_dashboard_snapshot.dart';
import 'package:logic_oasis/shared/models/parent_practice_summary.dart';
import 'package:logic_oasis/shared/models/quiz_attempt.dart';
import 'package:logic_oasis/shared/models/trusted_subtopic_progress.dart';
import 'package:logic_oasis/shared/repositories/learning_repository.dart';

const parentStudentId = 'student_a';

Map<String, dynamic> masteryData({String subtopicId = 'read_write_numbers'}) {
  return {
    'studentId': parentStudentId,
    'topicId': 'whole_numbers_y4',
    'subtopicId': subtopicId,
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
}

Map<String, dynamic> practiceData({String? student = parentStudentId}) {
  return {
    'schemaVersion': parentPracticeSummarySchemaVersion,
    'studentId': student,
    'timezone': parentPracticeTimezone,
    'weekStart': Timestamp.fromDate(DateTime.utc(2026, 8, 9, 16)),
    'dailyCompletionCounts': [1, 0, 0, 0, 2, 0, 0],
    'completedPracticeCount': 3,
    'activeDayCount': 2,
    'updatedAt': Timestamp.fromDate(DateTime.utc(2026, 8, 11, 4)),
  };
}

Map<String, dynamic> forumData({String? student = parentStudentId}) {
  return {
    'studentId': student,
    'weekStart': Timestamp.fromDate(DateTime.utc(2026, 8, 9, 16)),
    'questionsPostedCount': 1,
    'answersSubmittedCount': 2,
    'acceptedAnswersCount': 1,
    'helpfulReceivedCount': 0,
    'updatedAt': Timestamp.fromDate(DateTime.utc(2026, 8, 10, 3)),
  };
}

class _FakeFirestore implements FirebaseFirestore {
  _FakeFirestore(this.documents);

  /// collection name -> document id -> raw map.
  final Map<String, Map<String, Map<String, dynamic>>> documents;
  final List<String> accessedCollections = [];

  /// Key is a collection name (query reads) or `collection/doc` (document
  /// reads). A value here is thrown when that read is attempted.
  final Map<String, Object> readErrors = {};

  @override
  dynamic noSuchMethod(Invocation invocation) {
    if (invocation.memberName == #collection) {
      final path = invocation.positionalArguments.single as String;
      accessedCollections.add(path);
      return _FakeCollectionReference(
        path,
        documents.putIfAbsent(path, () => <String, Map<String, dynamic>>{}),
        readErrors,
      );
    }
    return super.noSuchMethod(invocation);
  }
}

// The Firestore interfaces are analyzer-sealed, so a focused test fake may
// not implement them without a suppression; the fake is never shipped.
// ignore: subtype_of_sealed_class
class _FakeCollectionReference
    implements CollectionReference<Map<String, dynamic>> {
  _FakeCollectionReference(this.path, this.documents, this.readErrors);

  final String path;
  final Map<String, Map<String, dynamic>> documents;
  final Map<String, Object> readErrors;

  @override
  _FakeDocumentReference doc([String? path]) {
    return _FakeDocumentReference(this.path, path!, documents, readErrors);
  }

  @override
  _FakeQuery where(
    Object field, {
    Object? isEqualTo,
    Object? isNotEqualTo,
    Object? isLessThan,
    Object? isLessThanOrEqualTo,
    Object? isGreaterThan,
    Object? isGreaterThanOrEqualTo,
    Object? arrayContains,
    Iterable<Object?>? arrayContainsAny,
    Iterable<Object?>? whereIn,
    Iterable<Object?>? whereNotIn,
    bool? isNull,
  }) {
    return _FakeQuery(path, documents, readErrors, [(field, isEqualTo)]);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) {
    if (invocation.memberName == #snapshots) {
      return Stream<QuerySnapshot<Map<String, dynamic>>>.fromFuture(get());
    }
    return super.noSuchMethod(invocation);
  }
}

// ignore: subtype_of_sealed_class
class _FakeQuery implements Query<Map<String, dynamic>> {
  _FakeQuery(this.path, this.documents, this.readErrors, this.conditions);

  final String path;
  final Map<String, Map<String, dynamic>> documents;
  final Map<String, Object> readErrors;
  final List<(Object, Object?)> conditions;

  @override
  _FakeQuery where(
    Object field, {
    Object? isEqualTo,
    Object? isNotEqualTo,
    Object? isLessThan,
    Object? isLessThanOrEqualTo,
    Object? isGreaterThan,
    Object? isGreaterThanOrEqualTo,
    Object? arrayContains,
    Iterable<Object?>? arrayContainsAny,
    Iterable<Object?>? whereIn,
    Iterable<Object?>? whereNotIn,
    bool? isNull,
  }) {
    return _FakeQuery(path, documents, readErrors, [
      ...conditions,
      (field, isEqualTo),
    ]);
  }

  @override
  Future<QuerySnapshot<Map<String, dynamic>>> get([GetOptions? options]) async {
    final error = readErrors[path];
    if (error != null) throw error;
    final docs = documents.values
        .where(
          (data) => conditions.every(
            (condition) => data[condition.$1 as String] == condition.$2,
          ),
        )
        .map((data) => _FakeQueryDocumentSnapshot(data))
        .toList(growable: false);
    return _FakeQuerySnapshot(docs);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) {
    if (invocation.memberName == #snapshots) {
      return Stream<QuerySnapshot<Map<String, dynamic>>>.fromFuture(get());
    }
    return super.noSuchMethod(invocation);
  }
}

class _FakeQuerySnapshot implements QuerySnapshot<Map<String, dynamic>> {
  _FakeQuerySnapshot(this.docs);

  @override
  final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ignore: subtype_of_sealed_class
class _FakeQueryDocumentSnapshot
    implements QueryDocumentSnapshot<Map<String, dynamic>> {
  _FakeQueryDocumentSnapshot(this._raw);

  final Map<String, dynamic> _raw;

  @override
  Map<String, dynamic> data() => _raw;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ignore: subtype_of_sealed_class
class _FakeDocumentReference
    implements DocumentReference<Map<String, dynamic>> {
  _FakeDocumentReference(
    this.collectionPath,
    this.documentPath,
    this.documents,
    this.readErrors,
  );

  final String collectionPath;
  final String documentPath;
  final Map<String, Map<String, dynamic>> documents;
  final Map<String, Object> readErrors;

  @override
  dynamic noSuchMethod(Invocation invocation) {
    if (invocation.memberName == #get) {
      final error = readErrors['$collectionPath/$documentPath'];
      if (error != null) throw error;
      return Future<DocumentSnapshot<Map<String, dynamic>>>.value(
        _FakeDocumentSnapshot(documents[documentPath]),
      );
    }
    if (invocation.memberName == #snapshots) {
      final error = readErrors['$collectionPath/$documentPath'];
      if (error != null) {
        return Stream<DocumentSnapshot<Map<String, dynamic>>>.error(error);
      }
      return Stream<DocumentSnapshot<Map<String, dynamic>>>.value(
        _FakeDocumentSnapshot(documents[documentPath]),
      );
    }
    return super.noSuchMethod(invocation);
  }
}

// ignore: subtype_of_sealed_class
class _FakeDocumentSnapshot implements DocumentSnapshot<Map<String, dynamic>> {
  _FakeDocumentSnapshot(this._raw);

  final Map<String, dynamic>? _raw;

  @override
  bool get exists => _raw != null;

  @override
  Map<String, dynamic>? data() => _raw;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

const forbiddenParentCollections = <String>[
  'studentAiStatuses',
  'adaptiveAssignments',
  'quizAttempts',
  'questionResponses',
  'aiJobs',
  'aiModelRuns',
  'forumQuestions',
  'forumAnswers',
];

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

  test(
    'subtopic mastery payload marks correct rate above 50 percent complete',
    () {
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
    },
  );

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

  group('fetchParentDashboardSnapshot safe assembly', () {
    test('watch assembles the three allowlisted live projections', () async {
      final fake = _FakeFirestore({
        'subtopicMastery': {'a_read_write': masteryData()},
        'parentPracticeSummaries': {parentStudentId: practiceData()},
        'forumParticipationSummaries': {parentStudentId: forumData()},
      });
      final repository = LearningRepository(firestore: fake);

      final snapshot = await repository
          .watchParentDashboardSnapshot(
            studentId: parentStudentId,
            yearLevel: 4,
          )
          .first;

      expect(snapshot.mastery, hasLength(1));
      expect(snapshot.practiceSummary?.completedPracticeCount, 3);
      expect(snapshot.forumParticipationSummary?.answersSubmittedCount, 2);
      for (final collection in forbiddenParentCollections) {
        expect(fake.accessedCollections, isNot(contains(collection)));
      }
    });

    test('watch surfaces permission denial as an auth failure', () async {
      final fake = _FakeFirestore({
        'subtopicMastery': {'a_read_write': masteryData()},
        'parentPracticeSummaries': {parentStudentId: practiceData()},
      });
      fake.readErrors['forumParticipationSummaries/$parentStudentId'] =
          FirebaseException(
            code: 'permission-denied',
            message: 'Missing or insufficient permissions.',
            plugin: 'cloud_firestore',
          );
      final repository = LearningRepository(firestore: fake);

      await expectLater(
        repository.watchParentDashboardSnapshot(
          studentId: parentStudentId,
          yearLevel: 4,
        ),
        emitsError(isA<ParentDashboardAuthException>()),
      );
    });

    test(
      'assembles only typed safe card inputs from the allowlisted reads',
      () async {
        final fake = _FakeFirestore({
          'subtopicMastery': {
            'a_read_write': masteryData(),
            'a_place_value': masteryData(subtopicId: 'place_digit_value'),
            // Malformed probability (> 1) must be omitted, not turned into
            // advice.
            'a_bad': {...masteryData(), 'masteryProbability': 7},
          },
          'parentPracticeSummaries': {parentStudentId: practiceData()},
          'forumParticipationSummaries': {parentStudentId: forumData()},
        });
        final repository = LearningRepository(firestore: fake);

        final snapshot = await repository.fetchParentDashboardSnapshot(
          studentId: parentStudentId,
          yearLevel: 4,
          topics: const [],
        );

        expect(snapshot.mastery, hasLength(2));
        expect(snapshot.mastery!.first, isA<TrustedSubtopicProgress>());
        expect(snapshot.practiceSummary, isA<ParentPracticeSummary>());
        expect(snapshot.practiceSummary?.completedPracticeCount, 3);
        expect(
          snapshot.forumParticipationSummary,
          isA<ForumParticipationSummary>(),
        );
        expect(snapshot.forumParticipationSummary?.answersSubmittedCount, 2);
        expect(
          fake.accessedCollections,
          containsAll(<String>[
            'subtopicMastery',
            'parentPracticeSummaries',
            'forumParticipationSummaries',
          ]),
        );
        for (final collection in forbiddenParentCollections) {
          expect(fake.accessedCollections, isNot(contains(collection)));
        }
      },
    );

    test('missing practice or forum documents leave independent unavailable '
        'cards while valid Understanding remains', () async {
      final fake = _FakeFirestore({
        'subtopicMastery': {'a_read_write': masteryData()},
      });
      final repository = LearningRepository(firestore: fake);

      final snapshot = await repository.fetchParentDashboardSnapshot(
        studentId: parentStudentId,
        yearLevel: 4,
        topics: const [],
      );

      expect(snapshot.mastery, hasLength(1));
      expect(snapshot.practiceSummary, isNull);
      expect(snapshot.forumParticipationSummary, isNull);
    });

    test('a non-auth read failure keeps the other cards available', () async {
      final fake = _FakeFirestore({
        'subtopicMastery': {'a_read_write': masteryData()},
        'forumParticipationSummaries': {parentStudentId: forumData()},
      });
      fake.readErrors['parentPracticeSummaries/$parentStudentId'] =
          FirebaseException(
            code: 'unavailable',
            message: 'network down',
            plugin: 'cloud_firestore',
          );
      final repository = LearningRepository(firestore: fake);

      final snapshot = await repository.fetchParentDashboardSnapshot(
        studentId: parentStudentId,
        yearLevel: 4,
        topics: const [],
      );

      expect(snapshot.mastery, hasLength(1));
      expect(snapshot.practiceSummary, isNull);
      expect(snapshot.forumParticipationSummary, isNotNull);
    });

    test(
      'permission denial clears the whole snapshot as an auth failure',
      () async {
        final fake = _FakeFirestore({
          'subtopicMastery': {'a_read_write': masteryData()},
          'parentPracticeSummaries': {parentStudentId: practiceData()},
        });
        fake.readErrors['forumParticipationSummaries/$parentStudentId'] =
            FirebaseException(
              code: 'permission-denied',
              message: 'Missing or insufficient permissions.',
              plugin: 'cloud_firestore',
            );
        final repository = LearningRepository(firestore: fake);

        await expectLater(
          repository.fetchParentDashboardSnapshot(
            studentId: parentStudentId,
            yearLevel: 4,
            topics: const [],
          ),
          throwsA(isA<ParentDashboardAuthException>()),
        );
      },
    );

    test(
      'a selected-child identity mismatch is a whole-snapshot auth failure',
      () async {
        final fake = _FakeFirestore({
          'subtopicMastery': {'a_read_write': masteryData()},
          'parentPracticeSummaries': {
            parentStudentId: practiceData(student: 'other_student'),
          },
        });
        final repository = LearningRepository(firestore: fake);

        await expectLater(
          repository.fetchParentDashboardSnapshot(
            studentId: parentStudentId,
            yearLevel: 4,
            topics: const [],
          ),
          throwsA(isA<ParentDashboardAuthException>()),
        );
      },
    );

    test(
      'a malformed practice document is unavailable, never advice',
      () async {
        final fake = _FakeFirestore({
          'subtopicMastery': {'a_read_write': masteryData()},
          'parentPracticeSummaries': {
            parentStudentId: practiceData()..['schemaVersion'] = 'u13-legacy',
          },
        });
        final repository = LearningRepository(firestore: fake);

        final snapshot = await repository.fetchParentDashboardSnapshot(
          studentId: parentStudentId,
          yearLevel: 4,
          topics: const [],
        );

        expect(snapshot.mastery, hasLength(1));
        expect(snapshot.practiceSummary, isNull);
      },
    );
  });
}
