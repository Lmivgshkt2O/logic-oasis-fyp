class QuizCompletion {
  const QuizCompletion({
    required this.correctCount,
    required this.timeTakenSeconds,
    this.attemptId,
    this.sessionId,
    this.totalQuestions,
    this.score,
    this.finalizationStatus = 'finalized',
  });

  final int correctCount;
  final int timeTakenSeconds;
  final String? attemptId;
  final String? sessionId;
  final int? totalQuestions;
  final int? score;
  final String finalizationStatus;

  factory QuizCompletion.fromCallableData(Map<Object?, Object?> data) {
    int readInt(String key) {
      final value = data[key];
      if (value is int) return value;
      if (value is num) return value.round();
      throw FormatException('Missing callable completion field: $key');
    }

    String readString(String key) {
      final value = data[key];
      if (value is String && value.isNotEmpty) return value;
      throw FormatException('Missing callable completion field: $key');
    }

    return QuizCompletion(
      correctCount: readInt('correctCount'),
      totalQuestions: readInt('totalQuestions'),
      score: readInt('score'),
      timeTakenSeconds: 0,
      attemptId: readString('attemptId'),
      sessionId: readString('sessionId'),
      finalizationStatus: readString('finalizationStatus'),
    );
  }
}
