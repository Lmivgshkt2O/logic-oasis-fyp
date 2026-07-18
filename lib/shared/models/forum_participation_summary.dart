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
    this.lastParticipationAt,
    this.updatedAt,
  });

  final String studentId;
  final int questionsPostedCount;
  final int answersSubmittedCount;
  final int acceptedAnswersCount;
  final int helpfulReceivedCount;
  final DateTime? lastParticipationAt;
  final DateTime? updatedAt;

  factory ForumParticipationSummary.fromFirestore(
    String studentId,
    Map<String, dynamic> data,
  ) {
    int count(String field) {
      final value = data[field];
      if (value is int && value >= 0) return value;
      if (value is num && value >= 0 && value == value.roundToDouble()) {
        return value.toInt();
      }
      return 0;
    }

    DateTime? timestamp(String field) {
      final value = data[field];
      return value is Timestamp ? value.toDate() : null;
    }

    return ForumParticipationSummary(
      studentId: studentId,
      questionsPostedCount: count('questionsPostedCount'),
      answersSubmittedCount: count('answersSubmittedCount'),
      acceptedAnswersCount: count('acceptedAnswersCount'),
      helpfulReceivedCount: count('helpfulReceivedCount'),
      lastParticipationAt: timestamp('lastParticipationAt'),
      updatedAt: timestamp('updatedAt'),
    );
  }
}
