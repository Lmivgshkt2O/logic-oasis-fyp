import 'package:cloud_firestore/cloud_firestore.dart';

class ForumQuestion {
  const ForumQuestion({
    required this.id,
    required this.authorId,
    required this.title,
    required this.text,
    this.createdAt,
  });

  final String id;
  final String authorId;
  final String title;
  final String text;
  final DateTime? createdAt;

  factory ForumQuestion.fromFirestore(String id, Map<String, dynamic> data) =>
      ForumQuestion(
        id: id,
        authorId: data['authorId'] as String? ?? '',
        title: data['title'] as String? ?? '',
        text: data['text'] as String? ?? '',
        createdAt: (data['createdAt'] as Timestamp?)?.toDate(),
      );
}
