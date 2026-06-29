import 'dart:async';

import 'package:flutter/material.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/oasis_area.dart';
import 'package:logic_oasis/shared/models/quiz_attempt.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';
import 'package:logic_oasis/shared/models/recommended_mission.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/models/weak_topic_insight.dart';
import 'package:logic_oasis/shared/repositories/learning_repository.dart';
import 'package:logic_oasis/shared/repositories/topic_repository.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppState extends ChangeNotifier {
  AppState({
    TopicRepository? topicRepository,
    LearningRepository? learningRepository,
  }) : _topicRepository = topicRepository,
       _learningRepository = learningRepository,
       topics = List<Topic>.from(_localTopicsForYear(4));

  static const String demoStudentId = 'student_aiman_y4';
  // Used only when the student has no quiz attempts yet.
  static const String recommendedMissionTopicId = 'fractions_y4';
  static const int recommendedMissionRequiredCompletions = 2;
  static const int recommendedMissionRewardCrystals = 20;
  static const String _lastTabKey = 'logic_oasis_last_tab';
  static const String _languageKey = 'logic_oasis_language';
  static const String _missionRemindersKey = 'logic_oasis_mission_reminders';
  static const String _eyeComfortKey = 'logic_oasis_eye_comfort';

  static const List<Topic> _localTopicBank = [
    const Topic(
      id: 'fractions_y4',
      title: 'Fractions',
      titleBm: 'Pecahan',
      area: 'Understand and compare fractions',
      yearLevel: 4,
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
      yearLevel: 4,
      progress: 0.48,
      mastery: 'Moderate',
      questions: [],
    ),
    const Topic(
      id: 'percentages_y4',
      title: 'Percentages',
      titleBm: 'Peratus',
      area: 'Percentages in real life',
      yearLevel: 4,
      progress: 0.28,
      mastery: 'Weak',
      questions: [],
    ),
    const Topic(
      id: 'money_y4',
      title: 'Money',
      titleBm: 'Wang',
      area: 'Money and daily spending',
      yearLevel: 4,
      progress: 0,
      mastery: 'Locked',
      questions: [],
    ),
    const Topic(
      id: 'fractions_y5',
      title: 'Fractions',
      titleBm: 'Pecahan',
      area: 'Mixed numbers and fraction operations',
      yearLevel: 5,
      progress: 0,
      mastery: 'New',
      questions: [
        QuizQuestion(
          question: 'What is 1 1/2 + 1/2?',
          options: ['1', '1 1/2', '2', '2 1/2'],
          answerIndex: 2,
          explanation: '1 1/2 plus 1/2 makes 2 wholes.',
        ),
        QuizQuestion(
          question: 'Which fraction is equivalent to 3/5?',
          options: ['6/10', '3/10', '5/3', '9/10'],
          answerIndex: 0,
          explanation: 'Multiply both numerator and denominator by 2.',
        ),
      ],
    ),
    const Topic(
      id: 'decimals_y5',
      title: 'Decimals',
      titleBm: 'Perpuluhan',
      area: 'Decimal addition and subtraction',
      yearLevel: 5,
      progress: 0,
      mastery: 'New',
      questions: [
        QuizQuestion(
          question: 'What is 2.35 + 1.4?',
          options: ['2.49', '3.39', '3.75', '4.35'],
          answerIndex: 2,
          explanation: 'Line up decimal places: 2.35 + 1.40 = 3.75.',
        ),
        QuizQuestion(
          question: 'What is 5.0 - 0.75?',
          options: ['4.25', '4.35', '5.75', '3.25'],
          answerIndex: 0,
          explanation: '5.00 minus 0.75 equals 4.25.',
        ),
      ],
    ),
    const Topic(
      id: 'percentages_y5',
      title: 'Percentages',
      titleBm: 'Peratus',
      area: 'Percentage of quantities',
      yearLevel: 5,
      progress: 0,
      mastery: 'New',
      questions: [
        QuizQuestion(
          question: 'What is 25% of 80?',
          options: ['10', '20', '25', '40'],
          answerIndex: 1,
          explanation: '25% is one quarter. One quarter of 80 is 20.',
        ),
        QuizQuestion(
          question: '50% is the same as which fraction?',
          options: ['1/4', '1/3', '1/2', '3/4'],
          answerIndex: 2,
          explanation: '50% means half of the whole.',
        ),
      ],
    ),
    const Topic(
      id: 'measurement_y5',
      title: 'Measurement',
      titleBm: 'Ukuran',
      area: 'Length, mass, and volume conversion',
      yearLevel: 5,
      progress: 0,
      mastery: 'New',
      questions: [
        QuizQuestion(
          question: 'How many centimetres are in 2.5 metres?',
          options: ['25 cm', '250 cm', '2500 cm', '0.25 cm'],
          answerIndex: 1,
          explanation: '1 metre is 100 cm, so 2.5 metres is 250 cm.',
        ),
        QuizQuestion(
          question: 'How many grams are in 3 kg?',
          options: ['30 g', '300 g', '3000 g', '30000 g'],
          answerIndex: 2,
          explanation: '1 kg is 1000 g, so 3 kg is 3000 g.',
        ),
      ],
    ),
    const Topic(
      id: 'fractions_y6',
      title: 'Fractions',
      titleBm: 'Pecahan',
      area: 'Fraction problem solving',
      yearLevel: 6,
      progress: 0,
      mastery: 'New',
      questions: [
        QuizQuestion(
          question: 'What is 2/3 of 24?',
          options: ['8', '12', '16', '18'],
          answerIndex: 2,
          explanation: 'One third of 24 is 8, so two thirds is 16.',
        ),
        QuizQuestion(
          question: 'What is 3/4 x 20?',
          options: ['10', '12', '15', '18'],
          answerIndex: 2,
          explanation: 'A quarter of 20 is 5, so three quarters is 15.',
        ),
      ],
    ),
    const Topic(
      id: 'percentages_y6',
      title: 'Percentages',
      titleBm: 'Peratus',
      area: 'Discounts, profit, and loss',
      yearLevel: 6,
      progress: 0,
      mastery: 'New',
      questions: [
        QuizQuestion(
          question: 'A RM50 bag has a 10% discount. What is the discount?',
          options: ['RM5', 'RM10', 'RM15', 'RM45'],
          answerIndex: 0,
          explanation: '10% of RM50 is RM5.',
        ),
        QuizQuestion(
          question: 'A price increases from RM40 to RM50. What is the increase?',
          options: ['10%', '20%', '25%', '50%'],
          answerIndex: 2,
          explanation: 'The increase is RM10. RM10 out of RM40 is 25%.',
        ),
      ],
    ),
    const Topic(
      id: 'ratio_y6',
      title: 'Ratio',
      titleBm: 'Nisbah',
      area: 'Compare quantities using ratios',
      yearLevel: 6,
      progress: 0,
      mastery: 'New',
      questions: [
        QuizQuestion(
          question: 'The ratio of red to blue beads is 2:3. If there are 10 red beads, how many blue beads are there?',
          options: ['12', '15', '20', '30'],
          answerIndex: 1,
          explanation: '2 parts equals 10, so 1 part equals 5. Blue is 3 parts, so 15.',
        ),
        QuizQuestion(
          question: 'Simplify the ratio 12:18.',
          options: ['2:3', '3:2', '4:9', '6:9'],
          answerIndex: 0,
          explanation: 'Divide both numbers by 6 to get 2:3.',
        ),
      ],
    ),
    const Topic(
      id: 'data_y6',
      title: 'Data Handling',
      titleBm: 'Pengendalian Data',
      area: 'Read charts and calculate averages',
      yearLevel: 6,
      progress: 0,
      mastery: 'New',
      questions: [
        QuizQuestion(
          question: 'Find the average of 6, 8, and 10.',
          options: ['7', '8', '9', '10'],
          answerIndex: 1,
          explanation: '6 + 8 + 10 = 24, and 24 divided by 3 is 8.',
        ),
        QuizQuestion(
          question: 'The mode of 3, 5, 5, 7, 8 is...',
          options: ['3', '5', '7', '8'],
          answerIndex: 1,
          explanation: 'The mode is the value that appears most often.',
        ),
      ],
    ),
  ];

  static List<Topic> _localTopicsForYear(int yearLevel) {
    final normalizedYearLevel = yearLevel.clamp(4, 6);
    return _localTopicBank
        .where((topic) => topic.yearLevel == normalizedYearLevel)
        .toList();
  }

  final TopicRepository? _topicRepository;
  final LearningRepository? _learningRepository;
  final List<Topic> topics;
  int selectedTab = 0;
  bool isLoadingTopics = false;
  bool loadedTopicsFromFirebase = false;
  String? topicLoadMessage;
  bool isSavingQuizToFirebase = false;
  bool lastQuizSavedToFirebase = false;
  String? quizSaveMessage;
  bool isLoadingParentDashboard = false;
  bool loadedParentDashboardFromFirebase = false;
  String? parentDashboardMessage;
  String currentStudentId = demoStudentId;
  String? currentStudentEmail;
  String studentName = 'Aiman';
  int yearLevel = 4;
  String language = 'English';
  bool missionReminders = true;
  bool eyeComfortMode = false;
  int crystals = 124;
  int mutualAidEnergy = 36;
  int? latestFractionsScore;
  final Set<String> claimedRecommendedMissionTopicIds = <String>{};
  final List<AiDiagnosis> aiDiagnoses = <AiDiagnosis>[];
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
      yearLevel: 4,
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
      yearLevel: 4,
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
      yearLevel: 4,
      score: 76,
      correctCount: 4,
      totalQuestions: 5,
      earnedCrystals: 34,
      mastery: 'Moderate',
      createdAt: DateTime.now().subtract(const Duration(days: 2)),
    ),
  ];

  List<QuizAttempt> get currentYearAttempts => attempts
      .where((attempt) => attempt.yearLevel == yearLevel)
      .toList(growable: false);

  int get completedQuizzes => currentYearAttempts.length;

  int get averageScore {
    final yearAttempts = currentYearAttempts;
    if (yearAttempts.isEmpty) return 0;
    final total = yearAttempts.fold<int>(
      0,
      (sum, attempt) => sum + attempt.score,
    );
    return total ~/ yearAttempts.length;
  }

  QuizAttempt? get latestAttempt =>
      currentYearAttempts.isEmpty ? null : currentYearAttempts.first;

  List<QuizAttempt> get recentAttempts => currentYearAttempts.take(4).toList();

  bool get isBahasaMelayu => language == 'Bahasa Melayu';

  Locale get locale => isBahasaMelayu ? const Locale('ms') : const Locale('en');

  AiDiagnosis? get recommendedAiDiagnosis => _recommendedAiDiagnosis();

  Future<void> loadSavedAppPreferences() async {
    final preferences = await SharedPreferences.getInstance();
    selectedTab = (preferences.getInt(_lastTabKey) ?? selectedTab).clamp(0, 2);
    language = preferences.getString(_languageKey) ?? language;
    missionReminders =
        preferences.getBool(_missionRemindersKey) ?? missionReminders;
    eyeComfortMode = preferences.getBool(_eyeComfortKey) ?? eyeComfortMode;
    notifyListeners();
  }

  Future<void> saveAppSession() async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setInt(_lastTabKey, selectedTab.clamp(0, 2));
    await preferences.setString(_languageKey, language);
    await preferences.setBool(_missionRemindersKey, missionReminders);
    await preferences.setBool(_eyeComfortKey, eyeComfortMode);
  }

  Future<void> clearSavedSessionPosition() async {
    selectedTab = 0;
    final preferences = await SharedPreferences.getInstance();
    await preferences.remove(_lastTabKey);
    notifyListeners();
  }

  Future<void> loadTopicsFromFirebase() async {
    if (isLoadingTopics) return;

    isLoadingTopics = true;
    topicLoadMessage = null;
    notifyListeners();

    try {
      final repository = _topicRepository ?? TopicRepository();
      final firebaseTopics = await repository.fetchTopicsWithQuestions(
        yearLevel: yearLevel,
      );
      if (firebaseTopics.isEmpty) {
        _resetTopicsForCurrentYear();
        loadedTopicsFromFirebase = false;
        topicLoadMessage = t(
          'Using local Year $yearLevel sample topics until Firestore is seeded.',
          'Menggunakan contoh topik Tahun $yearLevel setempat sehingga Firestore diisi.',
        );
      } else {
        topics
          ..clear()
          ..addAll(_mergeTopicProgress(firebaseTopics));
        loadedTopicsFromFirebase = true;
        topicLoadMessage = t(
          'Loaded ${firebaseTopics.length} Year $yearLevel topics from Firebase.',
          'Memuat ${firebaseTopics.length} topik Tahun $yearLevel daripada Firebase.',
        );
      }
    } catch (_) {
      _resetTopicsForCurrentYear();
      loadedTopicsFromFirebase = false;
      topicLoadMessage = t(
        'Firebase unavailable. Using local Year $yearLevel sample topics.',
        'Firebase tidak tersedia. Menggunakan contoh topik Tahun $yearLevel setempat.',
      );
    } finally {
      isLoadingTopics = false;
      notifyListeners();
    }
  }

  RecommendedMission get recommendedMission {
    final recommendedTopicId = _currentRecommendedMissionTopicId();
    final topic = topics.firstWhere(
      (topic) => topic.id == recommendedTopicId,
      orElse: () => topics.first,
    );
    final completedCompletions = attempts
        .where((attempt) => attempt.topicId == topic.id)
        .length;

    return RecommendedMission(
      topicId: topic.id,
      topicTitle: topic.title,
      topicTitleBm: topic.titleBm,
      requiredCompletions: recommendedMissionRequiredCompletions,
      completedCompletions: completedCompletions,
      rewardCrystals: recommendedMissionRewardCrystals,
      rewardClaimed: claimedRecommendedMissionTopicIds.contains(topic.id),
    );
  }

  String t(String english, String bahasaMelayu) {
    return isBahasaMelayu ? bahasaMelayu : english;
  }

  WeakTopicInsight get weakTopicInsight {
    final aiInsight = _aiWeakTopicInsight();
    if (aiInsight != null) return aiInsight;
    final yearAttempts = currentYearAttempts;

    if (yearAttempts.isEmpty) {
      return WeakTopicInsight(
        topicId: 'none',
        topicTitle: 'No Year $yearLevel topic yet',
        averageScore: 0,
        attemptCount: 0,
        mastery: 'Weak',
        reason: 'No Year $yearLevel quiz attempts have been completed yet.',
        recommendation:
            'Complete one Year $yearLevel Formula Forge mission to start tracking.',
      );
    }

    final grouped = <String, List<QuizAttempt>>{};
    for (final attempt in yearAttempts) {
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
    unawaited(saveAppSession());
  }

  void updateStudentProfile({required String name, required int year}) {
    final nextYearLevel = year.clamp(4, 6);
    final yearChanged = nextYearLevel != yearLevel;
    studentName = name.trim().isEmpty ? studentName : name.trim();
    yearLevel = nextYearLevel;
    if (yearChanged) {
      _resetTopicsForCurrentYear();
      unawaited(loadTopicsFromFirebase());
    }
    notifyListeners();
    unawaited(saveAppSession());
  }

  void updateSignedInStudent({
    required String uid,
    required String email,
    String? name,
    int? year,
  }) {
    final nextYearLevel = (year ?? yearLevel).clamp(4, 6);
    final yearChanged = nextYearLevel != yearLevel;
    currentStudentId = uid;
    currentStudentEmail = email;
    if (name != null && name.trim().isNotEmpty) {
      studentName = name.trim();
    }
    yearLevel = nextYearLevel;
    if (yearChanged) {
      _resetTopicsForCurrentYear();
      unawaited(loadTopicsFromFirebase());
    }
    notifyListeners();
    unawaited(saveAppSession());
  }

  void updateLanguage(String value) {
    language = value;
    notifyListeners();
    unawaited(saveAppSession());
  }

  void updateMissionReminders(bool value) {
    missionReminders = value;
    notifyListeners();
    unawaited(saveAppSession());
  }

  void updateEyeComfortMode(bool value) {
    eyeComfortMode = value;
    notifyListeners();
    unawaited(saveAppSession());
  }

  QuizReward saveQuizResult({
    required String topicId,
    required int correctCount,
    required int totalQuestions,
    int timeTakenSeconds = 0,
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
    final attemptId = 'attempt_${DateTime.now().millisecondsSinceEpoch}';
    final attempt = QuizAttempt(
      id: attemptId,
      topicId: topic.id,
      topicTitle: topic.title,
      yearLevel: topic.yearLevel,
      score: score,
      correctCount: correctCount,
      totalQuestions: totalQuestions,
      earnedCrystals: earnedCrystals,
      mastery: newMastery,
      createdAt: DateTime.now(),
    );

    attempts.insert(0, attempt);

    final reward = QuizReward(
      score: score,
      earnedCrystals: earnedCrystals,
      previousMastery: topic.mastery,
      newMastery: newMastery,
      encouragement: _encouragementForScore(score),
    );

    notifyListeners();
    unawaited(_saveQuizResultToFirebase(attempt, timeTakenSeconds));
    return reward;
  }

  Future<void> _saveQuizResultToFirebase(
    QuizAttempt attempt,
    int timeTakenSeconds,
  ) async {
    isSavingQuizToFirebase = true;
    lastQuizSavedToFirebase = false;
    quizSaveMessage = t(
      'Saving quiz result to Firebase...',
      'Menyimpan keputusan kuiz ke Firebase...',
    );
    notifyListeners();

    try {
      final repository = _learningRepository ?? LearningRepository();
      final topicAttempts = attempts
          .where(
            (item) =>
                item.topicId == attempt.topicId &&
                item.yearLevel == attempt.yearLevel,
          )
          .toList();
      await repository.saveQuizAttemptAndMastery(
        studentId: currentStudentId,
        attempt: attempt,
        timeTakenSeconds: timeTakenSeconds,
        retryCount: topicAttempts.length - 1,
        difficultyLevel: 'Mixed',
        topicAttempts: topicAttempts,
      );
      lastQuizSavedToFirebase = true;
      quizSaveMessage = t(
        'Quiz result saved to Firebase.',
        'Keputusan kuiz disimpan ke Firebase.',
      );
    } catch (_) {
      lastQuizSavedToFirebase = false;
      quizSaveMessage = t(
        'Firebase save failed. Local result is still kept.',
        'Simpanan Firebase gagal. Keputusan setempat masih disimpan.',
      );
    } finally {
      isSavingQuizToFirebase = false;
      notifyListeners();
    }
  }

  Future<void> loadParentDashboardFromFirebase() async {
    if (isLoadingParentDashboard) return;

    isLoadingParentDashboard = true;
    parentDashboardMessage = null;
    notifyListeners();

    try {
      final repository = _learningRepository ?? LearningRepository();
      final snapshot = await repository.fetchParentDashboardSnapshot(
        studentId: currentStudentId,
        yearLevel: yearLevel,
        topics: topics,
      );

      if (snapshot.attempts.isEmpty &&
          snapshot.masteryRecordCount == 0 &&
          snapshot.aiDiagnoses.isEmpty) {
        loadedParentDashboardFromFirebase = false;
        parentDashboardMessage = t(
          'Using local parent dashboard until Firestore has learning data.',
          'Menggunakan papan pemuka ibu bapa setempat sehingga Firestore mempunyai data pembelajaran.',
        );
      } else {
        if (snapshot.attempts.isNotEmpty) {
          attempts
            ..clear()
            ..addAll(snapshot.attempts);
        }
        aiDiagnoses
          ..clear()
          ..addAll(snapshot.aiDiagnoses);
        _applyAiTopicMastery();
        loadedParentDashboardFromFirebase = true;
        parentDashboardMessage = t(
          'Loaded parent dashboard from Firebase: ${snapshot.attempts.length} attempts, ${snapshot.masteryRecordCount} mastery records, ${snapshot.aiDiagnoses.length} AI diagnoses.',
          'Memuat papan pemuka ibu bapa daripada Firebase: ${snapshot.attempts.length} cubaan, ${snapshot.masteryRecordCount} rekod penguasaan, ${snapshot.aiDiagnoses.length} diagnosis AI.',
        );
      }
    } catch (_) {
      loadedParentDashboardFromFirebase = false;
      parentDashboardMessage = t(
        'Firebase parent dashboard unavailable. Using local summary.',
        'Papan pemuka ibu bapa Firebase tidak tersedia. Menggunakan ringkasan setempat.',
      );
    } finally {
      isLoadingParentDashboard = false;
      notifyListeners();
    }
  }

  bool claimRecommendedMissionReward() {
    final mission = recommendedMission;
    if (!mission.isReadyToClaim) return false;

    crystals += mission.rewardCrystals;
    claimedRecommendedMissionTopicIds.add(mission.topicId);
    notifyListeners();
    return true;
  }

  double mathMax(double a, double b) => a > b ? a : b;

  List<Topic> _mergeTopicProgress(List<Topic> firebaseTopics) {
    return firebaseTopics.map((firebaseTopic) {
      final localMatches = _localTopicBank.where(
        (localTopic) => localTopic.id == firebaseTopic.id,
      );
      if (localMatches.isEmpty) return firebaseTopic;

      final localTopic = localMatches.first;
      return firebaseTopic.copyWith(
        progress: localTopic.progress,
        mastery: localTopic.mastery,
      );
    }).toList();
  }

  void _resetTopicsForCurrentYear() {
    topics
      ..clear()
      ..addAll(_mergeTopicProgress(_localTopicsForYear(yearLevel)));
    topicLoadMessage = null;
    loadedTopicsFromFirebase = false;
  }

  String _currentRecommendedMissionTopicId() {
    final aiRecommendation = _recommendedAiDiagnosis();
    if (aiRecommendation != null &&
        !claimedRecommendedMissionTopicIds.contains(aiRecommendation.topicId)) {
      return aiRecommendation.topicId;
    }

    final yearAttempts = currentYearAttempts;
    if (yearAttempts.isEmpty) return _firstUnclaimedTopicId();

    final grouped = <String, List<QuizAttempt>>{};
    for (final attempt in yearAttempts) {
      if (!topics.any((topic) => topic.id == attempt.topicId)) continue;
      if (claimedRecommendedMissionTopicIds.contains(attempt.topicId)) {
        continue;
      }
      grouped.putIfAbsent(attempt.topicId, () => []).add(attempt);
    }

    if (grouped.isEmpty) return _firstUnclaimedTopicId();

    var weakestTopicId = grouped.keys.first;
    var weakestAverage = 101;

    for (final entry in grouped.entries) {
      final average = _averageScoreForAttempts(entry.value);
      if (average < weakestAverage) {
        weakestTopicId = entry.key;
        weakestAverage = average;
      }
    }

    return weakestTopicId;
  }

  String _firstUnclaimedTopicId() {
    final unclaimedTopics = topics.where(
      (topic) => !claimedRecommendedMissionTopicIds.contains(topic.id),
    );
    return unclaimedTopics.isEmpty ? topics.first.id : unclaimedTopics.first.id;
  }

  int _averageScoreForAttempts(List<QuizAttempt> topicAttempts) {
    if (topicAttempts.isEmpty) return 0;
    final total = topicAttempts.fold<int>(
      0,
      (sum, attempt) => sum + attempt.score,
    );
    return total ~/ topicAttempts.length;
  }

  AiDiagnosis? _recommendedAiDiagnosis() {
    if (aiDiagnoses.isEmpty) return null;

    AiDiagnosis? selected;
    var selectedScore = double.negativeInfinity;

    for (final diagnosis in aiDiagnoses) {
      if (diagnosis.yearLevel != null && diagnosis.yearLevel != yearLevel) {
        continue;
      }
      if (!topics.any((topic) => topic.id == diagnosis.topicId)) continue;
      final weaknessWeight = diagnosis.weaknessProbability;
      final masteryGap = 1 - diagnosis.bktMasteryProbability;
      final score = (weaknessWeight * 0.65) + (masteryGap * 0.35);
      if (score > selectedScore) {
        selected = diagnosis;
        selectedScore = score;
      }
    }

    return selected;
  }

  WeakTopicInsight? _aiWeakTopicInsight() {
    final diagnosis = _recommendedAiDiagnosis();
    if (diagnosis == null) return null;

    final topicTitle = _topicTitleFor(diagnosis.topicId);
    final masteryPercent = (diagnosis.bktMasteryProbability * 100).round();
    final weaknessPercent = (diagnosis.weaknessProbability * 100).round();
    final reason = diagnosis.shapReasons.isEmpty
        ? t(
            '$topicTitle is flagged by the Grey Box AI with $weaknessPercent% weakness risk and $masteryPercent% BKT mastery.',
            '$topicTitle ditandakan oleh AI Grey Box dengan risiko kelemahan $weaknessPercent% dan penguasaan BKT $masteryPercent%.',
          )
        : t(
            '$topicTitle is flagged by the Grey Box AI because ${diagnosis.shapReasons.take(3).join(', ')}.',
            '$topicTitle ditandakan oleh AI Grey Box kerana ${diagnosis.shapReasons.take(3).join(', ')}.',
          );

    return WeakTopicInsight(
      topicId: diagnosis.topicId,
      topicTitle: topicTitle,
      averageScore: masteryPercent,
      attemptCount: _attemptCountForTopic(diagnosis.topicId),
      mastery: diagnosis.finalMasteryLabel,
      reason: reason,
      recommendation: diagnosis.recommendedAction,
    );
  }

  String _topicTitleFor(String topicId) {
    final matches = topics.where((topic) => topic.id == topicId);
    return matches.isEmpty ? topicId : matches.first.title;
  }

  int _attemptCountForTopic(String topicId) {
    return currentYearAttempts
        .where((attempt) => attempt.topicId == topicId)
        .length;
  }

  void _applyAiTopicMastery() {
    for (final diagnosis in aiDiagnoses) {
      if (diagnosis.yearLevel != null && diagnosis.yearLevel != yearLevel) {
        continue;
      }
      final topicIndex = topics.indexWhere(
        (topic) => topic.id == diagnosis.topicId,
      );
      if (topicIndex == -1) continue;

      final topic = topics[topicIndex];
      topics[topicIndex] = topic.copyWith(
        progress: diagnosis.bktMasteryProbability.clamp(0.0, 1.0),
        mastery: diagnosis.finalMasteryLabel,
      );
    }
  }

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
      return t(
        '$topicTitle has the lowest recent score at $averageScore% from one attempt.',
        '$topicTitle mempunyai markah terkini paling rendah iaitu $averageScore% daripada satu cubaan.',
      );
    }
    return t(
      '$topicTitle has the lowest average score at $averageScore% across $attemptCount attempts.',
      '$topicTitle mempunyai purata markah paling rendah iaitu $averageScore% daripada $attemptCount cubaan.',
    );
  }

  String _parentRecommendation(String topicTitle, int averageScore) {
    if (averageScore >= 80) {
      return t(
        'Maintain progress with one short $topicTitle mission this week.',
        'Kekalkan kemajuan dengan satu misi ringkas $topicTitle minggu ini.',
      );
    }
    if (averageScore >= 50) {
      return t(
        'Review wrong answers and complete one guided $topicTitle practice mission.',
        'Semak jawapan salah dan lengkapkan satu misi latihan berpandu $topicTitle.',
      );
    }
    return t(
      'Spend 10 minutes revising basics, then retry an easy $topicTitle mission with parent support.',
      'Luangkan 10 minit mengulang kaji asas, kemudian cuba semula misi mudah $topicTitle dengan sokongan ibu bapa.',
    );
  }
}
