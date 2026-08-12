import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/quiz/quiz_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/question_response.dart';
import 'package:logic_oasis/shared/models/quiz_completion.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/quiz_session.dart';
import 'package:logic_oasis/shared/services/quiz_session_service.dart';

const _session = QuizSession(
  id: 'session-guidance',
  attemptId: 'attempt-guidance',
  assignmentId: 'assignment-guidance',
  assignmentSource: 'cold_start_easy',
  bankId: 'bank-guidance',
  topicId: 'whole_numbers',
  subtopicId: 'read_write_numbers',
  yearLevel: 4,
  difficultyLevel: 'Easy',
  contentVersion: 'test',
  questionIds: <String>['question-guidance'],
  questions: <QuizQuestion>[
    QuizQuestion(
      id: 'question-guidance',
      bankId: 'bank-guidance',
      topicId: 'whole_numbers',
      subtopicId: 'read_write_numbers',
      skillId: 'read_write_numbers',
      yearLevel: 4,
      difficultyLevel: 'Easy',
      estimatedDifficulty: .2,
      contentVersion: 'test',
      language: 'en',
      createdAt: '2026-07-30',
      question: 'Which numeral is shown?',
      questionBm: 'Angka manakah ditunjukkan?',
      options: <String>['2 004', '20 004'],
      optionsBm: <String>['2 004', '20 004'],
      sourceReference: 'Test',
    ),
  ],
);

class _WrongAnswerService implements QuizSessionGateway {
  int submissions = 0;

  @override
  Future<QuizSession> startSession({
    required String topicId,
    required String subtopicId,
    required int yearLevel,
  }) => throw UnsupportedError('The quiz page receives an existing session.');

  @override
  Future<QuestionResponse> submitResponse({
    required QuestionResponse pendingResponse,
    required int responseTimeMs,
    int hintCount = 0,
  }) async {
    submissions += 1;
    return QuestionResponse(
      sessionId: pendingResponse.sessionId,
      questionId: pendingResponse.questionId,
      selectedIndex: pendingResponse.selectedIndex,
      sequenceIndex: pendingResponse.sequenceIndex,
      idempotencyKey: pendingResponse.idempotencyKey,
      isCorrect: false,
      feedbackHint: 'Twenty thousand has 20 groups of one thousand.',
      feedbackHintBm: 'Dua puluh ribu mempunyai 20 kumpulan seribu.',
      feedbackExample: 'In 43 007, the 43 shows 43 thousands.',
      feedbackExampleBm: 'Dalam 43 007, angka 43 menunjukkan 43 ribu.',
      reviewFocus: 'Check how many thousands are named before the ones.',
      reviewFocusBm: 'Semak berapa ribu yang disebut sebelum sa.',
      validationStatus: 'validated',
    );
  }

  @override
  Future<QuizCompletion> finalizeSession(String sessionId) =>
      throw UnsupportedError('Not needed for this test.');
}

void main() {
  testWidgets(
    'a wrong validated answer displays ordered guidance without retry',
    (tester) async {
      final service = _WrongAnswerService();
      await tester.pumpWidget(
        MaterialApp(
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: QuizPage(
            title: 'Whole Numbers',
            isBahasaMelayu: false,
            session: _session,
            sessionService: service,
          ),
        ),
      );

      await tester.tap(find.text('2 004'));
      await tester.pumpAndSettle();

      expect(find.text('Hint'), findsOneWidget);
      expect(
        find.text(
          'Twenty thousand has 20 groups of one thousand.',
        ),
        findsOneWidget,
      );
      expect(
        find.text('Example: In 43 007, the 43 shows 43 thousands.'),
        findsOneWidget,
      );
      expect(
        find.text(
          'Check how many thousands are named before the ones.',
        ),
        findsOneWidget,
      );
      expect(find.text('Finish Quiz'), findsOneWidget);

      await tester.tap(find.text('20 004'));
      await tester.pump();
      expect(service.submissions, 1);
    },
  );
}
