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
    this.guidedSteps = const <String>[],
    this.guidedStepsBm = const <String>[],
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
  final List<String> guidedSteps;
  final List<String> guidedStepsBm;
  final String validationStatus;

  bool get isValidated => validationStatus == 'validated' && isCorrect != null;
  bool get isPending => !isValidated;

  String localizedPositiveConfirmation(bool isBahasaMelayu) {
    return isBahasaMelayu
        ? positiveConfirmationBm ?? positiveConfirmation ?? ''
        : positiveConfirmation ?? '';
  }

  List<String> localizedGuidedSteps(bool isBahasaMelayu) =>
      isBahasaMelayu && guidedStepsBm.isNotEmpty ? guidedStepsBm : guidedSteps;

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
    final guidedSteps = _stringList(data['guidedSteps']);
    final guidedStepsBm = _stringList(data['guidedStepsBm']);
    final validationStatus = _string(data['validationStatus']) ?? 'pending';
    if (validationStatus == 'validated' && isCorrect != null) {
      final hasGuidance =
          guidedSteps.length >= 2 &&
          guidedSteps.length <= 5 &&
          guidedSteps.length == guidedStepsBm.length;
      final hasConfirmation =
          (positiveConfirmation?.isNotEmpty ?? false) &&
          (positiveConfirmationBm?.isNotEmpty ?? false);
      if (isCorrect
          ? !hasConfirmation || guidedSteps.isNotEmpty
          : !hasGuidance || hasConfirmation) {
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
      guidedSteps: guidedSteps,
      guidedStepsBm: guidedStepsBm,
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

  static List<String> _stringList(Object? value) {
    if (value == null) return const <String>[];
    if (value is! List ||
        value.any((item) => item is! String || item.isEmpty)) {
      throw const FormatException('Invalid callable guidance field.');
    }
    return value.cast<String>();
  }
}
