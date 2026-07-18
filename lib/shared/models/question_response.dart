/// A response whose correctness was returned by the callable backend.
///
/// A pending value deliberately has no correctness or explanation. This keeps
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
    this.explanation,
    this.explanationBm,
    this.validationStatus = 'pending',
  });

  final String sessionId;
  final String questionId;
  final int selectedIndex;
  final int sequenceIndex;
  final String idempotencyKey;
  final String? responseId;
  final bool? isCorrect;
  final String? explanation;
  final String? explanationBm;
  final String validationStatus;

  bool get isValidated => validationStatus == 'validated' && isCorrect != null;
  bool get isPending => !isValidated;

  String localizedExplanation(bool isBahasaMelayu) {
    return isBahasaMelayu
        ? explanationBm ?? explanation ?? ''
        : explanation ?? '';
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
    return QuestionResponse(
      responseId: _string(data['responseId']),
      sessionId: _requiredString(data['sessionId'], 'sessionId'),
      questionId: _requiredString(data['questionId'], 'questionId'),
      selectedIndex: _requiredInt(data['selectedIndex'], 'selectedIndex'),
      sequenceIndex: _requiredInt(data['sequenceIndex'], 'sequenceIndex'),
      idempotencyKey: idempotencyKey,
      isCorrect: data['serverIsCorrect'] as bool?,
      explanation: _string(data['explanation']),
      explanationBm: _string(data['explanationBm']),
      validationStatus: _string(data['validationStatus']) ?? 'pending',
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
