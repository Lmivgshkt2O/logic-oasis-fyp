import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/quiz/quiz_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/question_response.dart';
import 'package:logic_oasis/shared/models/quiz_completion.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/quiz_session.dart';
import 'package:logic_oasis/shared/services/quiz_session_service.dart';

class _FinalizingQuizSessionService implements QuizSessionGateway {
  @override
  Future<QuizSession> startSession({
    required String topicId,
    required String subtopicId,
    required int yearLevel,
  }) {
    throw UnsupportedError('The quiz page receives an existing session.');
  }

  @override
  Future<QuestionResponse> submitResponse({
    required QuestionResponse pendingResponse,
    required int responseTimeMs,
    int hintCount = 0,
  }) async {
    return QuestionResponse(
      sessionId: pendingResponse.sessionId,
      questionId: pendingResponse.questionId,
      selectedIndex: pendingResponse.selectedIndex,
      sequenceIndex: pendingResponse.sequenceIndex,
      idempotencyKey: pendingResponse.idempotencyKey,
      isCorrect: true,
      explanation: 'Confirmed by the server.',
      validationStatus: 'validated',
    );
  }

  @override
  Future<QuizCompletion> finalizeSession(String sessionId) async {
    return const QuizCompletion(
      correctCount: 1,
      totalQuestions: 1,
      score: 100,
      timeTakenSeconds: 3,
    );
  }
}

void main() {
  testWidgets('finalized secure quiz replaces the quiz with a result page', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: QuizPage(
          title: 'Whole Numbers',
          isBahasaMelayu: false,
          sessionService: _FinalizingQuizSessionService(),
          session: const QuizSession(
            id: 'session-1',
            attemptId: 'attempt-1',
            assignmentId: 'assignment-1',
            assignmentSource: 'adaptive',
            bankId: 'bank-1',
            topicId: 'whole_numbers',
            subtopicId: 'read_write_numbers',
            yearLevel: 4,
            difficultyLevel: 'Easy',
            contentVersion: 'test',
            questionIds: <String>['question-1'],
            questions: <QuizQuestion>[
              QuizQuestion(
                id: 'question-1',
                bankId: 'bank-1',
                topicId: 'whole_numbers',
                subtopicId: 'read_write_numbers',
                skillId: 'read_write_numbers',
                yearLevel: 4,
                difficultyLevel: 'Easy',
                estimatedDifficulty: .2,
                contentVersion: 'test',
                language: 'en',
                createdAt: '2026-07-20',
                question: 'Which numeral shows twenty thousand four?',
                questionBm: 'Nombor manakah menunjukkan dua puluh ribu empat?',
                options: <String>['2 004', '20 004'],
                optionsBm: <String>['2 004', '20 004'],
                sourceReference: 'Test',
              ),
            ],
          ),
        ),
      ),
    );

    await tester.tap(find.text('20 004'));
    await tester.pump();
    await tester.tap(find.text('Finish Quiz'));
    await tester.pumpAndSettle();

    expect(find.text('100%'), findsOneWidget);
    expect(find.text('Back to Forge'), findsOneWidget);
    expect(find.text('Quiz complete!'), findsNothing);
  });
}
