import 'package:logic_oasis/shared/models/quiz_question.dart';

class Topic {
  const Topic({
    required this.id,
    required this.title,
    required this.titleBm,
    required this.area,
    required this.progress,
    required this.mastery,
    required this.questions,
  });

  final String id;
  final String title;
  final String titleBm;
  final String area;
  final double progress;
  final String mastery;
  final List<QuizQuestion> questions;

  Topic copyWith({
    String? id,
    String? title,
    String? titleBm,
    String? area,
    double? progress,
    String? mastery,
    List<QuizQuestion>? questions,
  }) {
    return Topic(
      id: id ?? this.id,
      title: title ?? this.title,
      titleBm: titleBm ?? this.titleBm,
      area: area ?? this.area,
      progress: progress ?? this.progress,
      mastery: mastery ?? this.mastery,
      questions: questions ?? this.questions,
    );
  }
}
