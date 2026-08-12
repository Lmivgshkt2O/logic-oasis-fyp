/// A bounded, server-owned learning projection. It deliberately excludes raw
/// responses, answer keys, and any AI/model evidence.
class TrustedSubtopicProgress {
  const TrustedSubtopicProgress({
    required this.studentId,
    required this.topicId,
    required this.subtopicId,
    required this.yearLevel,
    required this.completed,
    required this.masteryLevel,
    required this.bestCorrectRate,
    this.attempted = false,
    this.accessUnlocked = false,
    this.masteryProbability,
    this.evidenceLevel,
    this.recommendedLearningAction,
    this.recommendationBasis,
    this.recommendationTargetTopicId,
    this.recommendationTargetSubtopicId,
    this.projectionStatus,
    this.lastCorrectRate,
  });

  final String studentId;
  final String topicId;
  final String subtopicId;
  final int yearLevel;
  final bool completed;
  final String masteryLevel;
  final double bestCorrectRate;
  final bool attempted;
  final bool accessUnlocked;
  final double? masteryProbability;
  final String? evidenceLevel;
  final String? recommendedLearningAction;
  final String? recommendationBasis;
  final String? recommendationTargetTopicId;
  final String? recommendationTargetSubtopicId;
  final String? projectionStatus;
  final double? lastCorrectRate;

  factory TrustedSubtopicProgress.fromFirestore(Map<String, dynamic> data) {
    final studentId = data['studentId'];
    final topicId = data['topicId'];
    final subtopicId = data['subtopicId'];
    final yearLevel = data['yearLevel'];
    if (studentId is! String ||
        topicId is! String ||
        subtopicId is! String ||
        yearLevel is! num ||
        studentId.isEmpty ||
        topicId.isEmpty ||
        subtopicId.isEmpty) {
      throw const FormatException('Invalid trusted subtopic progress record.');
    }
    final completed = data['completed'];
    final masteryLevel = data['masteryLevel'];
    final rate = data['bestCorrectRate'];
    const masteryLevels = <String>{'New', 'Weak', 'Moderate', 'Strong'};
    return TrustedSubtopicProgress(
      studentId: studentId,
      topicId: topicId,
      subtopicId: subtopicId,
      yearLevel: _wholeYearLevel(yearLevel),
      completed: _requiredCompleted(completed),
      masteryLevel: _requiredMasteryLevel(masteryLevel, masteryLevels),
      bestCorrectRate: _requiredRate(rate),
      attempted: data['attempted'] is bool ? data['attempted'] as bool : false,
      accessUnlocked:
          data['accessUnlocked'] is bool
          ? data['accessUnlocked'] as bool
          : false,
      masteryProbability: _optionalRate(data['masteryProbability']),
      evidenceLevel: _optionalString(data['evidenceLevel']),
      recommendedLearningAction: _optionalString(
        data['recommendedLearningAction'],
      ),
      recommendationBasis: _optionalString(data['recommendationBasis']),
      recommendationTargetTopicId: _optionalString(
        data['recommendationTargetTopicId'],
      ),
      recommendationTargetSubtopicId: _optionalString(
        data['recommendationTargetSubtopicId'],
      ),
      projectionStatus: _optionalString(data['projectionStatus']),
      lastCorrectRate: _optionalRate(data['lastCorrectRate']),
    );
  }

  static int _wholeYearLevel(num value) {
    if (value is double && value != value.truncateToDouble()) {
      throw const FormatException('Invalid trusted progress year level.');
    }
    return value.toInt();
  }

  static bool _requiredCompleted(Object? value) {
    if (value is bool) return value;
    throw const FormatException('Missing trusted progress completion status.');
  }

  static String _requiredMasteryLevel(
    Object? value,
    Set<String> allowedValues,
  ) {
    if (value is String && allowedValues.contains(value)) return value;
    throw const FormatException('Invalid trusted progress mastery level.');
  }

  static double _requiredRate(Object? value) {
    if (value is num && value >= 0 && value <= 1) return value.toDouble();
    throw const FormatException('Invalid trusted progress rate.');
  }

  static double? _optionalRate(Object? value) {
    if (value == null) return null;
    if (value is num && value >= 0 && value <= 1) return value.toDouble();
    throw const FormatException('Invalid trusted progress probability.');
  }

  static String? _optionalString(Object? value) {
    if (value == null) return null;
    if (value is String && value.isNotEmpty) return value;
    throw const FormatException('Invalid trusted progress field.');
  }
}
