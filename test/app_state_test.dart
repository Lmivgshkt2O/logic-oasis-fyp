import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/models/adaptive_assignment.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/question_bank.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  test('recommended mission follows the weakest quiz topic', () {
    final state = AppState();

    expect(state.recommendedMission.topicId, 'whole_numbers_y4');
    expect(state.recommendedMission.topicTitle, 'Whole Numbers up to 100 000');
    expect(state.recommendedMission.visibleCompletions, 0);
    expect(state.recommendedMission.isReadyToClaim, isFalse);
  });

  test('AI diagnosis overrides rule-based weak topic fallback', () {
    final state = AppState();

    state.saveQuizResult(
      topicId: 'whole_numbers_y4',
      subtopicId: 'read_write_numbers',
      correctCount: 9,
      totalQuestions: 10,
    );
    state.aiDiagnoses.add(
      AiDiagnosis(
        attemptId: 'ai_fractions_focus',
        studentId: AppState.demoStudentId,
        sourceAttemptSequence: 1,
        analysisState: 'completed',
        displayCode: 'analysis_complete',
        topicId: 'fractions_y4',
        yearLevel: 4,
        masteryProbability: 0.34,
        weakTopicPriorityScore: 0.82,
        evidenceLevel: 'preliminary',
        observationCount: 4,
        rankingVersion: 'weak-topic-ranking-v1',
        assignment: const AdaptiveAssignment(
          id: 'assignment_fractions_focus',
          subtopicId: 'equivalent_fractions',
          bankId: 'fractions_equivalent_easy_v1',
          difficulty: QuestionDifficulty.easy,
          policyVersion: 'adaptive-policy-v1',
          reasonCode: 'practice_equivalent_fractions',
          reasonText: 'Practise equivalent fractions.',
          evidenceCount: 4,
          usedBktFallback: false,
        ),
        updatedAt: DateTime(2026, 7, 7, 10),
      ),
    );

    expect(state.recommendedAiDiagnosis!.topicId, 'fractions_y4');
    expect(state.weakTopicInsight.topicId, 'fractions_y4');
    expect(state.weakTopicInsight.reason, contains('Grey Box AI'));
    expect(state.recommendedMission.topicId, 'fractions_y4');
  });

  test('year 4 FYP1 content exposes one secure adaptive-bank subtopic', () {
    final state = AppState();
    final wholeNumbers = state.topics.firstWhere(
      (topic) => topic.id == 'whole_numbers_y4',
    );
    final subtopics = state.subtopicsForTopic(wholeNumbers);

    expect(subtopics, hasLength(5));
    final adaptiveSubtopic = subtopics.first;
    expect(adaptiveSubtopic.id, 'read_write_numbers');
    expect(adaptiveSubtopic.questions, hasLength(24));
    expect(
      adaptiveSubtopic.questions.map((question) => question.bankId).toSet(),
      containsAll(<String>[
        'y4_whole_read_write_easy_v1',
        'y4_whole_read_write_moderate_v1',
        'y4_whole_read_write_hard_v1',
      ]),
    );
  });

  test('cold-start selection returns a five-question Easy form', () {
    final state = AppState();
    final wholeNumbers = state.topics.firstWhere(
      (topic) => topic.id == 'whole_numbers_y4',
    );
    final readWrite = state.subtopicsForTopic(wholeNumbers).first;

    final form = state.selectQuestionForm(
      topic: wholeNumbers,
      subtopic: readWrite,
    );

    expect(form, hasLength(5));
    expect(form.map((question) => question.id).toSet(), hasLength(5));
    expect(form.map((question) => question.bankId).toSet(), <String>{
      'y4_whole_read_write_easy_v1',
    });
  });

  test('recommended mission becomes claimable after enough topic attempts', () {
    final state = AppState();
    final missionTopicId = state.recommendedMission.topicId;

    state.saveQuizResult(
      topicId: missionTopicId,
      correctCount: 2,
      totalQuestions: 5,
    );

    expect(state.recommendedMission.topicId, missionTopicId);
    expect(state.recommendedMission.visibleCompletions, 1);
    expect(state.recommendedMission.isReadyToClaim, isFalse);

    state.saveQuizResult(
      topicId: missionTopicId,
      correctCount: 3,
      totalQuestions: 5,
    );

    expect(state.recommendedMission.visibleCompletions, 2);
    expect(state.recommendedMission.isReadyToClaim, isTrue);
  });

  test('recommended mission reward can only be claimed once', () {
    final state = AppState();
    final missionTopicId = state.recommendedMission.topicId;

    state.saveQuizResult(
      topicId: missionTopicId,
      correctCount: 2,
      totalQuestions: 5,
    );
    state.saveQuizResult(
      topicId: missionTopicId,
      correctCount: 3,
      totalQuestions: 5,
    );

    final crystalsBeforeClaim = state.crystals;

    expect(state.claimRecommendedMissionReward(), isTrue);
    expect(
      state.crystals,
      crystalsBeforeClaim + AppState.recommendedMissionRewardCrystals,
    );
    expect(state.recommendedMission.rewardClaimed, isTrue);

    expect(state.claimRecommendedMissionReward(), isFalse);
    expect(
      state.crystals,
      crystalsBeforeClaim + AppState.recommendedMissionRewardCrystals,
    );
  });

  test(
    'claimed recommended mission reward is restored from saved session',
    () async {
      SharedPreferences.setMockInitialValues({
        'logic_oasis_claimed_mission_topics': <String>['whole_numbers_y4'],
      });
      final state = AppState();

      state.saveQuizResult(
        topicId: 'whole_numbers_y4',
        correctCount: 5,
        totalQuestions: 5,
      );
      state.saveQuizResult(
        topicId: 'whole_numbers_y4',
        correctCount: 5,
        totalQuestions: 5,
      );

      await state.loadSavedAppPreferences();

      expect(state.recommendedMission.isReadyToClaim, isFalse);
      expect(state.recommendedMission.rewardClaimed, isTrue);
      expect(state.claimRecommendedMissionReward(), isFalse);
    },
  );

  test(
    'settings controls persist sound accessibility screen time and eye mode',
    () async {
      SharedPreferences.setMockInitialValues({});
      final state = AppState();

      expect(state.eyeComfortMode, isFalse);
      state.updateSoundEnabled(false);
      state.updateAccessibilityMode(true);
      state.updateMissionReminders(false);
      state.updateScreenTimeLimit(45);
      state.updateEyeComfortMode(true);
      await state.saveAppSession();

      final restoredState = AppState();
      await restoredState.loadSavedAppPreferences();

      expect(restoredState.soundEnabled, isFalse);
      expect(restoredState.accessibilityMode, isTrue);
      expect(restoredState.missionReminders, isFalse);
      expect(restoredState.screenTimeLimitMinutes, 45);
      expect(restoredState.eyeComfortMode, isTrue);
    },
  );

  test(
    'quiz attempts restore topic and subtopic progress after restart',
    () async {
      SharedPreferences.setMockInitialValues({});
      final state = AppState();

      state.saveQuizResult(
        topicId: 'whole_numbers_y4',
        subtopicId: 'read_write_numbers',
        correctCount: 6,
        totalQuestions: 10,
      );
      await state.saveAppSession();

      final restoredState = AppState();
      await restoredState.loadSavedAppPreferences();
      final wholeNumbers = restoredState.topics.firstWhere(
        (topic) => topic.id == 'whole_numbers_y4',
      );
      final readWrite = restoredState
          .subtopicsForTopic(wholeNumbers)
          .firstWhere((subtopic) => subtopic.id == 'read_write_numbers');

      expect(restoredState.recentAttempts, hasLength(1));
      expect(
        restoredState.recentAttempts.first.subtopicId,
        'read_write_numbers',
      );
      expect(readWrite.progress, 0.6);
      expect(readWrite.mastery, 'Moderate');
      expect(wholeNumbers.progress, 0.2);
      expect(restoredState.averageScore, 60);
    },
  );

  test('quiz result creates a valid first attempt for the selected topic', () {
    final state = AppState();
    final beforeCount = state.attempts
        .where((attempt) => attempt.topicId == 'whole_numbers_y4')
        .length;

    final reward = state.saveQuizResult(
      topicId: 'whole_numbers_y4',
      correctCount: 5,
      totalQuestions: 5,
      timeTakenSeconds: 90,
    );

    final latest = state.latestAttempt!;
    expect(latest.topicId, 'whole_numbers_y4');
    expect(latest.yearLevel, 4);
    expect(latest.score, 100);
    expect(latest.correctCount, 5);
    expect(latest.totalQuestions, 5);
    expect(latest.mastery, 'Strong');
    expect(reward.score, 100);
    expect(
      state.attempts.where((attempt) => attempt.topicId == 'whole_numbers_y4'),
      hasLength(beforeCount + 1),
    );
  });

  test('subtopics unlock sequentially after previous subtopic completion', () {
    final state = AppState();
    final wholeNumbers = state.topics.firstWhere(
      (topic) => topic.id == 'whole_numbers_y4',
    );
    final subtopics = state.subtopicsForTopic(wholeNumbers);

    expect(state.isSubtopicUnlocked(wholeNumbers, subtopics[0]), isTrue);
    expect(state.isSubtopicUnlocked(wholeNumbers, subtopics[1]), isFalse);
  });

  test('subtopic quiz result updates selected subtopic and topic progress', () {
    final state = AppState();

    final reward = state.saveQuizResult(
      topicId: 'whole_numbers_y4',
      subtopicId: 'read_write_numbers',
      correctCount: 8,
      totalQuestions: 10,
    );
    final topic = state.topics.firstWhere(
      (topic) => topic.id == 'whole_numbers_y4',
    );
    final subtopics = state.subtopicsForTopic(topic);

    expect(reward.score, 80);
    expect(state.latestAttempt!.subtopicId, 'read_write_numbers');
    expect(subtopics.first.mastery, 'Strong');
    expect(subtopics.first.isComplete, isTrue);
    expect(topic.progress, 0.2);
    expect(state.isSubtopicUnlocked(topic, subtopics[1]), isTrue);
  });

  test('main topic stays locked until all previous subtopics are complete', () {
    final state = AppState();

    state.saveQuizResult(
      topicId: 'whole_numbers_y4',
      subtopicId: 'read_write_numbers',
      correctCount: 8,
      totalQuestions: 10,
    );

    final fractions = state.topics.firstWhere(
      (topic) => topic.id == 'fractions_y4',
    );
    final wholeNumbers = state.topics.firstWhere(
      (topic) => topic.id == 'whole_numbers_y4',
    );

    expect(wholeNumbers.mastery, 'Moderate');
    expect(wholeNumbers.progress, 0.2);
    expect(state.isTopicUnlocked(fractions), isFalse);
  });

  test('earned unlocks remain open after a lower retry', () {
    final state = AppState();
    final wholeNumbers = state.topics.firstWhere(
      (topic) => topic.id == 'whole_numbers_y4',
    );

    state.saveQuizResult(
      topicId: 'whole_numbers_y4',
      subtopicId: 'read_write_numbers',
      correctCount: 6,
      totalQuestions: 10,
    );

    var refreshedTopic = state.topics.firstWhere(
      (topic) => topic.id == wholeNumbers.id,
    );
    var subtopics = state.subtopicsForTopic(refreshedTopic);
    expect(state.isSubtopicUnlocked(refreshedTopic, subtopics[1]), isTrue);

    state.saveQuizResult(
      topicId: 'whole_numbers_y4',
      subtopicId: 'read_write_numbers',
      correctCount: 0,
      totalQuestions: 10,
    );

    refreshedTopic = state.topics.firstWhere(
      (topic) => topic.id == wholeNumbers.id,
    );
    subtopics = state.subtopicsForTopic(refreshedTopic);
    expect(subtopics.first.mastery, 'Weak');
    expect(state.isSubtopicUnlocked(refreshedTopic, subtopics[1]), isTrue);
  });

  test(
    'saved unlocks remain open even before current progress qualifies',
    () async {
      SharedPreferences.setMockInitialValues({
        'logic_oasis_unlocked_topics': <String>['fractions_y4'],
        'logic_oasis_unlocked_subtopics': <String>[
          'whole_numbers_y4::place_digit_value',
        ],
      });
      final state = AppState();

      await state.loadSavedAppPreferences();

      final wholeNumbers = state.topics.firstWhere(
        (topic) => topic.id == 'whole_numbers_y4',
      );
      final subtopics = state.subtopicsForTopic(wholeNumbers);
      final fractions = state.topics.firstWhere(
        (topic) => topic.id == 'fractions_y4',
      );

      expect(subtopics.first.progress, 0);
      expect(state.isSubtopicUnlocked(wholeNumbers, subtopics[1]), isTrue);
      expect(fractions.mastery, 'Locked');
      expect(state.isTopicUnlocked(fractions), isTrue);
    },
  );

  test('main topics unlock only after previous topic completion', () {
    final state = AppState();
    final fractions = state.topics.firstWhere(
      (topic) => topic.id == 'fractions_y4',
    );

    expect(state.isTopicUnlocked(fractions), isFalse);

    for (final subtopicId in [
      'read_write_numbers',
      'place_digit_value',
      'compare_order_numbers',
      'odd_even_numbers',
      'number_patterns',
    ]) {
      state.saveQuizResult(
        topicId: 'whole_numbers_y4',
        subtopicId: subtopicId,
        correctCount: 6,
        totalQuestions: 10,
      );
    }

    expect(state.isTopicUnlocked(fractions), isTrue);
  });

  test('repeated attempt updates topic progress without duplicate logic', () {
    final state = AppState();

    state.saveQuizResult(
      topicId: 'whole_numbers_y4',
      correctCount: 1,
      totalQuestions: 5,
    );
    state.saveQuizResult(
      topicId: 'whole_numbers_y4',
      correctCount: 4,
      totalQuestions: 5,
    );

    final wholeNumberAttempts = state.attempts
        .where((attempt) => attempt.topicId == 'whole_numbers_y4')
        .toList();
    final wholeNumbersTopic = state.topics.firstWhere(
      (topic) => topic.id == 'whole_numbers_y4',
    );

    expect(wholeNumberAttempts.first.score, 80);
    expect(wholeNumberAttempts.first.mastery, 'Strong');
    expect(wholeNumberAttempts, hasLength(2));
    expect(wholeNumbersTopic.mastery, 'Strong');
    expect(wholeNumbersTopic.progress, 0.8);
  });

  test('weak and strong attempts use clean score boundaries', () {
    final state = AppState();

    final weakReward = state.saveQuizResult(
      topicId: 'whole_numbers_y4',
      correctCount: -2,
      totalQuestions: 5,
    );
    final strongReward = state.saveQuizResult(
      topicId: 'whole_numbers_y4',
      correctCount: 10,
      totalQuestions: 5,
    );

    expect(weakReward.score, 0);
    expect(state.attempts[1].correctCount, 0);
    expect(state.attempts[1].mastery, 'Weak');
    expect(strongReward.score, 100);
    expect(state.attempts.first.correctCount, 5);
    expect(state.attempts.first.mastery, 'Strong');
  });

  test('switching topics keeps attempts attached to the correct topic', () {
    final state = AppState();

    state.saveQuizResult(
      topicId: 'whole_numbers_y4',
      correctCount: 7,
      totalQuestions: 10,
    );
    state.saveQuizResult(
      topicId: 'fractions_y4',
      correctCount: 3,
      totalQuestions: 10,
    );

    expect(state.latestAttempt!.topicId, 'fractions_y4');
    expect(state.latestAttempt!.score, 30);
    expect(
      state.attempts.where((attempt) => attempt.topicId == 'whole_numbers_y4'),
      hasLength(1),
    );
    expect(
      state.attempts.where((attempt) => attempt.topicId == 'fractions_y4'),
      hasLength(1),
    );
  });

  test('quiz result rejects empty question sets', () {
    final state = AppState();

    expect(
      () => state.saveQuizResult(
        topicId: 'whole_numbers_y4',
        correctCount: 0,
        totalQuestions: 0,
      ),
      throwsArgumentError,
    );
  });

  test('oasis repair deducts crystals and clamps area progress', () {
    final state = AppState();
    final bridgeBefore = state.oasisAreas.firstWhere(
      (area) => area.id == 'fraction_bridge',
    );
    final crystalsBefore = state.crystals;

    expect(state.canRepair(bridgeBefore), isTrue);
    expect(state.repairOasisArea('fraction_bridge'), isTrue);

    final bridgeAfter = state.oasisAreas.firstWhere(
      (area) => area.id == 'fraction_bridge',
    );
    expect(state.crystals, crystalsBefore - bridgeBefore.repairCost);
    expect(bridgeAfter.progress, 0.5);

    expect(state.repairOasisArea('fraction_bridge'), isTrue);
    expect(state.repairOasisArea('fraction_bridge'), isTrue);
    expect(state.repairOasisArea('fraction_bridge'), isFalse);

    final completeBridge = state.oasisAreas.firstWhere(
      (area) => area.id == 'fraction_bridge',
    );
    expect(completeBridge.progress, 1.0);
    expect(state.canRepair(completeBridge), isFalse);
  });

  test('oasis repair uses mutual aid and fails without enough resource', () {
    final state = AppState();
    final marketBefore = state.oasisAreas.firstWhere(
      (area) => area.id == 'market_corner',
    );
    final energyBefore = state.mutualAidEnergy;

    expect(state.repairOasisArea('market_corner'), isTrue);

    final marketAfter = state.oasisAreas.firstWhere(
      (area) => area.id == 'market_corner',
    );
    expect(state.mutualAidEnergy, energyBefore - marketBefore.repairCost);
    expect(marketAfter.progress, 0.5);

    expect(state.repairOasisArea('market_corner'), isFalse);
    expect(state.mutualAidEnergy, energyBefore - marketBefore.repairCost);
    expect(state.repairOasisArea('missing_area'), isFalse);
  });
}
