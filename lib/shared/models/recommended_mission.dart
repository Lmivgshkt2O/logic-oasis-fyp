class RecommendedMission {
  const RecommendedMission({
    required this.topicId,
    required this.topicTitle,
    required this.topicTitleBm,
    this.subtopicId = '',
    this.subtopicTitle = '',
    this.subtopicTitleBm = '',
    required this.requiredCompletions,
    required this.completedCompletions,
    required this.rewardCrystals,
    required this.rewardClaimed,
  });

  final String topicId;
  final String topicTitle;
  final String topicTitleBm;
  final String subtopicId;
  final String subtopicTitle;
  final String subtopicTitleBm;
  final int requiredCompletions;
  final int completedCompletions;
  final int rewardCrystals;
  final bool rewardClaimed;

  int get visibleCompletions {
    return completedCompletions.clamp(0, requiredCompletions).toInt();
  }

  bool get isReadyToClaim {
    return completedCompletions >= requiredCompletions && !rewardClaimed;
  }

  bool get isComplete => completedCompletions >= requiredCompletions;
}
