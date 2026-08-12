/// The typed next step returned by the result route.
///
/// `repeat` and `advance` come from the server's BKT recommendation; `back`
/// is the learner's explicit return to the subtopic page. The client never
/// chooses a bank: `SubtopicPage` resolves these actions through the existing
/// callable session service.
enum NextLearningActionKind { repeat, advance, back }

class NextLearningAction {
  const NextLearningAction._({
    required this.kind,
    this.targetTopicId,
    this.targetSubtopicId,
    this.difficultyLabel,
    this.recommendationBasis,
  });

  const NextLearningAction.repeat({
    required String difficultyLabel,
    String? recommendationBasis,
  }) : this._(
         kind: NextLearningActionKind.repeat,
         difficultyLabel: difficultyLabel,
         recommendationBasis: recommendationBasis,
       );

  const NextLearningAction.advance({
    String? targetTopicId,
    String? targetSubtopicId,
    String difficultyLabel = 'Easy',
    String? recommendationBasis,
  }) : this._(
         kind: NextLearningActionKind.advance,
         targetTopicId: targetTopicId,
         targetSubtopicId: targetSubtopicId,
         difficultyLabel: difficultyLabel,
         recommendationBasis: recommendationBasis,
       );

  const NextLearningAction.back() : this._(kind: NextLearningActionKind.back);

  final NextLearningActionKind kind;
  final String? targetTopicId;
  final String? targetSubtopicId;
  final String? difficultyLabel;
  final String? recommendationBasis;

  bool get isRepeat => kind == NextLearningActionKind.repeat;
  bool get isAdvance => kind == NextLearningActionKind.advance;
  bool get isBack => kind == NextLearningActionKind.back;

  bool get isCorrectRateFallback =>
      recommendationBasis == 'correct_rate_fallback';
}
