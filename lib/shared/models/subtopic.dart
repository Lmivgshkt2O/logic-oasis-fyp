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
    this.completed = false,
    this.accessUnlocked = false,
    this.masteryProbability,
    this.evidenceLevel,
    this.recommendedLearningAction,
    this.recommendationBasis,
    this.recommendationTargetTopicId,
    this.recommendationTargetSubtopicId,
    this.projectionStatus,
    this.bestCorrectRate,
    this.lastCorrectRate,
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
  /// Server-derived mastery outcome (BKT completion), never a client score.
  final bool completed;
  /// Unlocks after any valid finalized attempt, independent of completion.
  final bool accessUnlocked;
  /// Safe BKT posterior from the server; null while pending or on fallback.
  final double? masteryProbability;
  final String? evidenceLevel;
  final String? recommendedLearningAction;
  final String? recommendationBasis;
  final String? recommendationTargetTopicId;
  final String? recommendationTargetSubtopicId;
  final String? projectionStatus;
  final double? bestCorrectRate;
  final double? lastCorrectRate;
  final List<QuizQuestion> questions;

  bool get isComplete => completed;

  bool get isAttempted => accessUnlocked || completed;

  bool get isAnalysisPending =>
      isAttempted &&
      (projectionStatus == 'finalized_pending_ai' ||
          recommendationBasis == 'provisional_pending_ai');

  bool get usesCorrectRateFallback =>
      recommendationBasis == 'correct_rate_fallback';

  /// The fraction shown on the subtopic card: BKT mastery when available,
  /// the trusted quiz-progress rate only for the labelled fallback, and no
  /// invented value while analysis is pending or before the first attempt.
  double? get displayedMasteryFraction {
    if (masteryProbability != null) return masteryProbability;
    if (usesCorrectRateFallback) return bestCorrectRate;
    return null;
  }

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
    bool? completed,
    bool? accessUnlocked,
    double? masteryProbability,
    String? evidenceLevel,
    String? recommendedLearningAction,
    String? recommendationBasis,
    String? recommendationTargetTopicId,
    String? recommendationTargetSubtopicId,
    String? projectionStatus,
    double? bestCorrectRate,
    double? lastCorrectRate,
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
      completed: completed ?? this.completed,
      accessUnlocked: accessUnlocked ?? this.accessUnlocked,
      masteryProbability: masteryProbability ?? this.masteryProbability,
      evidenceLevel: evidenceLevel ?? this.evidenceLevel,
      recommendedLearningAction:
          recommendedLearningAction ?? this.recommendedLearningAction,
      recommendationBasis: recommendationBasis ?? this.recommendationBasis,
      recommendationTargetTopicId:
          recommendationTargetTopicId ?? this.recommendationTargetTopicId,
      recommendationTargetSubtopicId:
          recommendationTargetSubtopicId ?? this.recommendationTargetSubtopicId,
      projectionStatus: projectionStatus ?? this.projectionStatus,
      bestCorrectRate: bestCorrectRate ?? this.bestCorrectRate,
      lastCorrectRate: lastCorrectRate ?? this.lastCorrectRate,
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
