import 'package:logic_oasis/shared/models/quiz_question.dart';

/// A short-lived server-issued set of prompts. It contains no answer key.
class QuizSession {
  const QuizSession({
    required this.id,
    required this.attemptId,
    required this.assignmentId,
    required this.assignmentSource,
    required this.bankId,
    required this.topicId,
    required this.subtopicId,
    required this.yearLevel,
    required this.difficultyLevel,
    required this.contentVersion,
    required this.questionIds,
    required this.questions,
  });

  final String id;
  final String attemptId;
  final String assignmentId;
  final String assignmentSource;
  final String bankId;
  final String topicId;
  final String subtopicId;
  final int yearLevel;
  final String difficultyLevel;
  final String contentVersion;
  final List<String> questionIds;
  final List<QuizQuestion> questions;

  factory QuizSession.fromCallableData(Map<Object?, Object?> data) {
    final rawQuestions = data['questions'];
    if (rawQuestions is! List) {
      throw const FormatException('Missing callable response field: questions');
    }
    final questions = rawQuestions
        .whereType<Map>()
        .map(
          (item) =>
              QuizQuestion.fromCallableData(item.cast<Object?, Object?>()),
        )
        .toList(growable: false);
    final questionIds = _stringList(data['questionIds']);
    if (questions.isEmpty || questionIds.length != questions.length) {
      throw const FormatException('Invalid quiz session question lineage.');
    }
    return QuizSession(
      id: _requiredString(data['sessionId'], 'sessionId'),
      attemptId: _requiredString(data['attemptId'], 'attemptId'),
      assignmentId: _requiredString(data['assignmentId'], 'assignmentId'),
      assignmentSource: _requiredString(
        data['assignmentSource'],
        'assignmentSource',
      ),
      bankId: _requiredString(data['bankId'], 'bankId'),
      topicId: _requiredString(data['topicId'], 'topicId'),
      subtopicId: _requiredString(data['subtopicId'], 'subtopicId'),
      yearLevel: _requiredInt(data['yearLevel'], 'yearLevel'),
      difficultyLevel: _requiredString(
        data['difficultyLevel'],
        'difficultyLevel',
      ),
      contentVersion: _requiredString(data['contentVersion'], 'contentVersion'),
      questionIds: questionIds,
      questions: questions,
    );
  }

  static List<String> _stringList(Object? value) {
    if (value is! List || value.any((item) => item is! String)) {
      throw const FormatException(
        'Missing callable response field: questionIds',
      );
    }
    return value.cast<String>();
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
}
