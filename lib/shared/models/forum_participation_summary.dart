import 'package:cloud_firestore/cloud_firestore.dart';

/// The deliberately count-only U10 projection that U9 may display to a
/// student or an actively linked parent. It never carries forum text, peer
/// identities, moderation information, or model output.
class ForumParticipationSummary {
  const ForumParticipationSummary({
    required this.studentId,
    required this.questionsPostedCount,
    required this.answersSubmittedCount,
    required this.acceptedAnswersCount,
    required this.helpfulReceivedCount,
    this.weekStart,
    this.lastParticipationAt,
    this.updatedAt,
  });

  final String studentId;
  final int questionsPostedCount;
  final int answersSubmittedCount;
  final int acceptedAnswersCount;
  final int helpfulReceivedCount;
  final DateTime? weekStart;
  final DateTime? lastParticipationAt;
  final DateTime? updatedAt;

  factory ForumParticipationSummary.fromFirestore(
    String studentId,
    Map<String, dynamic> data,
  ) {
    final storedStudentId = data['studentId'];
    if (storedStudentId is! String ||
        storedStudentId.isEmpty ||
        storedStudentId != studentId) {
      throw const FormatException(
        'Forum participation summary child mismatch.',
      );
    }
    int count(String field) {
      final value = data[field];
      if (value is num && value >= 0 && value == value.roundToDouble()) {
        return value.toInt();
      }
      throw FormatException('Invalid forum participation count: $field');
    }

    DateTime? optionalTimestamp(String field) {
      final value = data[field];
      if (value == null) return null;
      if (value is Timestamp) return value.toDate().toUtc();
      throw FormatException('Invalid forum participation timestamp: $field');
    }

    final weekStart = data['weekStart'];
    if (weekStart is! Timestamp) {
      throw const FormatException(
        'Forum participation summary needs weekStart.',
      );
    }

    return ForumParticipationSummary(
      studentId: studentId,
      questionsPostedCount: count('questionsPostedCount'),
      answersSubmittedCount: count('answersSubmittedCount'),
      acceptedAnswersCount: count('acceptedAnswersCount'),
      helpfulReceivedCount: count('helpfulReceivedCount'),
      weekStart: weekStart.toDate().toUtc(),
      lastParticipationAt: optionalTimestamp('lastParticipationAt'),
      updatedAt: optionalTimestamp('updatedAt'),
    );
  }
}
