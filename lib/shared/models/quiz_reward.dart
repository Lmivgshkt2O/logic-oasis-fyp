class QuizReward {
  const QuizReward({
    required this.score,
    required this.earnedCrystals,
    required this.previousMastery,
    required this.newMastery,
    required this.encouragement,
  });

  final int score;
  final int earnedCrystals;
  final String previousMastery;
  final String newMastery;
  final String encouragement;
}
