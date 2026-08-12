/// One missed question's answer-free review card from a finalized attempt.
///
/// The server builds these in quiz order from the sealed wrong responses plus
/// client-safe question metadata. The payload never contains options, answer
/// indexes, or any correct-answer text.
class QuizReviewItem {
  const QuizReviewItem({
    required this.questionId,
    required this.sequenceIndex,
    required this.questionText,
    required this.questionTextBm,
    this.questionType = '',
    this.questionTypeBm = '',
    required this.reviewFocus,
    required this.reviewFocusBm,
  });

  final String questionId;
  final int sequenceIndex;
  final String questionText;
  final String questionTextBm;
  final String questionType;
  final String questionTypeBm;
  final String reviewFocus;
  final String reviewFocusBm;

  String localizedPrompt(bool isBahasaMelayu) =>
      isBahasaMelayu ? questionTextBm : questionText;

  String localizedType(bool isBahasaMelayu) =>
      isBahasaMelayu ? questionTypeBm : questionType;

  String localizedReviewFocus(bool isBahasaMelayu) =>
      isBahasaMelayu ? reviewFocusBm : reviewFocus;

  factory QuizReviewItem.fromCallableData(Map<Object?, Object?> data) {
    String readString(String key) {
      final value = data[key];
      if (value is String) return value;
      throw FormatException('Missing callable review field: $key');
    }

    final sequenceIndex = data['sequenceIndex'];
    if (sequenceIndex is! int) {
      throw const FormatException(
        'Missing callable review field: sequenceIndex',
      );
    }

    return QuizReviewItem(
      questionId: readString('questionId'),
      sequenceIndex: sequenceIndex,
      questionText: readString('questionText'),
      questionTextBm: readString('questionTextBm'),
      questionType: readString('questionType'),
      questionTypeBm: readString('questionTypeBm'),
      reviewFocus: readString('reviewFocus'),
      reviewFocusBm: readString('reviewFocusBm'),
    );
  }
}
