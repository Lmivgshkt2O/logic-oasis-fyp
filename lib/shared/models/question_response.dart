/// A response whose correctness was returned by the callable backend.
///
/// A pending value deliberately has no correctness or guidance. This keeps
/// the quiz UI from inferring an answer while a network retry is outstanding.
class QuestionResponse {
  const QuestionResponse({
    required this.sessionId,
    required this.questionId,
    required this.selectedIndex,
    required this.sequenceIndex,
    required this.idempotencyKey,
    this.responseId,
    this.isCorrect,
    this.positiveConfirmation,
    this.positiveConfirmationBm,
    this.feedbackHint,
    this.feedbackHintBm,
    this.feedbackExample,
    this.feedbackExampleBm,
    this.reviewFocus,
    this.reviewFocusBm,
    this.validationStatus = 'pending',
  });

  final String sessionId;
  final String questionId;
  final int selectedIndex;
  final int sequenceIndex;
  final String idempotencyKey;
  final String? responseId;
  final bool? isCorrect;
  final String? positiveConfirmation;
  final String? positiveConfirmationBm;
  final String? feedbackHint;
  final String? feedbackHintBm;
  final String? feedbackExample;
  final String? feedbackExampleBm;
  final String? reviewFocus;
  final String? reviewFocusBm;
  final String validationStatus;

  bool get isValidated => validationStatus == 'validated' && isCorrect != null;
  bool get isPending => !isValidated;

  String localizedPositiveConfirmation(bool isBahasaMelayu) {
    return isBahasaMelayu
        ? positiveConfirmationBm ?? positiveConfirmation ?? ''
        : positiveConfirmation ?? '';
  }

  String? localizedFeedbackHint(bool isBahasaMelayu) =>
      isBahasaMelayu ? (feedbackHintBm ?? feedbackHint) : feedbackHint;

  String? localizedFeedbackExample(bool isBahasaMelayu) => isBahasaMelayu
      ? (feedbackExampleBm ?? feedbackExample)
      : feedbackExample;

  String? localizedReviewFocus(bool isBahasaMelayu) =>
      isBahasaMelayu ? (reviewFocusBm ?? reviewFocus) : reviewFocus;

  /// The bounded, answer-free lines shown after a wrong answer: the authored
  /// hint, an optional different-number worked example, and the review focus.
  List<String> localizedFeedbackLines(bool isBahasaMelayu) {
    final hint = localizedFeedbackHint(isBahasaMelayu);
    final example = localizedFeedbackExample(isBahasaMelayu);
    final focus = localizedReviewFocus(isBahasaMelayu);
    return <String>[
      if (hint != null && hint.isNotEmpty) hint,
      if (example != null && example.isNotEmpty) 'Example: $example',
      if (focus != null && focus.isNotEmpty) focus,
    ];
  }

  Map<String, Object> toSubmissionData({
    required int responseTimeMs,
    required int hintCount,
  }) {
    final normalizedResponseTimeMs = responseTimeMs < 0 ? 0 : responseTimeMs;
    final normalizedHintCount = hintCount < 0 ? 0 : hintCount;
    return <String, Object>{
      'sessionId': sessionId,
      'questionId': questionId,
      // Android callable transport can decode Dart integers inconsistently.
      // The backend accepts only digit strings and normalizes them to trusted
      // integers before validating the session and answer key.
      'selectedIndex': selectedIndex.toString(),
      'sequenceIndex': sequenceIndex.toString(),
      'idempotencyKey': idempotencyKey,
      'responseTimeMs': normalizedResponseTimeMs.toString(),
      'hintCount': normalizedHintCount.toString(),
    };
  }

  factory QuestionResponse.fromCallableData(
    Map<Object?, Object?> data, {
    required String idempotencyKey,
  }) {
    final isCorrect = data['serverIsCorrect'] as bool?;
    final positiveConfirmation = _string(data['positiveConfirmation']);
    final positiveConfirmationBm = _string(data['positiveConfirmationBm']);
    final feedbackHint = _string(data['feedbackHint']);
    final feedbackHintBm = _string(data['feedbackHintBm']);
    final feedbackExample = _string(data['feedbackExample']);
    final feedbackExampleBm = _string(data['feedbackExampleBm']);
    final reviewFocus = _string(data['reviewFocus']);
    final reviewFocusBm = _string(data['reviewFocusBm']);
    final validationStatus = _string(data['validationStatus']) ?? 'pending';
    if (validationStatus == 'validated' && isCorrect != null) {
      final hasHint =
          (feedbackHint?.isNotEmpty ?? false) &&
          (feedbackHintBm?.isNotEmpty ?? false);
      final hasReviewFocus =
          (reviewFocus?.isNotEmpty ?? false) &&
          (reviewFocusBm?.isNotEmpty ?? false);
      final hasExample = feedbackExample != null;
      final hasExampleBm = feedbackExampleBm != null;
      final examplePairIsValid = hasExample == hasExampleBm;
      final hasConfirmation =
          (positiveConfirmation?.isNotEmpty ?? false) &&
          (positiveConfirmationBm?.isNotEmpty ?? false);
      if (isCorrect
          ? !hasConfirmation || hasHint || hasReviewFocus
          : !hasHint ||
                !hasReviewFocus ||
                !examplePairIsValid ||
                hasConfirmation) {
        throw const FormatException('Invalid secure quiz feedback payload.');
      }
    }
    return QuestionResponse(
      responseId: _string(data['responseId']),
      sessionId: _requiredString(data['sessionId'], 'sessionId'),
      questionId: _requiredString(data['questionId'], 'questionId'),
      selectedIndex: _requiredInt(data['selectedIndex'], 'selectedIndex'),
      sequenceIndex: _requiredInt(data['sequenceIndex'], 'sequenceIndex'),
      idempotencyKey: idempotencyKey,
      isCorrect: isCorrect,
      positiveConfirmation: positiveConfirmation,
      positiveConfirmationBm: positiveConfirmationBm,
      feedbackHint: feedbackHint,
      feedbackHintBm: feedbackHintBm,
      feedbackExample: feedbackExample,
      feedbackExampleBm: feedbackExampleBm,
      reviewFocus: reviewFocus,
      reviewFocusBm: reviewFocusBm,
      validationStatus: validationStatus,
    );
  }

  static String _requiredString(Object? value, String field) {
    if (value is String && value.isNotEmpty) return value;
    throw FormatException('Missing callable response field: $field');
  }

  static int _requiredInt(Object? value, String field) {
    if (value is int) return value;
    if (value is num) return value.round();
    throw FormatException('Missing callable response field: $field');
  }

  static String? _string(Object? value) => value is String ? value : null;
}
