class QuizAttempt {
  const QuizAttempt({
    required this.id,
    required this.topicId,
    required this.topicTitle,
    required this.score,
    required this.correctCount,
    required this.totalQuestions,
    required this.earnedCrystals,
    required this.mastery,
    required this.createdAt,
  });

  final String id;
  final String topicId;
  final String topicTitle;
  final int score;
  final int correctCount;
  final int totalQuestions;
  final int earnedCrystals;
  final String mastery;
  final DateTime createdAt;
}
