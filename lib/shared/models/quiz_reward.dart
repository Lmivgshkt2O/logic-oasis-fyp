class QuizReward {
  const QuizReward({
    required this.score,
    required this.earnedCrystals,
    required this.previousMastery,
    required this.newMastery,
    required this.encouragement,
    this.previousMasteryPercent = 0,
  });

  final int score;
  final int earnedCrystals;
  final String previousMastery;
  final String newMastery;
  final String encouragement;
  final int previousMasteryPercent;
}
