import 'package:cloud_firestore/cloud_firestore.dart';

class ForumAnswerFeedback {
  const ForumAnswerFeedback({
    required this.state,
    required this.label,
    required this.message,
    this.probability,
    this.modelVersion,
    this.calibrationState,
  });

  final String state;
  final String label;
  final String message;
  final double? probability;
  final String? modelVersion;
  final String? calibrationState;

  factory ForumAnswerFeedback.fromFirestore(Map<String, dynamic>? data) {
    final rawProbability = data?['probability'];
    return ForumAnswerFeedback(
      state: data?['state'] as String? ?? 'queued',
      label: data?['label'] as String? ?? 'uncertain',
      message: data?['message'] as String? ?? 'Your answer is being reviewed.',
      probability: rawProbability is num ? rawProbability.toDouble() : null,
      modelVersion: data?['modelVersion'] as String?,
      calibrationState: data?['calibrationState'] as String?,
    );
  }
}

class ForumAnswer {
  const ForumAnswer({
    required this.id,
    required this.questionId,
    required this.authorId,
    required this.text,
    required this.feedback,
    this.createdAt,
    this.acceptedAt,
    this.revision = 1,
  });

  final String id;
  final String questionId;
  final String authorId;
  final String text;
  final ForumAnswerFeedback feedback;
  final DateTime? createdAt;
  final DateTime? acceptedAt;
  final int revision;

  factory ForumAnswer.fromFirestore(String id, Map<String, dynamic> data) =>
      ForumAnswer(
        id: id,
        questionId: data['questionId'] as String? ?? '',
        authorId: data['authorId'] as String? ?? '',
        text: data['text'] as String? ?? '',
        feedback: ForumAnswerFeedback.fromFirestore(
          data['aiFeedback'] as Map<String, dynamic>?,
        ),
        createdAt: (data['createdAt'] as Timestamp?)?.toDate(),
        acceptedAt: (data['acceptedAt'] as Timestamp?)?.toDate(),
        revision: data['revision'] as int? ?? 1,
      );
}
