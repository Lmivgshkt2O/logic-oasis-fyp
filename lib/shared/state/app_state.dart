import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:logic_oasis/shared/data/year4_chapter1_content.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/oasis_area.dart';
import 'package:logic_oasis/shared/models/quiz_attempt.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';
import 'package:logic_oasis/shared/models/recommended_mission.dart';
import 'package:logic_oasis/shared/models/subtopic.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/models/weak_topic_insight.dart';
import 'package:logic_oasis/shared/repositories/learning_repository.dart';
import 'package:logic_oasis/shared/repositories/topic_repository.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppState extends ChangeNotifier {
  AppState({
    TopicRepository? topicRepository,
    LearningRepository? learningRepository,
    this.persistQuizResults = false,
  }) : _topicRepository = topicRepository,
       _learningRepository = learningRepository,
       topics = List<Topic>.from(_localTopicsForYear(4));

  static const String demoStudentId = 'student_aiman_y4';
  // Used only when the student has no quiz attempts yet.
  static const String recommendedMissionTopicId = 'whole_numbers_y4';
  static const int recommendedMissionRequiredCompletions = 2;
  static const int recommendedMissionRewardCrystals = 20;
  static const String _lastTabKey = 'logic_oasis_last_tab';
  static const String _languageKey = 'logic_oasis_language';
  static const String _missionRemindersKey = 'logic_oasis_mission_reminders';
  static const String _eyeComfortKey = 'logic_oasis_eye_comfort';
  static const String _soundEnabledKey = 'logic_oasis_sound_enabled';
  static const String _accessibilityModeKey =
      'logic_oasis_accessibility_mode';
  static const String _screenTimeLimitKey = 'logic_oasis_screen_time_limit';
  static const String _unlockedTopicIdsKey = 'logic_oasis_unlocked_topics';
  static const String _unlockedSubtopicIdsKey =
      'logic_oasis_unlocked_subtopics';
  static const String _claimedMissionTopicIdsKey =
      'logic_oasis_claimed_mission_topics';
  static const String _savedAttemptsKey = 'logic_oasis_saved_attempts';
  static const int _maxStoredResource = 99999;

  static final List<Topic> _localTopicBank = [
    ...year4Chapter1Topics,
    const Topic(
      id: 'fractions_y4',
      title: 'Fractions',
      titleBm: 'Pecahan',
      area: 'Understand and compare fractions',
      yearLevel: 4,
      progress: 0,
      mastery: 'Locked',
      subtopics: [
        Subtopic(
          id: 'equivalent_fractions',
          title: 'Equivalent Fractions',
          titleBm: 'Pecahan Setara',
          order: 1,
          description: 'Recognise fractions with the same value.',
          descriptionBm: 'Kenal pecahan yang mempunyai nilai yang sama.',
          progress: 1,
          mastery: 'Strong',
          questions: [
            QuizQuestion(
              subtopicId: 'equivalent_fractions',
              question: 'Which fraction is equal to 1/2?',
              options: ['1/4', '2/4', '3/4', '4/4'],
              answerIndex: 1,
              explanation:
                  '2/4 can be simplified by dividing both numbers by 2.',
            ),
            QuizQuestion(
              subtopicId: 'equivalent_fractions',
              question: 'Which fraction is equivalent to 3/6?',
              questionBm: 'Pecahan manakah yang setara dengan 3/6?',
              options: ['1/2', '1/3', '2/3', '3/4'],
              optionsBm: ['1/2', '1/3', '2/3', '3/4'],
              answerIndex: 0,
              explanation: '3/6 simplifies to 1/2.',
              explanationBm: '3/6 diringkaskan kepada 1/2.',
            ),
          ],
        ),
        Subtopic(
          id: 'compare_unit_fractions',
          title: 'Compare Unit Fractions',
          titleBm: 'Banding Pecahan Unit',
          order: 2,
          description: 'Compare unit fractions by denominator size.',
          descriptionBm: 'Banding pecahan unit mengikut saiz penyebut.',
          progress: 1,
          mastery: 'Strong',
          questions: [
            QuizQuestion(
              subtopicId: 'compare_unit_fractions',
              question: 'Which fraction is larger?',
              options: ['1/3', '1/5', '1/8', '1/10'],
              answerIndex: 0,
              explanation:
                  'For unit fractions, the smaller denominator is larger.',
            ),
            QuizQuestion(
              subtopicId: 'compare_unit_fractions',
              question: 'Which is smaller?',
              questionBm: 'Yang manakah lebih kecil?',
              options: ['1/2', '1/4', '1/6', '1/8'],
              optionsBm: ['1/2', '1/4', '1/6', '1/8'],
              answerIndex: 3,
              explanation:
                  'For unit fractions, the larger denominator is smaller.',
              explanationBm:
                  'Bagi pecahan unit, penyebut yang lebih besar memberi nilai lebih kecil.',
            ),
          ],
        ),
        Subtopic(
          id: 'add_like_denominators',
          title: 'Add Like Denominators',
          titleBm: 'Tambah Penyebut Sama',
          order: 3,
          description: 'Add fractions that share the same denominator.',
          descriptionBm: 'Tambah pecahan yang mempunyai penyebut yang sama.',
          progress: .4,
          mastery: 'Weak',
          questions: [
            QuizQuestion(
              subtopicId: 'add_like_denominators',
              question: 'What is 1/4 + 1/4?',
              options: ['1/8', '1/4', '1/2', '1'],
              answerIndex: 2,
              explanation:
                  'One quarter plus one quarter makes two quarters, or 1/2.',
            ),
            QuizQuestion(
              subtopicId: 'add_like_denominators',
              question: 'What is 2/5 + 1/5?',
              questionBm: 'Berapakah 2/5 + 1/5?',
              options: ['2/10', '3/5', '3/10', '1/5'],
              optionsBm: ['2/10', '3/5', '3/10', '1/5'],
              answerIndex: 1,
              explanation: 'Keep the denominator 5 and add 2 + 1.',
              explanationBm: 'Kekalkan penyebut 5 dan tambah 2 + 1.',
            ),
          ],
        ),
      ],
    ),
    const Topic(
      id: 'decimals_y4',
      title: 'Decimals',
      titleBm: 'Perpuluhan',
      area: 'Decimals and place value',
      yearLevel: 4,
      progress: 0,
      mastery: 'Locked',
      subtopics: [
        Subtopic(
          id: 'decimal_place_value',
          title: 'Decimal Place Value',
          titleBm: 'Nilai Tempat Perpuluhan',
          order: 1,
          description: 'Read tenths and hundredths.',
          descriptionBm: 'Baca persepuluh dan perseratus.',
          progress: 1,
          mastery: 'Moderate',
          questions: [
            QuizQuestion(
              subtopicId: 'decimal_place_value',
              question: 'What is the value of the digit 5 in 3.52?',
              questionBm: 'Apakah nilai digit 5 dalam 3.52?',
              options: ['5 ones', '5 tenths', '5 hundredths', '5 tens'],
              optionsBm: ['5 sa', '5 persepuluh', '5 perseratus', '5 puluh'],
              answerIndex: 1,
              explanation: 'The digit 5 is in the tenths place.',
              explanationBm: 'Digit 5 berada di tempat persepuluh.',
            ),
          ],
        ),
        Subtopic(
          id: 'compare_decimals',
          title: 'Compare Decimals',
          titleBm: 'Banding Perpuluhan',
          order: 2,
          description: 'Compare decimal values.',
          descriptionBm: 'Banding nilai perpuluhan.',
          questions: [
            QuizQuestion(
              subtopicId: 'compare_decimals',
              question: 'Which decimal is the largest?',
              questionBm: 'Perpuluhan manakah yang paling besar?',
              options: ['0.4', '0.35', '0.09', '0.3'],
              optionsBm: ['0.4', '0.35', '0.09', '0.3'],
              answerIndex: 0,
              explanation: '0.4 is the same as 0.40, which is largest.',
              explanationBm: '0.4 sama dengan 0.40, iaitu paling besar.',
            ),
          ],
        ),
      ],
    ),
    const Topic(
      id: 'percentages_y4',
      title: 'Percentages',
      titleBm: 'Peratus',
      area: 'Percentages in real life',
      yearLevel: 4,
      progress: 0,
      mastery: 'Locked',
      subtopics: [
        Subtopic(
          id: 'percentage_meaning',
          title: 'Meaning of Percentage',
          titleBm: 'Maksud Peratus',
          order: 1,
          description: 'Connect percentage with parts out of 100.',
          descriptionBm: 'Hubungkan peratus dengan bahagian daripada 100.',
          questions: [
            QuizQuestion(
              subtopicId: 'percentage_meaning',
              question: '50% is the same as which fraction?',
              options: ['1/4', '1/3', '1/2', '3/4'],
              answerIndex: 2,
              explanation: '50% means half of the whole.',
            ),
          ],
        ),
        Subtopic(
          id: 'percentage_of_quantity',
          title: 'Percentage of Quantity',
          titleBm: 'Peratus daripada Kuantiti',
          order: 2,
          description: 'Find common percentages of a number.',
          descriptionBm: 'Cari peratus lazim daripada suatu nombor.',
          questions: [
            QuizQuestion(
              subtopicId: 'percentage_of_quantity',
              question: 'What is 25% of 80?',
              options: ['10', '20', '25', '40'],
              answerIndex: 1,
              explanation: '25% is one quarter. One quarter of 80 is 20.',
            ),
          ],
        ),
      ],
    ),
    const Topic(
      id: 'money_y4',
      title: 'Money',
      titleBm: 'Wang',
      area: 'Money and daily spending',
      yearLevel: 4,
      progress: 0,
      mastery: 'Locked',
      subtopics: [
        Subtopic(
          id: 'money_addition',
          title: 'Add Money',
          titleBm: 'Tambah Wang',
          order: 1,
          description: 'Add ringgit and sen in daily spending.',
          descriptionBm: 'Tambah ringgit dan sen dalam perbelanjaan harian.',
          questions: [
            QuizQuestion(
              subtopicId: 'money_addition',
              question:
                  'A pencil costs RM1.25 and an eraser costs RM0.50. What is the total?',
              questionBm:
                  'Sebatang pensel berharga RM1.25 dan pemadam berharga RM0.50. Berapakah jumlahnya?',
              options: ['RM1.50', 'RM1.75', 'RM2.25', 'RM0.75'],
              optionsBm: ['RM1.50', 'RM1.75', 'RM2.25', 'RM0.75'],
              answerIndex: 1,
              explanation: 'RM1.25 + RM0.50 = RM1.75.',
              explanationBm: 'RM1.25 + RM0.50 = RM1.75.',
            ),
          ],
        ),
        Subtopic(
          id: 'money_change',
          title: 'Find Change',
          titleBm: 'Cari Baki Wang',
          order: 2,
          description: 'Subtract spending from the amount paid.',
          descriptionBm: 'Tolak perbelanjaan daripada jumlah bayaran.',
          questions: [
            QuizQuestion(
              subtopicId: 'money_change',
              question: 'You pay RM10 for an item costing RM6.40. What is the change?',
              questionBm:
                  'Anda membayar RM10 untuk barang berharga RM6.40. Berapakah bakinya?',
              options: ['RM2.60', 'RM3.60', 'RM4.40', 'RM16.40'],
              optionsBm: ['RM2.60', 'RM3.60', 'RM4.40', 'RM16.40'],
              answerIndex: 1,
              explanation: 'RM10.00 - RM6.40 = RM3.60.',
              explanationBm: 'RM10.00 - RM6.40 = RM3.60.',
            ),
          ],
        ),
      ],
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
  final bool persistQuizResults;
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
  bool isLoadingOasisProgress = false;
  bool loadedOasisProgressFromFirebase = false;
  String? oasisProgressMessage;
  String currentStudentId = demoStudentId;
  String? currentStudentEmail;
  String studentName = 'Aiman';
  int yearLevel = 4;
  String language = 'English';
  bool missionReminders = true;
  bool eyeComfortMode = false;
  bool soundEnabled = true;
  bool accessibilityMode = false;
  int screenTimeLimitMinutes = 30;
  int crystals = 124;
  int mutualAidEnergy = 36;
  int? latestFractionsScore;
  final Set<String> claimedRecommendedMissionTopicIds = <String>{};
  final Set<String> _unlockedTopicIds = <String>{};
  final Set<String> _unlockedSubtopicIds = <String>{};
  final List<AiDiagnosis> aiDiagnoses = <AiDiagnosis>[];
  final List<OasisArea> oasisAreas = [
    const OasisArea(
      id: 'fraction_bridge',
      title: 'Fraction Bridge',
      topic: 'Fractions',
      description: 'Reconnect oasis paths and learning routes.',
      resource: OasisResource.crystals,
      repairCost: 30,
      progress: 0.25,
      markerPosition: Offset(0.40, 0.55),
      damagedImage: 'assets/illustrations/oasis_parts/fraction_bridge_damaged.png',
      repairingImage: 'assets/illustrations/oasis_parts/fraction_bridge_repairing_50.png',
      restoredImage: 'assets/illustrations/oasis_parts/fraction_bridge_restored_100.png',
      homeOverlay50: 'assets/illustrations/oasis_parts/home_overlay_fraction_bridge_50.png',
      homeOverlay100: 'assets/illustrations/oasis_parts/home_overlay_fraction_bridge_100.png',
    ),
    const OasisArea(
      id: 'decimal_waterway',
      title: 'Decimal Waterway',
      topic: 'Decimals',
      description: 'Bring clean water back to the oasis.',
      resource: OasisResource.crystals,
      repairCost: 35,
      progress: 0,
      markerPosition: Offset(0.72, 0.35),
      damagedImage: 'assets/illustrations/oasis_parts/decimal_waterway_damaged.png',
      repairingImage: 'assets/illustrations/oasis_parts/decimal_waterway_repairing_50.png',
      restoredImage: 'assets/illustrations/oasis_parts/decimal_waterway_restored_100.png',
      homeOverlay50: 'assets/illustrations/oasis_parts/home_overlay_decimal_waterway_50.png',
      homeOverlay100: 'assets/illustrations/oasis_parts/home_overlay_decimal_waterway_100.png',
    ),
    const OasisArea(
      id: 'percentage_garden',
      title: 'Percentage Garden',
      topic: 'Percentages',
      description: 'Grow green areas through steady practice.',
      resource: OasisResource.crystals,
      repairCost: 40,
      progress: 0,
      markerPosition: Offset(0.14, 0.70),
      damagedImage: 'assets/illustrations/oasis_parts/percentage_garden_damaged.png',
      repairingImage: 'assets/illustrations/oasis_parts/percentage_garden_repairing_50.png',
      restoredImage: 'assets/illustrations/oasis_parts/percentage_garden_restored_100.png',
      homeOverlay50: 'assets/illustrations/oasis_parts/home_overlay_percentage_garden_50.png',
      homeOverlay100: 'assets/illustrations/oasis_parts/home_overlay_percentage_garden_100.png',
    ),
    const OasisArea(
      id: 'market_corner',
      title: 'Market Corner',
      topic: 'Money',
      description: 'Rebuild facilities with helpful community energy.',
      resource: OasisResource.mutualAid,
      repairCost: 20,
      progress: 0.25,
      markerPosition: Offset(0.78, 0.62),
      damagedImage: 'assets/illustrations/oasis_parts/market_corner_damaged.png',
      repairingImage: 'assets/illustrations/oasis_parts/market_corner_repairing_50.png',
      restoredImage: 'assets/illustrations/oasis_parts/market_corner_restored_100.png',
      homeOverlay50: 'assets/illustrations/oasis_parts/home_overlay_market_corner_50.png',
      homeOverlay100: 'assets/illustrations/oasis_parts/home_overlay_market_corner_100.png',
    ),
  ];
  final List<QuizAttempt> attempts = [];

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

  int get estimatedScreenTimeMinutesToday {
    final minutes = (currentYearAttempts.length * 8) + (completedQuizzes > 0 ? 4 : 0);
    return minutes.clamp(0, screenTimeLimitMinutes).toInt();
  }

  double get screenTimeProgress {
    if (screenTimeLimitMinutes <= 0) return 0;
    return (estimatedScreenTimeMinutesToday / screenTimeLimitMinutes)
        .clamp(0.0, 1.0)
        .toDouble();
  }

  bool get isBahasaMelayu => language == 'Bahasa Melayu';

  Locale get locale => isBahasaMelayu ? const Locale('ms') : const Locale('en');

  AiDiagnosis? get recommendedAiDiagnosis => _recommendedAiDiagnosis();

  List<Subtopic> subtopicsForTopic(Topic topic) {
    final subtopics = topic.subtopics;
    if (subtopics.isNotEmpty) {
      return List<Subtopic>.from(subtopics)
        ..sort((a, b) => a.order.compareTo(b.order));
    }
    if (topic.questions.isEmpty) return const <Subtopic>[];
    return [
      Subtopic(
        id: '${topic.id}_practice',
        title: topic.title,
        titleBm: topic.titleBm,
        order: 1,
        description: topic.area,
        descriptionBm: topic.areaBm,
        progress: topic.progress,
        mastery: topic.mastery,
        questions: topic.questions,
      ),
    ];
  }

  bool isTopicUnlocked(Topic topic) {
    final topicIndex = topics.indexWhere((item) => item.id == topic.id);
    if (topicIndex <= 0) return true;
    if (_unlockedTopicIds.contains(topic.id)) return true;
    final previousTopic = topics[topicIndex - 1];
    return _isTopicComplete(previousTopic);
  }

  String? lockedReasonForTopic(Topic topic) {
    if (isTopicUnlocked(topic)) return null;
    final topicIndex = topics.indexWhere((item) => item.id == topic.id);
    if (topicIndex <= 0) return null;
    final previousTopic = topics[topicIndex - 1];
    return t(
      'Complete ${previousTopic.title} first.',
      'Lengkapkan ${previousTopic.titleBm} dahulu.',
    );
  }

  bool isSubtopicUnlocked(Topic topic, Subtopic subtopic) {
    final subtopics = subtopicsForTopic(topic);
    final subtopicIndex = subtopics.indexWhere((item) => item.id == subtopic.id);
    if (subtopicIndex <= 0) return true;
    if (_unlockedSubtopicIds.contains(_subtopicUnlockKey(topic, subtopic))) {
      return true;
    }
    return subtopics[subtopicIndex - 1].isComplete;
  }

  String? lockedReasonForSubtopic(Topic topic, Subtopic subtopic) {
    if (isSubtopicUnlocked(topic, subtopic)) return null;
    final subtopics = subtopicsForTopic(topic);
    final subtopicIndex = subtopics.indexWhere((item) => item.id == subtopic.id);
    if (subtopicIndex <= 0) return null;
    final previousSubtopic = subtopics[subtopicIndex - 1];
    return t(
      'Complete ${previousSubtopic.title} with more than 50%.',
      'Lengkapkan ${previousSubtopic.titleBm} dengan lebih daripada 50%.',
    );
  }

  Future<void> loadSavedAppPreferences() async {
    final preferences = await SharedPreferences.getInstance();
    selectedTab = (preferences.getInt(_lastTabKey) ?? selectedTab).clamp(0, 2);
    language = preferences.getString(_languageKey) ?? language;
    missionReminders =
        preferences.getBool(_missionRemindersKey) ?? missionReminders;
    eyeComfortMode = preferences.getBool(_eyeComfortKey) ?? eyeComfortMode;
    soundEnabled = preferences.getBool(_soundEnabledKey) ?? soundEnabled;
    accessibilityMode =
        preferences.getBool(_accessibilityModeKey) ?? accessibilityMode;
    screenTimeLimitMinutes =
        preferences.getInt(_screenTimeLimitKey) ?? screenTimeLimitMinutes;
    screenTimeLimitMinutes = screenTimeLimitMinutes.clamp(15, 120).toInt();
    _unlockedTopicIds
      ..clear()
      ..addAll(preferences.getStringList(_unlockedTopicIdsKey) ?? const []);
    _unlockedSubtopicIds
      ..clear()
      ..addAll(preferences.getStringList(_unlockedSubtopicIdsKey) ?? const []);
    claimedRecommendedMissionTopicIds
      ..clear()
      ..addAll(
        preferences.getStringList(_claimedMissionTopicIdsKey) ?? const [],
      );
    _restoreSavedAttempts(preferences.getString(_savedAttemptsKey));
    _applyAttemptProgressToTopics();
    _recordUnlockedProgression();
    notifyListeners();
  }

  Future<void> saveAppSession() async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setInt(_lastTabKey, selectedTab.clamp(0, 2));
    await preferences.setString(_languageKey, language);
    await preferences.setBool(_missionRemindersKey, missionReminders);
    await preferences.setBool(_eyeComfortKey, eyeComfortMode);
    await preferences.setBool(_soundEnabledKey, soundEnabled);
    await preferences.setBool(_accessibilityModeKey, accessibilityMode);
    await preferences.setInt(_screenTimeLimitKey, screenTimeLimitMinutes);
    await preferences.setStringList(
      _unlockedTopicIdsKey,
      _unlockedTopicIds.toList()..sort(),
    );
    await preferences.setStringList(
      _unlockedSubtopicIdsKey,
      _unlockedSubtopicIds.toList()..sort(),
    );
    await preferences.setStringList(
      _claimedMissionTopicIdsKey,
      claimedRecommendedMissionTopicIds.toList()..sort(),
    );
    await preferences.setString(_savedAttemptsKey, _encodedSavedAttempts());
  }

  void _saveAppSessionInBackground() {
    unawaited(saveAppSession().catchError((_) {}));
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
        _applyAttemptProgressToTopics();
        _recordUnlockedProgression();
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
    final completedCompletions = currentYearAttempts
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
    if (oasisAreas.isEmpty) return 0;
    final areaAverage =
        oasisAreas.fold<double>(0, (sum, area) => sum + area.progress) /
        oasisAreas.length;
    return areaAverage.clamp(0.0, 1.0);
  }

  Map<String, double> get oasisAreaProgress => {
    for (final area in oasisAreas) area.id: area.progress.clamp(0.0, 1.0),
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
    if (persistQuizResults) {
      unawaited(_saveOasisProgressToFirebase());
    }
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
    if (persistQuizResults) {
      unawaited(loadOasisProgressFromFirebase());
      unawaited(loadParentDashboardFromFirebase());
    }
  }

  void updateLanguage(String value) {
    language = value;
    notifyListeners();
    unawaited(saveAppSession());
    if (persistQuizResults) {
      unawaited(_saveOasisProgressToFirebase());
    }
  }

  void updateMissionReminders(bool value) {
    missionReminders = value;
    notifyListeners();
    unawaited(saveAppSession());
    if (persistQuizResults) {
      unawaited(_saveOasisProgressToFirebase());
    }
  }

  void updateEyeComfortMode(bool value) {
    eyeComfortMode = value;
    notifyListeners();
    unawaited(saveAppSession());
    if (persistQuizResults) {
      unawaited(_saveOasisProgressToFirebase());
    }
  }

  void updateSoundEnabled(bool value) {
    soundEnabled = value;
    notifyListeners();
    unawaited(saveAppSession());
  }

  void updateAccessibilityMode(bool value) {
    accessibilityMode = value;
    notifyListeners();
    unawaited(saveAppSession());
  }

  void updateScreenTimeLimit(int minutes) {
    screenTimeLimitMinutes = minutes.clamp(15, 120).toInt();
    notifyListeners();
    unawaited(saveAppSession());
  }

  QuizReward saveQuizResult({
    required String topicId,
    String? subtopicId,
    required int correctCount,
    required int totalQuestions,
    int timeTakenSeconds = 0,
  }) {
    final topicIndex = topics.indexWhere((topic) => topic.id == topicId);
    if (topicIndex == -1) {
      throw ArgumentError('Unknown topicId: $topicId');
    }

    final topic = topics[topicIndex];
    if (totalQuestions <= 0) {
      throw ArgumentError('totalQuestions must be greater than zero.');
    }

    final normalizedCorrectCount = correctCount.clamp(0, totalQuestions);
    final score = ((normalizedCorrectCount / totalQuestions) * 100).round();
    final earnedCrystals = _calculateCrystals(score, normalizedCorrectCount);
    final newMastery = _masteryForScore(score);
    final subtopicUpdate = _updatedSubtopicsForResult(
      topic: topic,
      subtopicId: subtopicId,
      score: score,
      mastery: newMastery,
    );
    final updatedSubtopics = subtopicUpdate.$1;
    final updatedSubtopic = subtopicUpdate.$2;
    final learningProgress = subtopicId == null
        ? mathMax(topic.progress, score / 100)
        : _topicProgressFromSubtopics(updatedSubtopics);
    final topicMastery = subtopicId == null
        ? newMastery
        : _topicMasteryFromSubtopics(updatedSubtopics);

    latestFractionsScore = topicId == 'fractions_y4'
        ? score
        : latestFractionsScore;
    crystals += earnedCrystals;
    topics[topicIndex] = topic.copyWith(
      progress: learningProgress,
      mastery: topicMastery,
      subtopics: updatedSubtopics,
    );
    _recordUnlockedProgression();
    final attemptId = 'attempt_${DateTime.now().millisecondsSinceEpoch}';
    final attempt = QuizAttempt(
      id: attemptId,
      topicId: topic.id,
      topicTitle: topic.title,
      subtopicId: updatedSubtopic?.id,
      subtopicTitle: updatedSubtopic?.title,
      yearLevel: topic.yearLevel,
      score: score,
      correctCount: normalizedCorrectCount,
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
      newMastery: subtopicId == null ? newMastery : topicMastery,
      encouragement: _encouragementForScore(score),
    );

    notifyListeners();
    _saveAppSessionInBackground();
    if (persistQuizResults) {
      unawaited(_saveQuizResultToFirebase(attempt, timeTakenSeconds));
      unawaited(_saveOasisProgressToFirebase());
    }
    return reward;
  }

  (List<Subtopic>, Subtopic?) _updatedSubtopicsForResult({
    required Topic topic,
    required String? subtopicId,
    required int score,
    required String mastery,
  }) {
    final subtopics = subtopicsForTopic(topic);
    if (subtopics.isEmpty || subtopicId == null) return (subtopics, null);

    final subtopicIndex = subtopics.indexWhere(
      (subtopic) => subtopic.id == subtopicId,
    );
    if (subtopicIndex == -1) {
      throw ArgumentError('Unknown subtopicId: $subtopicId');
    }

    final selected = subtopics[subtopicIndex];
    final updated = selected.copyWith(
      progress: mathMax(selected.progress, score / 100),
      mastery: mastery,
    );
    subtopics[subtopicIndex] = updated;
    return (subtopics, updated);
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
        totalSubtopicCount: _totalSubtopicCountForTopic(attempt.topicId),
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
          _applyAttemptProgressToTopics();
          _recordUnlockedProgression();
          unawaited(saveAppSession());
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

  Future<void> loadOasisProgressFromFirebase() async {
    if (!persistQuizResults || isLoadingOasisProgress) return;

    isLoadingOasisProgress = true;
    oasisProgressMessage = null;
    notifyListeners();

    try {
      final repository = _learningRepository ?? LearningRepository();
      final snapshot = await repository.fetchOasisProgress(
        studentId: currentStudentId,
      );

      if (snapshot == null || snapshot.isEmpty) {
        loadedOasisProgressFromFirebase = false;
        oasisProgressMessage = t(
          'Using local oasis progress until Firebase has saved progress.',
          'Menggunakan kemajuan oasis setempat sehingga Firebase mempunyai kemajuan tersimpan.',
        );
      } else {
        _applyOasisProgress(snapshot);
        await saveAppSession();
        loadedOasisProgressFromFirebase = true;
        oasisProgressMessage = t(
          'Loaded oasis progress from Firebase.',
          'Kemajuan oasis dimuat daripada Firebase.',
        );
      }
    } catch (_) {
      loadedOasisProgressFromFirebase = false;
      oasisProgressMessage = t(
        'Firebase oasis progress unavailable. Local progress is still kept.',
        'Kemajuan oasis Firebase tidak tersedia. Kemajuan setempat masih dikekalkan.',
      );
    } finally {
      isLoadingOasisProgress = false;
      notifyListeners();
    }
  }

  Future<void> _saveOasisProgressToFirebase() async {
    try {
      final repository = _learningRepository ?? LearningRepository();
      await repository.saveOasisProgress(
        studentId: currentStudentId,
        yearLevel: yearLevel,
        crystals: crystals,
        mutualAidEnergy: mutualAidEnergy,
        language: language,
        missionReminders: missionReminders,
        eyeComfortMode: eyeComfortMode,
        repairedAreas: oasisAreaProgress,
      );
      loadedOasisProgressFromFirebase = true;
      oasisProgressMessage = t(
        'Oasis progress synced to Firebase.',
        'Kemajuan oasis disegerakkan ke Firebase.',
      );
    } catch (_) {
      loadedOasisProgressFromFirebase = false;
      oasisProgressMessage = t(
        'Firebase oasis sync failed. Local progress is still kept.',
        'Penyegerakan oasis Firebase gagal. Kemajuan setempat masih dikekalkan.',
      );
    } finally {
      notifyListeners();
    }
  }

  void _applyOasisProgress(OasisProgressSnapshot snapshot) {
    if (snapshot.crystals != null) {
      crystals = snapshot.crystals!.clamp(0, _maxStoredResource).toInt();
    }
    if (snapshot.mutualAidEnergy != null) {
      mutualAidEnergy = snapshot.mutualAidEnergy!
          .clamp(0, _maxStoredResource)
          .toInt();
    }
    if (snapshot.language != null) {
      language = snapshot.language!;
    }
    if (snapshot.missionReminders != null) {
      missionReminders = snapshot.missionReminders!;
    }
    if (snapshot.eyeComfortMode != null) {
      eyeComfortMode = snapshot.eyeComfortMode!;
    }
    for (var index = 0; index < oasisAreas.length; index += 1) {
      final area = oasisAreas[index];
      // Force reset for testing!
      oasisAreas[index] = area.copyWith(
        progress: 0.0,
      );
    }
    
    // Give plenty of resources to test
    crystals = 800;
    mutualAidEnergy = 800;
    
    // Sync the reset back to Firebase
    unawaited(_saveOasisProgressToFirebase());
  }

  bool claimRecommendedMissionReward() {
    final mission = recommendedMission;
    if (!mission.isReadyToClaim) return false;

    crystals += mission.rewardCrystals;
    claimedRecommendedMissionTopicIds.add(mission.topicId);
    notifyListeners();
    _saveAppSessionInBackground();
    if (persistQuizResults) {
      unawaited(_saveOasisProgressToFirebase());
    }
    return true;
  }

  double mathMax(double a, double b) => a > b ? a : b;

  bool _isTopicComplete(Topic topic) {
    final subtopics = subtopicsForTopic(topic);
    if (subtopics.isNotEmpty) {
      return subtopics.every((subtopic) => subtopic.isComplete);
    }
    if (topic.mastery == 'Moderate' || topic.mastery == 'Strong') {
      return true;
    }
    return topic.progress > 0.5;
  }

  double _topicProgressFromSubtopics(List<Subtopic> subtopics) {
    if (subtopics.isEmpty) return 0;
    final completedCount = subtopics
        .where((subtopic) => subtopic.isComplete)
        .length;
    return completedCount / subtopics.length;
  }

  String _topicMasteryFromSubtopics(List<Subtopic> subtopics) {
    if (subtopics.isEmpty) return 'New';
    final progress = _topicProgressFromSubtopics(subtopics);
    if (progress >= .8) return 'Strong';
    if (progress > .5) return 'Moderate';
    final hasModerateWork = subtopics.any(
      (subtopic) =>
          subtopic.mastery == 'Moderate' || subtopic.mastery == 'Strong',
    );
    return hasModerateWork ? 'Moderate' : 'Weak';
  }

  List<Topic> _mergeTopicProgress(List<Topic> sourceTopics) {
    final localTopics = _localTopicsForYear(yearLevel);
    final merged = <Topic>[];
    for (final localTopic in localTopics) {
      final sourceMatches = sourceTopics.where(
        (sourceTopic) => sourceTopic.id == localTopic.id,
      );
      if (sourceMatches.isEmpty) {
        merged.add(localTopic);
        continue;
      }

      final sourceTopic = sourceMatches.first;
      merged.add(
        sourceTopic.copyWith(
          progress: localTopic.progress,
          mastery: localTopic.mastery,
          subtopics: sourceTopic.subtopics.isEmpty
              ? localTopic.subtopics
              : sourceTopic.subtopics,
        ),
      );
    }

    for (final sourceTopic in sourceTopics) {
      if (merged.any((topic) => topic.id == sourceTopic.id)) continue;
      merged.add(
        sourceTopic.copyWith(
          progress: sourceTopic.progress,
          mastery: sourceTopic.mastery,
        ),
      );
    }
    return merged;
  }

  void _resetTopicsForCurrentYear() {
    topics
      ..clear()
      ..addAll(_mergeTopicProgress(_localTopicsForYear(yearLevel)));
    _applyAttemptProgressToTopics();
    _recordUnlockedProgression();
    topicLoadMessage = null;
    loadedTopicsFromFirebase = false;
  }

  void _applyAttemptProgressToTopics() {
    final yearAttempts = currentYearAttempts;
    if (yearAttempts.isEmpty) return;

    for (var topicIndex = 0; topicIndex < topics.length; topicIndex += 1) {
      final topic = topics[topicIndex];
      final topicAttempts = yearAttempts
          .where((attempt) => attempt.topicId == topic.id)
          .toList(growable: false);
      if (topicAttempts.isEmpty) continue;

      final subtopics = subtopicsForTopic(topic);
      if (subtopics.isNotEmpty) {
        final updatedSubtopics = subtopics
            .map((subtopic) {
              final subtopicAttempts = topicAttempts
                  .where((attempt) => attempt.subtopicId == subtopic.id)
                  .toList(growable: false);
              if (subtopicAttempts.isEmpty) return subtopic;

              final bestAttempt = _bestAttempt(subtopicAttempts);
              return subtopic.copyWith(
                progress: mathMax(subtopic.progress, bestAttempt.score / 100),
                mastery: bestAttempt.mastery,
              );
            })
            .toList(growable: false);

        topics[topicIndex] = topic.copyWith(
          progress: _topicProgressFromSubtopics(updatedSubtopics),
          mastery: _topicMasteryFromSubtopics(updatedSubtopics),
          subtopics: updatedSubtopics,
        );
        continue;
      }

      final bestAttempt = _bestAttempt(topicAttempts);
      topics[topicIndex] = topic.copyWith(
        progress: mathMax(topic.progress, bestAttempt.score / 100),
        mastery: bestAttempt.mastery,
      );
    }
  }

  QuizAttempt _bestAttempt(List<QuizAttempt> sourceAttempts) {
    return sourceAttempts.reduce((best, attempt) {
      if (attempt.score != best.score) {
        return attempt.score > best.score ? attempt : best;
      }
      return attempt.createdAt.isAfter(best.createdAt) ? attempt : best;
    });
  }

  void _restoreSavedAttempts(String? encodedAttempts) {
    if (encodedAttempts == null || encodedAttempts.trim().isEmpty) return;

    try {
      final decoded = jsonDecode(encodedAttempts);
      if (decoded is! List) return;

      final restoredAttempts = decoded
          .map(_attemptFromSavedJson)
          .whereType<QuizAttempt>()
          .toList(growable: false)
        ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
      if (restoredAttempts.isEmpty) return;

      attempts
        ..clear()
        ..addAll(restoredAttempts);
    } catch (_) {
      return;
    }
  }

  String _encodedSavedAttempts() {
    final encodedAttempts = attempts.map(_attemptToJson).toList(growable: false);
    return jsonEncode(encodedAttempts);
  }

  Map<String, Object?> _attemptToJson(QuizAttempt attempt) {
    return {
      'id': attempt.id,
      'topicId': attempt.topicId,
      'topicTitle': attempt.topicTitle,
      'subtopicId': attempt.subtopicId,
      'subtopicTitle': attempt.subtopicTitle,
      'yearLevel': attempt.yearLevel,
      'score': attempt.score,
      'correctCount': attempt.correctCount,
      'totalQuestions': attempt.totalQuestions,
      'earnedCrystals': attempt.earnedCrystals,
      'mastery': attempt.mastery,
      'createdAt': attempt.createdAt.toIso8601String(),
    };
  }

  QuizAttempt? _attemptFromSavedJson(Object? value) {
    if (value is! Map) return null;

    final id = value['id'];
    final topicId = value['topicId'];
    final topicTitle = value['topicTitle'];
    final yearLevel = value['yearLevel'];
    final score = value['score'];
    final correctCount = value['correctCount'];
    final totalQuestions = value['totalQuestions'];
    final earnedCrystals = value['earnedCrystals'];
    final mastery = value['mastery'];
    final createdAt = value['createdAt'];

    if (id is! String ||
        topicId is! String ||
        topicTitle is! String ||
        yearLevel is! num ||
        score is! num ||
        correctCount is! num ||
        totalQuestions is! num ||
        earnedCrystals is! num ||
        mastery is! String ||
        createdAt is! String) {
      return null;
    }

    final parsedCreatedAt = DateTime.tryParse(createdAt);
    if (parsedCreatedAt == null) return null;

    final subtopicId = value['subtopicId'];
    final subtopicTitle = value['subtopicTitle'];
    return QuizAttempt(
      id: id,
      topicId: topicId,
      topicTitle: topicTitle,
      subtopicId: subtopicId is String && subtopicId.isNotEmpty
          ? subtopicId
          : null,
      subtopicTitle: subtopicTitle is String && subtopicTitle.isNotEmpty
          ? subtopicTitle
          : null,
      yearLevel: yearLevel.round().clamp(4, 6).toInt(),
      score: score.round().clamp(0, 100).toInt(),
      correctCount: correctCount.round(),
      totalQuestions: totalQuestions.round() <= 0
          ? 1
          : totalQuestions.round(),
      earnedCrystals: earnedCrystals.round(),
      mastery: mastery,
      createdAt: parsedCreatedAt,
    );
  }

  bool _recordUnlockedProgression() {
    var changed = false;
    for (var topicIndex = 1; topicIndex < topics.length; topicIndex += 1) {
      if (_isTopicComplete(topics[topicIndex - 1])) {
        changed = _unlockedTopicIds.add(topics[topicIndex].id) || changed;
      }
    }

    for (final topic in topics) {
      final subtopics = subtopicsForTopic(topic);
      for (var index = 1; index < subtopics.length; index += 1) {
        if (subtopics[index - 1].isComplete) {
          changed =
              _unlockedSubtopicIds.add(
                _subtopicUnlockKey(topic, subtopics[index]),
              ) ||
              changed;
        }
      }
    }
    return changed;
  }

  String _subtopicUnlockKey(Topic topic, Subtopic subtopic) {
    return '${topic.id}::${subtopic.id}';
  }

  int _totalSubtopicCountForTopic(String topicId) {
    final matches = topics.where((topic) => topic.id == topicId);
    if (matches.isEmpty) return 0;
    return subtopicsForTopic(matches.first).length;
  }

  String _currentRecommendedMissionTopicId() {
    final aiRecommendation = _recommendedAiDiagnosis();
    if (aiRecommendation != null) {
      return aiRecommendation.topicId;
    }

    final yearAttempts = currentYearAttempts;
    if (yearAttempts.isEmpty) return _firstUnclaimedTopicId();

    final grouped = <String, List<QuizAttempt>>{};
    for (final attempt in yearAttempts) {
      if (!topics.any((topic) => topic.id == attempt.topicId)) continue;
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

    for (final diagnosis in _latestAiDiagnosesForCurrentYear()) {
      final score = diagnosis.priorityScore;
      if (score > selectedScore ||
          (score == selectedScore &&
              selected != null &&
              diagnosis.isNewerThan(selected))) {
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
    final reasons = diagnosis.explanationReasons;
    final reason = reasons.isEmpty
        ? t(
            '$topicTitle is flagged by the Grey Box AI with $weaknessPercent% weakness risk and $masteryPercent% BKT mastery.',
            '$topicTitle ditandakan oleh AI Grey Box dengan risiko kelemahan $weaknessPercent% dan penguasaan BKT $masteryPercent%.',
          )
        : t(
            '$topicTitle is flagged by the Grey Box AI because ${reasons.take(3).join(', ')}.',
            '$topicTitle ditandakan oleh AI Grey Box kerana ${reasons.take(3).join(', ')}.',
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
    for (final diagnosis in _latestAiDiagnosesForCurrentYear()) {
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

  List<AiDiagnosis> _latestAiDiagnosesForCurrentYear() {
    final latestByTopic = <String, AiDiagnosis>{};
    for (final diagnosis in aiDiagnoses) {
      if (diagnosis.yearLevel != null && diagnosis.yearLevel != yearLevel) {
        continue;
      }
      if (!topics.any((topic) => topic.id == diagnosis.topicId)) continue;

      final existing = latestByTopic[diagnosis.topicId];
      if (existing == null || diagnosis.isNewerThan(existing)) {
        latestByTopic[diagnosis.topicId] = diagnosis;
      }
    }
    return latestByTopic.values.toList(growable: false);
  }

  bool canRepair(OasisArea area) {
    if (area.isComplete) return false;
    return switch (area.resource) {
      OasisResource.crystals =>
        area.repairCost > 0 && crystals >= area.repairCost,
      OasisResource.mutualAid =>
        area.repairCost > 0 && mutualAidEnergy >= area.repairCost,
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
    if (persistQuizResults) {
      unawaited(_saveOasisProgressToFirebase());
    }
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
