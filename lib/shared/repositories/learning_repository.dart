import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/parent_dashboard_snapshot.dart';
import 'package:logic_oasis/shared/models/quiz_attempt.dart';
import 'package:logic_oasis/shared/models/topic.dart';

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
    final attemptsSnapshot = await _firestore
        .collection('quizAttempts')
        .where('studentId', isEqualTo: studentId)
        .get(const GetOptions(source: Source.server));
    final masterySnapshot = await _firestore
        .collection('topicMastery')
        .where('studentId', isEqualTo: studentId)
        .get(const GetOptions(source: Source.server));
    final aiSnapshot = await _firestore
        .collection('aiModelRuns')
        .where('studentId', isEqualTo: studentId)
        .get(const GetOptions(source: Source.server));

    final topicTitles = {for (final topic in topics) topic.id: topic.title};
    final topicYearLevels = {
      for (final topic in topics) topic.id: topic.yearLevel,
    };

    final attempts =
        attemptsSnapshot.docs
            .map(
              (doc) => _attemptFromData(
                doc.id,
                doc.data(),
                topicTitles,
                topicYearLevels,
              ),
            )
            .whereType<QuizAttempt>()
            .where((attempt) => attempt.yearLevel == normalizedYearLevel)
            .toList()
          ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    final aiDiagnoses =
        aiSnapshot.docs
            .map((doc) => AiDiagnosis.fromFirestore(doc.id, doc.data()))
            .whereType<AiDiagnosis>()
            .where(
              (diagnosis) =>
                  diagnosis.yearLevel == null ||
                  diagnosis.yearLevel == normalizedYearLevel,
            )
            .toList()
          ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    final masteryRecordCount = masterySnapshot.docs.where((doc) {
      final data = doc.data();
      final recordYearLevel =
          _intValue(data['yearLevel']) ??
          _yearFromTopicId(data['topicId'] as String?);
      return recordYearLevel == null || recordYearLevel == normalizedYearLevel;
    }).length;

    return ParentDashboardSnapshot(
      attempts: attempts,
      masteryRecordCount: masteryRecordCount,
      aiDiagnoses: _latestDiagnosisPerTopic(aiDiagnoses),
    );
  }

  List<AiDiagnosis> _latestDiagnosisPerTopic(List<AiDiagnosis> diagnoses) {
    final latestByTopic = <String, AiDiagnosis>{};
    for (final diagnosis in diagnoses) {
      final existing = latestByTopic[diagnosis.topicId];
      if (existing == null || diagnosis.isNewerThan(existing)) {
        latestByTopic[diagnosis.topicId] = diagnosis;
      }
    }
    return latestByTopic.values.toList(growable: false);
  }

  QuizAttempt? _attemptFromData(
    String id,
    Map<String, dynamic> data,
    Map<String, String> topicTitles,
    Map<String, int> topicYearLevels,
  ) {
    final topicId = data['topicId'];
    final score = data['score'];
    final correctCount = data['correctCount'];
    final totalQuestions = data['totalQuestions'];

    if (topicId is! String ||
        score is! num ||
        correctCount is! num ||
        totalQuestions is! num) {
      return null;
    }

    final createdAt = data['createdAt'];
    final topicTitle = data['topicTitle'];
    final subtopicId = data['subtopicId'];
    final subtopicTitle = data['subtopicTitle'];
    final yearLevel =
        _intValue(data['yearLevel']) ??
        topicYearLevels[topicId] ??
        _yearFromTopicId(topicId) ??
        4;
    final mastery = data['masteryLevel'] ?? data['mastery'];
    final earnedCrystals = data['earnedCrystals'];

    return QuizAttempt(
      id: id,
      topicId: topicId,
      topicTitle: topicTitle is String && topicTitle.isNotEmpty
          ? topicTitle
          : topicTitles[topicId] ?? topicId,
      subtopicId: subtopicId is String && subtopicId.isNotEmpty
          ? subtopicId
          : null,
      subtopicTitle: subtopicTitle is String && subtopicTitle.isNotEmpty
          ? subtopicTitle
          : null,
      yearLevel: yearLevel.clamp(4, 6),
      score: score.round(),
      correctCount: correctCount.round(),
      totalQuestions: totalQuestions.round(),
      earnedCrystals: earnedCrystals is num ? earnedCrystals.round() : 0,
      mastery: mastery is String && mastery.isNotEmpty
          ? mastery
          : _masteryForScore(score.round()),
      createdAt: createdAt is Timestamp ? createdAt.toDate() : DateTime.now(),
    );
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

  int? _yearFromTopicId(String? topicId) {
    if (topicId == null) return null;
    final match = RegExp(r'(?:^|_)y([456])(?:_|$)').firstMatch(topicId);
    return match == null ? null : int.tryParse(match.group(1)!);
  }
}
