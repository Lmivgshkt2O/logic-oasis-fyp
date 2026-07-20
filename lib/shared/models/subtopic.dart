import 'package:logic_oasis/shared/models/quiz_question.dart';

class Subtopic {
  const Subtopic({
    required this.id,
    required this.title,
    required this.titleBm,
    required this.order,
    this.description = '',
    this.descriptionBm,
    this.standardCode,
    this.sourcePages,
    this.skillIds = const [],
    this.contentVersion,
    this.activeBankCount = 0,
    this.progress = 0,
    this.mastery = 'New',
    this.questions = const [],
  });

  final String id;
  final String title;
  final String titleBm;
  final int order;
  final String description;
  final String? descriptionBm;
  final String? standardCode;
  final String? sourcePages;
  final List<String> skillIds;
  final String? contentVersion;
  final int activeBankCount;
  final double progress;
  final String mastery;
  final List<QuizQuestion> questions;

  bool get isComplete =>
      progress > 0.5 || mastery == 'Moderate' || mastery == 'Strong';

  Subtopic copyWith({
    String? id,
    String? title,
    String? titleBm,
    int? order,
    String? description,
    String? descriptionBm,
    String? standardCode,
    String? sourcePages,
    List<String>? skillIds,
    String? contentVersion,
    int? activeBankCount,
    double? progress,
    String? mastery,
    List<QuizQuestion>? questions,
  }) {
    return Subtopic(
      id: id ?? this.id,
      title: title ?? this.title,
      titleBm: titleBm ?? this.titleBm,
      order: order ?? this.order,
      description: description ?? this.description,
      descriptionBm: descriptionBm ?? this.descriptionBm,
      standardCode: standardCode ?? this.standardCode,
      sourcePages: sourcePages ?? this.sourcePages,
      skillIds: skillIds ?? this.skillIds,
      contentVersion: contentVersion ?? this.contentVersion,
      activeBankCount: activeBankCount ?? this.activeBankCount,
      progress: progress ?? this.progress,
      mastery: mastery ?? this.mastery,
      questions: questions ?? this.questions,
    );
  }

  String localizedTitle(bool isBahasaMelayu) {
    return isBahasaMelayu ? titleBm : title;
  }

  String localizedDescription(bool isBahasaMelayu) {
    if (!isBahasaMelayu) return description;
    if (descriptionBm != null && descriptionBm!.trim().isNotEmpty) {
      return descriptionBm!;
    }
    return description;
  }
}
