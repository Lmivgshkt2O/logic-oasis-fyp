import 'package:flutter/material.dart';
import 'package:logic_oasis/shared/models/oasis_area.dart';
import 'package:logic_oasis/shared/models/quiz_attempt.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';
import 'package:logic_oasis/shared/models/recommended_mission.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/models/weak_topic_insight.dart';

class AppState extends ChangeNotifier {
  static const String recommendedMissionTopicId = 'fractions_y4';
  static const int recommendedMissionRequiredCompletions = 2;
  static const int recommendedMissionRewardCrystals = 20;

  final List<Topic> topics = [
    const Topic(
      id: 'fractions_y4',
      title: 'Fractions',
      titleBm: 'Pecahan',
      area: 'Understand and compare fractions',
      progress: 0.72,
      mastery: 'Strong',
      questions: [
        QuizQuestion(
          question: 'Which fraction is equal to 1/2?',
          options: ['1/4', '2/4', '3/4', '4/4'],
          answerIndex: 1,
          explanation: '2/4 can be simplified by dividing both numbers by 2.',
        ),
        QuizQuestion(
          question: 'Which fraction is larger?',
          options: ['1/3', '1/5', '1/8', '1/10'],
          answerIndex: 0,
          explanation: 'For unit fractions, the smaller denominator is larger.',
        ),
        QuizQuestion(
          question: 'What is 1/4 + 1/4?',
          options: ['1/8', '1/4', '1/2', '1'],
          answerIndex: 2,
          explanation:
              'One quarter plus one quarter makes two quarters, or 1/2.',
        ),
        QuizQuestion(
          question: 'Which shows three out of four equal parts?',
          options: ['1/4', '2/4', '3/4', '4/3'],
          answerIndex: 2,
          explanation: '3/4 means three selected parts from four equal parts.',
        ),
        QuizQuestion(
          question: 'What is 2/6 simplified?',
          options: ['1/2', '1/3', '2/3', '3/6'],
          answerIndex: 1,
          explanation: 'Divide 2 and 6 by 2. The answer is 1/3.',
        ),
      ],
    ),
    const Topic(
      id: 'decimals_y4',
      title: 'Decimals',
      titleBm: 'Perpuluhan',
      area: 'Decimals and place value',
      progress: 0.48,
      mastery: 'Moderate',
      questions: [],
    ),
    const Topic(
      id: 'percentages_y4',
      title: 'Percentages',
      titleBm: 'Peratus',
      area: 'Percentages in real life',
      progress: 0.28,
      mastery: 'Weak',
      questions: [],
    ),
    const Topic(
      id: 'money_y4',
      title: 'Money',
      titleBm: 'Wang',
      area: 'Money and daily spending',
      progress: 0,
      mastery: 'Locked',
      questions: [],
    ),
  ];

  int selectedTab = 0;
  String studentName = 'Aiman';
  int yearLevel = 4;
  String language = 'English';
  bool missionReminders = true;
  bool eyeComfortMode = true;
  int crystals = 124;
  int mutualAidEnergy = 36;
  int? latestFractionsScore;
  bool recommendedMissionRewardClaimed = false;
  final List<OasisArea> oasisAreas = [
    const OasisArea(
      id: 'fraction_bridge',
      title: 'Fraction Bridge',
      description: 'Reconnect oasis paths and learning routes.',
      resource: OasisResource.crystals,
      repairCost: 30,
      progress: 0.25,
    ),
    const OasisArea(
      id: 'decimal_waterway',
      title: 'Decimal Waterway',
      description: 'Bring clean water back to the oasis.',
      resource: OasisResource.crystals,
      repairCost: 35,
      progress: 0,
    ),
    const OasisArea(
      id: 'percentage_garden',
      title: 'Percentage Garden',
      description: 'Grow green areas through steady practice.',
      resource: OasisResource.crystals,
      repairCost: 40,
      progress: 0,
    ),
    const OasisArea(
      id: 'market_corner',
      title: 'Market Corner',
      description: 'Rebuild facilities with helpful community energy.',
      resource: OasisResource.mutualAid,
      repairCost: 20,
      progress: 0.25,
    ),
  ];
  final List<QuizAttempt> attempts = [
    QuizAttempt(
      id: 'attempt_demo_003',
      topicId: 'money_y4',
      topicTitle: 'Money',
      score: 86,
      correctCount: 4,
      totalQuestions: 5,
      earnedCrystals: 40,
      mastery: 'Strong',
      createdAt: DateTime.now().subtract(const Duration(hours: 3)),
    ),
    QuizAttempt(
      id: 'attempt_demo_002',
      topicId: 'decimals_y4',
      topicTitle: 'Decimals',
      score: 42,
      correctCount: 2,
      totalQuestions: 5,
      earnedCrystals: 22,
      mastery: 'Weak',
      createdAt: DateTime.now().subtract(const Duration(days: 1)),
    ),
    QuizAttempt(
      id: 'attempt_demo_001',
      topicId: 'fractions_y4',
      topicTitle: 'Fractions',
      score: 76,
      correctCount: 4,
      totalQuestions: 5,
      earnedCrystals: 34,
      mastery: 'Moderate',
      createdAt: DateTime.now().subtract(const Duration(days: 2)),
    ),
  ];

  int get completedQuizzes => attempts.length;

  int get averageScore {
    if (attempts.isEmpty) return 0;
    final total = attempts.fold<int>(0, (sum, attempt) => sum + attempt.score);
    return total ~/ attempts.length;
  }

  QuizAttempt? get latestAttempt => attempts.isEmpty ? null : attempts.first;

  List<QuizAttempt> get recentAttempts => attempts.take(4).toList();

  bool get isBahasaMelayu => language == 'Bahasa Melayu';

  RecommendedMission get recommendedMission {
    final topic = topics.firstWhere(
      (topic) => topic.id == recommendedMissionTopicId,
      orElse: () => topics.first,
    );
    final completedCompletions = attempts
        .where((attempt) => attempt.topicId == recommendedMissionTopicId)
        .length;

    return RecommendedMission(
      topicId: topic.id,
      topicTitle: topic.title,
      topicTitleBm: topic.titleBm,
      requiredCompletions: recommendedMissionRequiredCompletions,
      completedCompletions: completedCompletions,
      rewardCrystals: recommendedMissionRewardCrystals,
      rewardClaimed: recommendedMissionRewardClaimed,
    );
  }

  String t(String english, String bahasaMelayu) {
    return isBahasaMelayu ? bahasaMelayu : english;
  }

  WeakTopicInsight get weakTopicInsight {
    if (attempts.isEmpty) {
      return const WeakTopicInsight(
        topicId: 'none',
        topicTitle: 'No topic yet',
        averageScore: 0,
        attemptCount: 0,
        mastery: 'Weak',
        reason: 'No quiz attempts have been completed yet.',
        recommendation: 'Complete one Formula Forge mission to start tracking.',
      );
    }

    final grouped = <String, List<QuizAttempt>>{};
    for (final attempt in attempts) {
      grouped.putIfAbsent(attempt.topicId, () => []).add(attempt);
    }

    QuizAttempt? weakestRepresentative;
    var weakestAverage = 101;
    var weakestCount = 0;

    for (final entry in grouped.entries) {
      final topicAttempts = entry.value;
      final total = topicAttempts.fold<int>(
        0,
        (sum, attempt) => sum + attempt.score,
      );
      final average = total ~/ topicAttempts.length;
      if (average < weakestAverage) {
        weakestAverage = average;
        weakestCount = topicAttempts.length;
        weakestRepresentative = topicAttempts.first;
      }
    }

    final topicTitle = weakestRepresentative?.topicTitle ?? 'Unknown topic';
    final mastery = _masteryForScore(weakestAverage);

    return WeakTopicInsight(
      topicId: weakestRepresentative?.topicId ?? 'unknown',
      topicTitle: topicTitle,
      averageScore: weakestAverage,
      attemptCount: weakestCount,
      mastery: mastery,
      reason: _weakTopicReason(topicTitle, weakestAverage, weakestCount),
      recommendation: _parentRecommendation(topicTitle, weakestAverage),
    );
  }

  double get restorationProgress {
    final areaAverage =
        oasisAreas.fold<double>(0, (sum, area) => sum + area.progress) /
        oasisAreas.length;
    return areaAverage.clamp(0.0, 1.0);
  }

  Map<String, double> get oasisAreaProgress => {
    for (final area in oasisAreas) area.id: area.progress,
  };

  String get predictedWeakTopic => weakTopicInsight.topicTitle;

  void changeTab(int index) {
    if (index < 0) {
      selectedTab = 0;
    } else if (index > 2) {
      selectedTab = 2;
    } else {
      selectedTab = index;
    }
    notifyListeners();
  }

  void updateStudentProfile({required String name, required int year}) {
    studentName = name.trim().isEmpty ? studentName : name.trim();
    yearLevel = year.clamp(4, 6);
    notifyListeners();
  }

  void updateLanguage(String value) {
    language = value;
    notifyListeners();
  }

  void updateMissionReminders(bool value) {
    missionReminders = value;
    notifyListeners();
  }

  void updateEyeComfortMode(bool value) {
    eyeComfortMode = value;
    notifyListeners();
  }

  QuizReward saveQuizResult({
    required String topicId,
    required int correctCount,
    required int totalQuestions,
  }) {
    final topicIndex = topics.indexWhere((topic) => topic.id == topicId);
    if (topicIndex == -1) {
      throw ArgumentError('Unknown topicId: $topicId');
    }

    final topic = topics[topicIndex];
    final score = ((correctCount / totalQuestions) * 100).round();
    final earnedCrystals = _calculateCrystals(score, correctCount);
    final newMastery = _masteryForScore(score);
    final learningProgress = mathMax(topic.progress, score / 100);

    latestFractionsScore = topicId == 'fractions_y4'
        ? score
        : latestFractionsScore;
    crystals += earnedCrystals;
    topics[topicIndex] = topic.copyWith(
      progress: learningProgress,
      mastery: newMastery,
    );
    attempts.insert(
      0,
      QuizAttempt(
        id: 'attempt_${DateTime.now().millisecondsSinceEpoch}',
        topicId: topic.id,
        topicTitle: topic.title,
        score: score,
        correctCount: correctCount,
        totalQuestions: totalQuestions,
        earnedCrystals: earnedCrystals,
        mastery: newMastery,
        createdAt: DateTime.now(),
      ),
    );

    final reward = QuizReward(
      score: score,
      earnedCrystals: earnedCrystals,
      previousMastery: topic.mastery,
      newMastery: newMastery,
      encouragement: _encouragementForScore(score),
    );

    notifyListeners();
    return reward;
  }

  bool claimRecommendedMissionReward() {
    final mission = recommendedMission;
    if (!mission.isReadyToClaim) return false;

    crystals += mission.rewardCrystals;
    recommendedMissionRewardClaimed = true;
    notifyListeners();
    return true;
  }

  double mathMax(double a, double b) => a > b ? a : b;

  bool canRepair(OasisArea area) {
    if (area.isComplete) return false;
    return switch (area.resource) {
      OasisResource.crystals => crystals >= area.repairCost,
      OasisResource.mutualAid => mutualAidEnergy >= area.repairCost,
    };
  }

  bool repairOasisArea(String areaId) {
    final areaIndex = oasisAreas.indexWhere((area) => area.id == areaId);
    if (areaIndex == -1) return false;

    final area = oasisAreas[areaIndex];
    if (!canRepair(area)) return false;

    switch (area.resource) {
      case OasisResource.crystals:
        crystals -= area.repairCost;
      case OasisResource.mutualAid:
        mutualAidEnergy -= area.repairCost;
    }

    oasisAreas[areaIndex] = area.copyWith(
      progress: (area.progress + 0.25).clamp(0.0, 1.0),
    );
    notifyListeners();
    return true;
  }

  int _calculateCrystals(int score, int correctCount) {
    final effortBonus = 10;
    final correctBonus = correctCount * 4;
    final masteryBonus = score >= 80
        ? 14
        : score >= 50
        ? 8
        : 4;
    return effortBonus + correctBonus + masteryBonus;
  }

  String _masteryForScore(int score) {
    if (score >= 80) return 'Strong';
    if (score >= 50) return 'Moderate';
    return 'Weak';
  }

  String _encouragementForScore(int score) {
    if (score >= 80) {
      return 'Great work. This topic is becoming stronger.';
    }
    if (score >= 50) {
      return 'Good progress. A little more practice can strengthen this area.';
    }
    return 'Keep going. The oasis still grows when you try and review mistakes.';
  }

  String _weakTopicReason(
    String topicTitle,
    int averageScore,
    int attemptCount,
  ) {
    if (attemptCount == 1) {
      return '$topicTitle has the lowest recent score at $averageScore% from one attempt.';
    }
    return '$topicTitle has the lowest average score at $averageScore% across $attemptCount attempts.';
  }

  String _parentRecommendation(String topicTitle, int averageScore) {
    if (averageScore >= 80) {
      return 'Maintain progress with one short $topicTitle mission this week.';
    }
    if (averageScore >= 50) {
      return 'Review wrong answers and complete one guided $topicTitle practice mission.';
    }
    return 'Spend 10 minutes revising basics, then retry an easy $topicTitle mission with parent support.';
  }
}
