import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/adaptive_assignment.dart';
import 'package:logic_oasis/shared/models/forum_participation_summary.dart';
import 'package:logic_oasis/shared/models/parent_dashboard_snapshot.dart';
import 'package:logic_oasis/shared/models/quiz_attempt.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/models/trusted_subtopic_progress.dart';

class OasisProgressSnapshot {
  const OasisProgressSnapshot({
    this.yearLevel,
    this.crystals,
    this.mutualAidEnergy,
    this.language,
    this.missionReminders,
    this.eyeComfortMode,
    this.repairedAreas = const <String, double>{},
  });

  final int? yearLevel;
  final int? crystals;
  final int? mutualAidEnergy;
  final String? language;
  final bool? missionReminders;
  final bool? eyeComfortMode;
  final Map<String, double> repairedAreas;

  bool get isEmpty =>
      yearLevel == null &&
      crystals == null &&
      mutualAidEnergy == null &&
      language == null &&
      missionReminders == null &&
      eyeComfortMode == null &&
      repairedAreas.isEmpty;
}

class LearningRepository {
  LearningRepository({FirebaseFirestore? firestore})
    : _firestore = firestore ?? FirebaseFirestore.instance;

  final FirebaseFirestore _firestore;

  /// Loads only the student-readable completion projection written by trusted
  /// quiz finalization. This is a read path; clients never write this data.
  Future<List<TrustedSubtopicProgress>> fetchTrustedSubtopicProgress({
    required String studentId,
    required int yearLevel,
  }) async {
    final snapshot = await _firestore
        .collection('subtopicMastery')
        .where('studentId', isEqualTo: studentId)
        .where('yearLevel', isEqualTo: yearLevel.clamp(4, 6))
        .get(const GetOptions(source: Source.server));
    return snapshot.docs
        .map((document) {
          try {
            return TrustedSubtopicProgress.fromFirestore(document.data());
          } on FormatException {
            return null;
          }
        })
        .whereType<TrustedSubtopicProgress>()
        .toList(growable: false);
  }

  Future<void> saveQuizAttemptAndMastery({
    required String studentId,
    required QuizAttempt attempt,
    required int timeTakenSeconds,
    required int retryCount,
    required String difficultyLevel,
    required List<QuizAttempt> topicAttempts,
    int totalSubtopicCount = 0,
  }) async {
    final batch = _firestore.batch();
    final attemptRef = _firestore.collection('quizAttempts').doc(attempt.id);
    final masteryRef = _firestore
        .collection('topicMastery')
        .doc('${studentId}_y${attempt.yearLevel}_${attempt.topicId}');
    final subtopicMasteryRef = attempt.subtopicId == null
        ? null
        : _firestore
              .collection('subtopicMastery')
              .doc(
                '${studentId}_y${attempt.yearLevel}_${attempt.topicId}_${attempt.subtopicId}',
              );
    final subtopicAttempts = attempt.subtopicId == null
        ? const <QuizAttempt>[]
        : topicAttempts
              .where((item) => item.subtopicId == attempt.subtopicId)
              .toList();

    batch.set(
      attemptRef,
      buildQuizAttemptData(
        studentId: studentId,
        attempt: attempt,
        timeTakenSeconds: timeTakenSeconds,
        retryCount: retryCount,
        difficultyLevel: difficultyLevel,
      ),
      SetOptions(merge: true),
    );

    batch.set(
      masteryRef,
      buildTopicMasteryData(
        studentId: studentId,
        attempt: attempt,
        topicAttempts: topicAttempts,
        totalSubtopicCount: totalSubtopicCount,
      ),
      SetOptions(merge: true),
    );

    if (subtopicMasteryRef != null) {
      batch.set(
        subtopicMasteryRef,
        buildSubtopicMasteryData(
          studentId: studentId,
          attempt: attempt,
          subtopicAttempts: subtopicAttempts,
        ),
        SetOptions(merge: true),
      );
    }

    await batch.commit();
  }

  static Map<String, Object> buildQuizAttemptData({
    required String studentId,
    required QuizAttempt attempt,
    required int timeTakenSeconds,
    required int retryCount,
    required String difficultyLevel,
  }) {
    final totalQuestions = attempt.totalQuestions <= 0
        ? 1
        : attempt.totalQuestions;
    final correctCount = attempt.correctCount.clamp(0, totalQuestions);
    final wrongCount = totalQuestions - correctCount;
    final correctRate = correctCount / totalQuestions;

    return {
      'studentId': studentId,
      'topicId': attempt.topicId,
      'topicTitle': attempt.topicTitle,
      if (attempt.subtopicId != null) 'subtopicId': attempt.subtopicId!,
      if (attempt.subtopicTitle != null)
        'subtopicTitle': attempt.subtopicTitle!,
      'yearLevel': attempt.yearLevel,
      'score': attempt.score.clamp(0, 100),
      'correctRate': correctRate,
      'correctCount': correctCount,
      'totalQuestions': totalQuestions,
      'wrongCount': wrongCount,
      'timeTakenSeconds': timeTakenSeconds < 0 ? 0 : timeTakenSeconds,
      'retryCount': retryCount < 0 ? 0 : retryCount,
      'difficultyLevel': difficultyLevel,
      'masteryLevel': attempt.mastery,
      'earnedCrystals': attempt.earnedCrystals,
      'createdAt': Timestamp.fromDate(attempt.createdAt),
    };
  }

  static Map<String, Object> buildTopicMasteryData({
    required String studentId,
    required QuizAttempt attempt,
    required List<QuizAttempt> topicAttempts,
    int totalSubtopicCount = 0,
  }) {
    final orderedAttempts = _latestFirst(topicAttempts);
    final completedSubtopicCount = _completedSubtopicCount(orderedAttempts);
    final normalizedTotalSubtopics = totalSubtopicCount < completedSubtopicCount
        ? completedSubtopicCount
        : totalSubtopicCount;
    final averageScore = _averageScore(orderedAttempts);
    final progress = normalizedTotalSubtopics > 0
        ? completedSubtopicCount / normalizedTotalSubtopics
        : averageScore / 100;

    return {
      'studentId': studentId,
      'topicId': attempt.topicId,
      if (attempt.subtopicId != null) 'latestSubtopicId': attempt.subtopicId!,
      'yearLevel': attempt.yearLevel,
      'masteryLevel': _masteryForAverage(orderedAttempts),
      'averageScore': averageScore,
      'completedSubtopicCount': completedSubtopicCount,
      'totalSubtopicCount': normalizedTotalSubtopics,
      'progress': progress.clamp(0.0, 1.0),
      'recentTrend': _recentTrend(orderedAttempts),
      'attemptsCount': orderedAttempts.length,
      'updatedAt': FieldValue.serverTimestamp(),
    };
  }

  static Map<String, Object> buildSubtopicMasteryData({
    required String studentId,
    required QuizAttempt attempt,
    List<QuizAttempt> subtopicAttempts = const <QuizAttempt>[],
  }) {
    final orderedAttempts = _latestFirst(
      subtopicAttempts.isEmpty ? [attempt] : subtopicAttempts,
    );
    final bestCorrectRate = orderedAttempts
        .map(_correctRateForAttempt)
        .fold<double>(0, (best, rate) => rate > best ? rate : best);
    final completed =
        bestCorrectRate > 0.5 ||
        orderedAttempts.any(
          (item) => item.mastery == 'Moderate' || item.mastery == 'Strong',
        );

    return {
      'studentId': studentId,
      'topicId': attempt.topicId,
      'subtopicId': attempt.subtopicId ?? '',
      if (attempt.subtopicTitle != null)
        'subtopicTitle': attempt.subtopicTitle!,
      'yearLevel': attempt.yearLevel,
      'masteryLevel': _masteryForAverage(orderedAttempts),
      'averageScore': _averageScore(orderedAttempts),
      'bestCorrectRate': bestCorrectRate,
      'recentTrend': _recentTrend(orderedAttempts),
      'attemptsCount': orderedAttempts.length,
      'completed': completed,
      'unlocked': true,
      'updatedAt': FieldValue.serverTimestamp(),
    };
  }

  Future<void> saveOasisProgress({
    required String studentId,
    required int yearLevel,
    required int crystals,
    required int mutualAidEnergy,
    required String language,
    required bool missionReminders,
    required bool eyeComfortMode,
    required Map<String, double> repairedAreas,
  }) async {
    await _firestore.collection('oasisProgress').doc(studentId).set({
      'studentId': studentId,
      'yearLevel': yearLevel,
      'crystals': crystals,
      'mutualAidEnergy': mutualAidEnergy,
      'language': language,
      'missionReminders': missionReminders,
      'eyeComfortMode': eyeComfortMode,
      'repairedAreas': repairedAreas,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Future<OasisProgressSnapshot?> fetchOasisProgress({
    required String studentId,
  }) async {
    final progressDoc = await _firestore
        .collection('oasisProgress')
        .doc(studentId)
        .get();
    if (!progressDoc.exists) return null;

    final data = progressDoc.data();
    if (data == null) return null;

    return OasisProgressSnapshot(
      yearLevel: _intValue(data['yearLevel']),
      crystals: _intValue(data['crystals']),
      mutualAidEnergy: _intValue(data['mutualAidEnergy']),
      language: _stringValue(data['language']),
      missionReminders: _boolValue(data['missionReminders']),
      eyeComfortMode: _boolValue(data['eyeComfortMode']),
      repairedAreas: _doubleMapValue(data['repairedAreas'] ?? data['areas']),
    );
  }

  Future<ParentDashboardSnapshot> fetchParentDashboardSnapshot({
    required String studentId,
    required int yearLevel,
    required List<Topic> topics,
  }) async {
    final normalizedYearLevel = yearLevel.clamp(4, 6);
    // Parents are intentionally unable to read raw quiz attempts and raw AI
    // runs. Compose the dashboard entirely from the bounded U8 projections.
    final results = await Future.wait<Object>([
      _firestore
          .collection('studentAiStatuses')
          .where('studentId', isEqualTo: studentId)
          .get(const GetOptions(source: Source.server)),
      _firestore
          .collection('subtopicMastery')
          .where('studentId', isEqualTo: studentId)
          .where('yearLevel', isEqualTo: normalizedYearLevel)
          .get(const GetOptions(source: Source.server)),
      _firestore
          .collection('adaptiveAssignments')
          .where('studentId', isEqualTo: studentId)
          .get(const GetOptions(source: Source.server)),
      _firestore
          .collection('forumParticipationSummaries')
          .doc(studentId)
          .get(const GetOptions(source: Source.server)),
    ]);
    final statusSnapshot = results[0] as QuerySnapshot<Map<String, dynamic>>;
    final masterySnapshot = results[1] as QuerySnapshot<Map<String, dynamic>>;
    final assignmentSnapshot =
        results[2] as QuerySnapshot<Map<String, dynamic>>;
    final forumSnapshot = results[3] as DocumentSnapshot<Map<String, dynamic>>;
    final masteryByAttempt = <String, Map<String, dynamic>>{};
    for (final document in masterySnapshot.docs) {
      final data = document.data();
      final attemptId = data['lastSourceAttemptId'];
      if (attemptId is String && attemptId.isNotEmpty) {
        masteryByAttempt[attemptId] = data;
      }
    }
    final assignmentsByAttempt = <String, AdaptiveAssignment>{};
    for (final document in assignmentSnapshot.docs) {
      final data = document.data();
      final attemptId = data['sourceAttemptId'];
      if (attemptId is! String || attemptId.isEmpty) continue;
      try {
        assignmentsByAttempt[attemptId] = AdaptiveAssignment.fromFirestoreData(
          document.id,
          data,
        );
      } on FormatException {
        // A malformed projection is ignored rather than turned into advice.
      }
    }
    final aiDiagnoses =
        statusSnapshot.docs
            .map(
              (document) => AiDiagnosis.fromSafeProjection(
                document.id,
                document.data(),
                mastery: masteryByAttempt[document.id],
                assignment: assignmentsByAttempt[document.id],
              ),
            )
            .whereType<AiDiagnosis>()
            .where(
              (diagnosis) =>
                  diagnosis.yearLevel == null ||
                  diagnosis.yearLevel == normalizedYearLevel,
            )
            .toList()
          ..sort(
            (a, b) =>
                b.sourceAttemptSequence.compareTo(a.sourceAttemptSequence),
          );
    final masteryRecordCount = masterySnapshot.docs.length;

    return ParentDashboardSnapshot(
      attempts: const <QuizAttempt>[],
      masteryRecordCount: masteryRecordCount,
      aiDiagnoses: _latestDiagnosisPerTopic(aiDiagnoses),
      forumParticipationSummary:
          forumSnapshot.exists && forumSnapshot.data() != null
          ? ForumParticipationSummary.fromFirestore(
              studentId,
              forumSnapshot.data()!,
            )
          : null,
    );
  }

  List<AiDiagnosis> _latestDiagnosisPerTopic(List<AiDiagnosis> diagnoses) {
    final latestByTopic = <String, AiDiagnosis>{};
    for (final diagnosis in diagnoses) {
      final topicId = diagnosis.topicId;
      if (topicId.isEmpty) continue;
      final existing = latestByTopic[topicId];
      if (existing == null || diagnosis.isNewerThan(existing)) {
        latestByTopic[topicId] = diagnosis;
      }
    }
    return latestByTopic.values.toList(growable: false);
  }

  static List<QuizAttempt> _latestFirst(List<QuizAttempt> attempts) {
    return List<QuizAttempt>.from(attempts)
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
  }

  static int _averageScore(List<QuizAttempt> attempts) {
    if (attempts.isEmpty) return 0;
    final total = attempts.fold<int>(0, (sum, attempt) => sum + attempt.score);
    return (total / attempts.length).round();
  }

  static double _correctRateForAttempt(QuizAttempt attempt) {
    final totalQuestions = attempt.totalQuestions <= 0
        ? 1
        : attempt.totalQuestions;
    final correctCount = attempt.correctCount.clamp(0, totalQuestions);
    return correctCount / totalQuestions;
  }

  static int _completedSubtopicCount(List<QuizAttempt> attempts) {
    final completedSubtopicIds = <String>{};
    for (final attempt in attempts) {
      final subtopicId = attempt.subtopicId;
      if (subtopicId == null || subtopicId.isEmpty) continue;
      final correctRate = _correctRateForAttempt(attempt);
      if (correctRate > 0.5 ||
          attempt.mastery == 'Moderate' ||
          attempt.mastery == 'Strong') {
        completedSubtopicIds.add(subtopicId);
      }
    }
    return completedSubtopicIds.length;
  }

  static String _masteryForAverage(List<QuizAttempt> attempts) {
    final average = _averageScore(attempts);
    return _masteryForScore(average);
  }

  static String _masteryForScore(int score) {
    if (score >= 80) return 'Strong';
    if (score >= 50) return 'Moderate';
    return 'Weak';
  }

  static String _recentTrend(List<QuizAttempt> attempts) {
    if (attempts.length < 2) return 'stable';

    final latest = attempts[0].score;
    final previous = attempts[1].score;
    if (latest >= previous + 5) return 'improving';
    if (latest <= previous - 5) return 'declining';
    return 'stable';
  }

  int? _intValue(Object? value) {
    if (value is int) return value;
    if (value is num) return value.round();
    if (value is String) return int.tryParse(value);
    return null;
  }

  String? _stringValue(Object? value) {
    if (value is String && value.trim().isNotEmpty) return value;
    return null;
  }

  bool? _boolValue(Object? value) {
    if (value is bool) return value;
    return null;
  }

  Map<String, double> _doubleMapValue(Object? value) {
    if (value is! Map) return const <String, double>{};

    final parsed = <String, double>{};
    for (final entry in value.entries) {
      final key = entry.key;
      final progress = entry.value;
      if (key is String && progress is num) {
        parsed[key] = progress.toDouble().clamp(0.0, 1.0);
      }
    }
    return parsed;
  }
}
