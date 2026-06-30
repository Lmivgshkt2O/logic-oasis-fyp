import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

void main() {
  test('recommended mission follows the weakest quiz topic', () {
    final state = AppState();

    expect(state.recommendedMission.topicId, 'decimals_y4');
    expect(state.recommendedMission.topicTitle, 'Decimals');
    expect(state.recommendedMission.visibleCompletions, 1);
    expect(state.recommendedMission.isReadyToClaim, isFalse);
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
}
