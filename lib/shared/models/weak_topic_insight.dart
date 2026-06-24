class WeakTopicInsight {
  const WeakTopicInsight({
    required this.topicId,
    required this.topicTitle,
    required this.averageScore,
    required this.attemptCount,
    required this.mastery,
    required this.reason,
    required this.recommendation,
  });

  final String topicId;
  final String topicTitle;
  final int averageScore;
  final int attemptCount;
  final String mastery;
  final String reason;
  final String recommendation;
}
