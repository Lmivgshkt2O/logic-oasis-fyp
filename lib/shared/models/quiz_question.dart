/// A client-readable quiz prompt.
///
/// This model deliberately contains no correct-answer index or explanation.
/// Those fields are held by the server-only `questionAnswerKeys` collection and
/// are returned to the client only after response validation in U3.
class QuizQuestion {
  const QuizQuestion({
    required this.id,
    required this.bankId,
    required this.topicId,
    required this.subtopicId,
    required this.skillId,
    required this.yearLevel,
    required this.difficultyLevel,
    required this.estimatedDifficulty,
    required this.contentVersion,
    required this.language,
    required this.createdAt,
    required this.question,
    required this.questionBm,
    required this.options,
    required this.optionsBm,
    required this.sourceReference,
    this.order,
    this.bloomLevel,
    this.isActive = true,
  });

  final String id;
  final String bankId;
  final String topicId;
  final String subtopicId;
  final String skillId;
  final int yearLevel;
  final String difficultyLevel;
  final double estimatedDifficulty;
  final String contentVersion;
  final String language;
  final String createdAt;
  final String question;
  final String questionBm;
  final List<String> options;
  final List<String> optionsBm;
  final String sourceReference;
  final int? order;
  final String? bloomLevel;
  final bool isActive;

  String localizedQuestion(bool isBahasaMelayu) {
    return isBahasaMelayu ? questionBm : question;
  }

  List<String> localizedOptions(bool isBahasaMelayu) {
    return isBahasaMelayu ? optionsBm : options;
  }

  /// Parses a prompt returned by `startQuizSession`.
  ///
  /// The callable response has the same safe contract as the public
  /// `questions` collection: answer indexes and explanations are absent.
  factory QuizQuestion.fromCallableData(Map<Object?, Object?> data) {
    return QuizQuestion(
      id: _requiredString(data['questionId'], 'questionId'),
      bankId: _requiredString(data['bankId'], 'bankId'),
      topicId: _requiredString(data['topicId'], 'topicId'),
      subtopicId: _requiredString(data['subtopicId'], 'subtopicId'),
      skillId: _requiredString(data['skillId'], 'skillId'),
      yearLevel: _requiredInt(data['yearLevel'], 'yearLevel'),
      difficultyLevel: _requiredString(
        data['difficultyLevel'],
        'difficultyLevel',
      ),
      estimatedDifficulty: _requiredDouble(
        data['estimatedDifficulty'],
        'estimatedDifficulty',
      ),
      contentVersion: _requiredString(data['contentVersion'], 'contentVersion'),
      language: _requiredString(data['language'], 'language'),
      createdAt: _requiredString(data['createdAt'], 'createdAt'),
      question: _requiredString(data['questionText'], 'questionText'),
      questionBm: _requiredString(data['questionTextBm'], 'questionTextBm'),
      options: _requiredStringList(data['options'], 'options'),
      optionsBm: _requiredStringList(data['optionsBm'], 'optionsBm'),
      sourceReference: _requiredString(
        data['sourceReference'],
        'sourceReference',
      ),
      order: _optionalInt(data['order']),
      bloomLevel: data['bloomLevel'] as String?,
    );
  }

  /// The exact document shape allowed in the client-readable `questions`
  /// collection. Keep answer keys and explanations out of this map.
  Map<String, Object> toFirestoreDocument() {
    return <String, Object>{
      'questionId': id,
      'bankId': bankId,
      'topicId': topicId,
      'subtopicId': subtopicId,
      'skillId': skillId,
      'yearLevel': yearLevel,
      'difficultyLevel': difficultyLevel,
      'estimatedDifficulty': estimatedDifficulty,
      'contentVersion': contentVersion,
      'language': language,
      'createdAt': createdAt,
      'questionText': question,
      'questionTextBm': questionBm,
      'options': options,
      'optionsBm': optionsBm,
      'sourceReference': sourceReference,
      'isActive': isActive,
      if (order != null) 'order': order!,
      if (bloomLevel != null) 'bloomLevel': bloomLevel!,
    };
  }

  static String _requiredString(Object? value, String field) {
    if (value is String && value.isNotEmpty) return value;
    throw FormatException('Missing quiz question field: $field');
  }

  static int _requiredInt(Object? value, String field) {
    if (value is int) return value;
    if (value is num) return value.round();
    throw FormatException('Missing quiz question field: $field');
  }

  static int? _optionalInt(Object? value) {
    if (value is int) return value;
    if (value is num) return value.round();
    return null;
  }

  static double _requiredDouble(Object? value, String field) {
    if (value is num) return value.toDouble();
    throw FormatException('Missing quiz question field: $field');
  }

  static List<String> _requiredStringList(Object? value, String field) {
    if (value is List && value.every((item) => item is String)) {
      return value.cast<String>();
    }
    throw FormatException('Missing quiz question field: $field');
  }
}
