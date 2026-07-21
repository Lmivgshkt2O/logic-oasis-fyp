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
  });

  final String studentId;
  final String topicId;
  final String subtopicId;
  final int yearLevel;
  final bool completed;
  final String masteryLevel;
  final double bestCorrectRate;

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
}
