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
  }) async {
    final batch = _firestore.batch();
    final attemptRef = _firestore.collection('quizAttempts').doc(attempt.id);
    final masteryRef = _firestore
        .collection('topicMastery')
        .doc('${studentId}_y${attempt.yearLevel}_${attempt.topicId}');

    final correctRate = attempt.totalQuestions == 0
        ? 0.0
        : attempt.correctCount / attempt.totalQuestions;

    batch.set(attemptRef, {
      'studentId': studentId,
      'topicId': attempt.topicId,
      'topicTitle': attempt.topicTitle,
      'yearLevel': attempt.yearLevel,
      'score': attempt.score,
      'correctRate': correctRate,
      'correctCount': attempt.correctCount,
      'totalQuestions': attempt.totalQuestions,
      'wrongCount': attempt.totalQuestions - attempt.correctCount,
      'timeTakenSeconds': timeTakenSeconds,
      'retryCount': retryCount,
      'difficultyLevel': difficultyLevel,
      'masteryLevel': attempt.mastery,
      'earnedCrystals': attempt.earnedCrystals,
      'createdAt': Timestamp.fromDate(attempt.createdAt),
    }, SetOptions(merge: true));

    batch.set(masteryRef, {
      'studentId': studentId,
      'topicId': attempt.topicId,
      'yearLevel': attempt.yearLevel,
      'masteryLevel': _masteryForAverage(topicAttempts),
      'averageScore': _averageScore(topicAttempts),
      'recentTrend': _recentTrend(topicAttempts),
      'attemptsCount': topicAttempts.length,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    await batch.commit();
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
        .get();
    final masterySnapshot = await _firestore
        .collection('topicMastery')
        .where('studentId', isEqualTo: studentId)
        .get();
    final aiSnapshot = await _firestore
        .collection('aiModelRuns')
        .where('studentId', isEqualTo: studentId)
        .get();

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
      latestByTopic.putIfAbsent(diagnosis.topicId, () => diagnosis);
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

  int _averageScore(List<QuizAttempt> attempts) {
    if (attempts.isEmpty) return 0;
    final total = attempts.fold<int>(0, (sum, attempt) => sum + attempt.score);
    return (total / attempts.length).round();
  }

  String _masteryForAverage(List<QuizAttempt> attempts) {
    final average = _averageScore(attempts);
    return _masteryForScore(average);
  }

  String _masteryForScore(int score) {
    if (score >= 80) return 'Strong';
    if (score >= 50) return 'Moderate';
    return 'Weak';
  }

  String _recentTrend(List<QuizAttempt> attempts) {
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
