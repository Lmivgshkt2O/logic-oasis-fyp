import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/models/question_response.dart';
import 'package:logic_oasis/shared/models/quiz_completion.dart';
import 'package:logic_oasis/shared/models/quiz_session.dart';

void main() {
  final prompt = <Object?, Object?>{
    'questionId': 'question_1',
    'bankId': 'bank_easy',
    'topicId': 'whole_numbers_y4',
    'subtopicId': 'read_write_numbers',
    'skillId': 'y4_read_write',
    'yearLevel': 4,
    'difficultyLevel': 'Easy',
    'estimatedDifficulty': .2,
    'contentVersion': '2026.07.15',
    'language': 'bilingual',
    'createdAt': '2026-07-15T00:00:00Z',
    'questionText': 'Which numeral is correct?',
    'questionTextBm': 'Angka manakah betul?',
    'options': ['a', 'b', 'c', 'd'],
    'optionsBm': ['a', 'b', 'c', 'd'],
    'sourceReference': 'KSSR',
  };

  test('session parser accepts prompts but never requires answer keys', () {
    final session = QuizSession.fromCallableData(<Object?, Object?>{
      'sessionId': 'session_1',
      'attemptId': 'attempt_1',
      'assignmentId': 'cold_start_easy',
      'assignmentSource': 'cold_start_easy',
      'bankId': 'bank_easy',
      'topicId': 'whole_numbers_y4',
      'subtopicId': 'read_write_numbers',
      'yearLevel': 4,
      'difficultyLevel': 'Easy',
      'contentVersion': '2026.07.15',
      'questionIds': ['question_1'],
      'questions': [prompt],
    });

    expect(session.questions.single.id, 'question_1');
    expect(session.questions.single.options, hasLength(4));
  });

  test(
    'pending response has no local correctness before callable validation',
    () {
      const pending = QuestionResponse(
        sessionId: 'session_1',
        questionId: 'question_1',
        selectedIndex: 2,
        sequenceIndex: 0,
        idempotencyKey: 'session_1:question_1:0',
      );

      expect(pending.isPending, isTrue);
      expect(pending.isCorrect, isNull);
      expect(
        pending.toSubmissionData(responseTimeMs: 10, hintCount: 0),
        isNot(contains('serverIsCorrect')),
      );
      expect(
        pending.toSubmissionData(responseTimeMs: 10, hintCount: 0),
        containsPair('selectedIndex', '2'),
      );
      expect(
        pending.toSubmissionData(responseTimeMs: 10, hintCount: 0),
        containsPair('sequenceIndex', '0'),
      );
      expect(
        pending.toSubmissionData(responseTimeMs: -1, hintCount: -1),
        containsPair('responseTimeMs', '0'),
      );
    },
  );

  test(
    'trusted callable feedback and completion parse server-owned fields',
    () {
      final response = QuestionResponse.fromCallableData(<Object?, Object?>{
        'responseId': 'response_1',
        'sessionId': 'session_1',
        'attemptId': 'attempt_1',
        'questionId': 'question_1',
        'selectedIndex': 2,
        'serverIsCorrect': false,
        'feedbackHint': 'Look at the place of the digit.',
        'feedbackHintBm': 'Lihat tempat digit itu.',
        'feedbackExample': 'In 43 007, the 43 shows 43 thousands.',
        'feedbackExampleBm': 'Dalam 43 007, angka 43 menunjukkan 43 ribu.',
        'reviewFocus': 'Check the value of each digit.',
        'reviewFocusBm': 'Semak nilai setiap digit.',
        'validationStatus': 'validated',
        'sequenceIndex': 0,
      }, idempotencyKey: 'session_1:question_1:0');
      final completion = QuizCompletion.fromCallableData(<Object?, Object?>{
        'attemptId': 'attempt_1',
        'sessionId': 'session_1',
        'correctCount': 3,
        'totalQuestions': 5,
        'score': 60,
        'finalizationStatus': 'finalized',
        'reviewItems': [
          <Object?, Object?>{
            'questionId': 'question_1',
            'sequenceIndex': 0,
            'questionText': 'Which numeral is correct?',
            'questionTextBm': 'Angka manakah betul?',
            'questionType': 'Choose a numeral',
            'questionTypeBm': 'Pilih angka',
            'reviewFocus': 'Check the value of each digit.',
            'reviewFocusBm': 'Semak nilai setiap digit.',
          },
        ],
      });

      expect(response.isValidated, isTrue);
      expect(response.isCorrect, isFalse);
      expect(response.localizedFeedbackHint(false), 'Look at the place of the digit.');
      expect(response.localizedFeedbackExample(false), 'In 43 007, the 43 shows 43 thousands.');
      expect(response.localizedReviewFocus(false), 'Check the value of each digit.');
      expect(response.localizedFeedbackLines(false), hasLength(3));
      expect(response.localizedPositiveConfirmation(false), isEmpty);
      expect(completion.score, 60);
      expect(completion.attemptId, 'attempt_1');
      expect(completion.reviewItems, hasLength(1));
      expect(completion.reviewItems.single.questionId, 'question_1');
      expect(completion.reviewItems.single.sequenceIndex, 0);
      expect(completion.reviewItems.single.localizedPrompt(false),
          'Which numeral is correct?');
      expect(completion.reviewItems.single.localizedPrompt(true),
          'Angka manakah betul?');
      expect(completion.reviewItems.single.localizedType(false),
          'Choose a numeral');
      expect(completion.reviewItems.single.localizedReviewFocus(false),
          'Check the value of each digit.');
    },
  );

  test('validated feedback rejects incomplete or mixed secure payloads', () {
    final invalid = <Object?, Object?>{
      'responseId': 'response_1',
      'sessionId': 'session_1',
      'questionId': 'question_1',
      'selectedIndex': 2,
      'serverIsCorrect': false,
      'feedbackHint': 'A hint without a review focus.',
      'feedbackHintBm': 'Petunjuk tanpa fokus ulang kaji.',
      'validationStatus': 'validated',
      'sequenceIndex': 0,
    };

    expect(
      () => QuestionResponse.fromCallableData(
        invalid,
        idempotencyKey: 'session_1:question_1:0',
      ),
      throwsFormatException,
    );

    final mixed = <Object?, Object?>{
      'responseId': 'response_1',
      'sessionId': 'session_1',
      'questionId': 'question_1',
      'selectedIndex': 0,
      'serverIsCorrect': true,
      'positiveConfirmation': 'Correct.',
      'positiveConfirmationBm': 'Betul.',
      'feedbackHint': 'A hint on a correct answer.',
      'feedbackHintBm': 'Petunjuk pada jawapan betul.',
      'validationStatus': 'validated',
      'sequenceIndex': 0,
    };
    expect(
      () => QuestionResponse.fromCallableData(
        mixed,
        idempotencyKey: 'session_1:question_1:0',
      ),
      throwsFormatException,
    );

    final lopsidedExample = <Object?, Object?>{
      'responseId': 'response_1',
      'sessionId': 'session_1',
      'questionId': 'question_1',
      'selectedIndex': 2,
      'serverIsCorrect': false,
      'feedbackHint': 'A hint.',
      'feedbackHintBm': 'Petunjuk.',
      'feedbackExample': 'In 31 006, the 31 shows 31 thousands.',
      'reviewFocus': 'Check the value of each digit.',
      'reviewFocusBm': 'Semak nilai setiap digit.',
      'validationStatus': 'validated',
      'sequenceIndex': 0,
    };
    expect(
      () => QuestionResponse.fromCallableData(
        lopsidedExample,
        idempotencyKey: 'session_1:question_1:0',
      ),
      throwsFormatException,
    );
  });
}
