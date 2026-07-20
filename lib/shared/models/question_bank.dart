import 'package:logic_oasis/shared/models/quiz_question.dart';

enum QuestionDifficulty {
  easy('Easy'),
  moderate('Moderate'),
  hard('Hard');

  const QuestionDifficulty(this.label);

  final String label;

  static QuestionDifficulty? fromLabel(String value) {
    for (final difficulty in QuestionDifficulty.values) {
      if (difficulty.label == value) return difficulty;
    }
    return null;
  }
}

/// A reusable, versioned set of client-safe prompts for one subtopic.
class QuestionBank {
  const QuestionBank({
    required this.id,
    required this.topicId,
    required this.subtopicId,
    required this.skillId,
    required this.yearLevel,
    required this.difficulty,
    required this.contentVersion,
    required this.questions,
    this.isActive = true,
  });

  final String id;
  final String topicId;
  final String subtopicId;
  final String skillId;
  final int yearLevel;
  final QuestionDifficulty difficulty;
  final String contentVersion;
  final List<QuizQuestion> questions;
  final bool isActive;

  /// Returns a deterministic form that favours unseen questions. The offset
  /// lets the server create different forms without exposing an answer key.
  List<QuizQuestion> sampleFive({
    Iterable<String> recentlySeenQuestionIds = const <String>[],
    int offset = 0,
  }) {
    const formSize = 5;
    final recentIds = recentlySeenQuestionIds.toSet();
    final active = questions.where((question) => question.isActive).toList();
    final unseen = active
        .where((question) => !recentIds.contains(question.id))
        .toList();
    final pool = unseen.length >= formSize ? unseen : active;

    if (pool.length < formSize) {
      throw StateError('Question bank $id cannot create a five-question form.');
    }

    final normalizedOffset =
        ((offset % pool.length) + pool.length) % pool.length;
    return List<QuizQuestion>.generate(
      formSize,
      (index) => pool[(normalizedOffset + index) % pool.length],
      growable: false,
    );
  }

  List<String> validate() {
    final errors = <String>[];
    if (id.trim().isEmpty) errors.add('bank id is required');
    if (topicId.trim().isEmpty) errors.add('topic id is required');
    if (subtopicId.trim().isEmpty) errors.add('subtopic id is required');
    if (skillId.trim().isEmpty) errors.add('skill id is required');
    if (yearLevel < 4 || yearLevel > 6) errors.add('year level must be 4-6');
    if (contentVersion.trim().isEmpty)
      errors.add('content version is required');

    final activeQuestions = questions.where((question) => question.isActive);
    if (isActive &&
        (activeQuestions.length < 8 || activeQuestions.length > 10)) {
      errors.add('active bank must contain 8-10 active questions');
    }

    final questionIds = <String>{};
    for (final question in activeQuestions) {
      if (!questionIds.add(question.id)) {
        errors.add('duplicate question id ${question.id}');
      }
      if (question.bankId != id ||
          question.topicId != topicId ||
          question.subtopicId != subtopicId ||
          question.skillId != skillId ||
          question.yearLevel != yearLevel ||
          question.difficultyLevel != difficulty.label ||
          question.contentVersion != contentVersion) {
        errors.add('question ${question.id} does not match bank metadata');
      }
      if (question.language != 'bilingual' ||
          question.createdAt.trim().isEmpty) {
        errors.add('question ${question.id} is missing provenance metadata');
      }
      if (question.question.trim().isEmpty ||
          question.questionBm.trim().isEmpty ||
          question.options.length != 4 ||
          question.optionsBm.length != 4 ||
          question.options.any((option) => option.trim().isEmpty) ||
          question.optionsBm.any((option) => option.trim().isEmpty)) {
        errors.add(
          'question ${question.id} is missing required bilingual fields',
        );
      }
    }
    return errors;
  }

  void validateOrThrow() {
    final errors = validate();
    if (errors.isNotEmpty) {
      throw StateError('Invalid question bank $id: ${errors.join('; ')}');
    }
  }

  Map<String, Object> toFirestoreDocument() {
    return <String, Object>{
      'bankId': id,
      'topicId': topicId,
      'subtopicId': subtopicId,
      'skillId': skillId,
      'yearLevel': yearLevel,
      'difficultyLevel': difficulty.label,
      'questionIds': questions.map((question) => question.id).toList(),
      'version': contentVersion,
      'isActive': isActive,
    };
  }
}
