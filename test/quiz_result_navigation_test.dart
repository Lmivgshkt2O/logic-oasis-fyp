import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/collaboration/qa_forum/qa_forum_page.dart';
import 'package:logic_oasis/features/formula_forge/subtopic_page.dart';
import 'package:logic_oasis/features/quiz/quiz_page.dart';
import 'package:logic_oasis/features/quiz/result_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/forum_answer.dart';
import 'package:logic_oasis/shared/models/forum_question.dart';
import 'package:logic_oasis/shared/models/question_response.dart';
import 'package:logic_oasis/shared/models/quiz_completion.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/quiz_review_item.dart';
import 'package:logic_oasis/shared/models/quiz_session.dart';
import 'package:logic_oasis/shared/models/subtopic.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/repositories/collaboration_repository.dart';
import 'package:logic_oasis/shared/services/quiz_session_service.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

const _quizSession = QuizSession(
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
);

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
      positiveConfirmation: 'Confirmed by the server.',
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

class _ReviewingQuizSessionService implements QuizSessionGateway {
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
      positiveConfirmation: 'Confirmed by the server.',
      validationStatus: 'validated',
    );
  }

  @override
  Future<QuizCompletion> finalizeSession(String sessionId) async {
    return const QuizCompletion(
      correctCount: 0,
      totalQuestions: 1,
      score: 0,
      timeTakenSeconds: 3,
      reviewItems: <QuizReviewItem>[
        QuizReviewItem(
          questionId: 'question-1',
          sequenceIndex: 0,
          questionText: 'Which numeral shows twenty thousand four?',
          questionTextBm: 'Nombor manakah menunjukkan dua puluh ribu empat?',
          questionType: 'Place value',
          questionTypeBm: 'Nilai tempat',
          reviewFocus: 'Check the value of each digit.',
          reviewFocusBm: 'Semak nilai setiap digit.',
        ),
      ],
    );
  }
}

class _IntegrationDiscussRepository implements CollaborationRepository {
  String? openedQuestionId;

  @override
  Future<LinkedDiscussion> openOrCreateLinkedDiscussion({
    required String questionId,
  }) async {
    openedQuestionId = questionId;
    return LinkedDiscussion(
      id: 'linked_question-1_v1',
      sourceQuestionId: questionId,
      sourceContentVersion: 'test',
      prompt: 'Which numeral shows twenty thousand four?',
      promptBm: 'Nombor manakah menunjukkan dua puluh ribu empat?',
      options: const ['2 004', '20 004'],
      optionsBm: const ['2 004', '20 004'],
    );
  }

  @override
  Stream<Set<String>> watchBlockedStudentIds(String studentId) =>
      const Stream<Set<String>>.empty();

  @override
  Stream<List<ForumAnswer>> watchAnswers(String questionId) =>
      Stream.value(const <ForumAnswer>[]);

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

QuizQuestion _question(String id, String subtopicId) {
  return QuizQuestion(
    id: id,
    bankId: 'bank-$subtopicId',
    topicId: 'topic-1',
    subtopicId: subtopicId,
    skillId: 'skill',
    yearLevel: 4,
    difficultyLevel: 'Easy',
    estimatedDifficulty: .2,
    contentVersion: 'test',
    language: 'en',
    createdAt: '2026-08-12',
    question: 'Question for $subtopicId',
    questionBm: 'Soalan $subtopicId',
    options: <String>['a', 'b'],
    optionsBm: <String>['a', 'b'],
    sourceReference: 'Test',
  );
}

Subtopic _subtopic(String id, {int order = 1}) {
  return Subtopic(
    id: id,
    title: 'Step $id',
    titleBm: 'Langkah $id',
    order: order,
    activeBankCount: 1,
    questions: <QuizQuestion>[_question('q-$id', id)],
  );
}

Topic _topic(String id, String title, List<Subtopic> subtopics) {
  return Topic(
    id: id,
    title: title,
    titleBm: title,
    area: 'Area',
    yearLevel: 4,
    progress: 0,
    mastery: 'New',
    subtopics: subtopics,
  );
}

class _NavigatingQuizSessionService implements QuizSessionGateway {
  final List<String> startedSubtopicIds = <String>[];
  int _attempt = 0;

  @override
  Future<QuizSession> startSession({
    required String topicId,
    required String subtopicId,
    required int yearLevel,
  }) async {
    startedSubtopicIds.add(subtopicId);
    return QuizSession(
      id: 'session-$subtopicId-${startedSubtopicIds.length}',
      attemptId: 'attempt-${_attempt++}',
      assignmentId: 'assignment',
      assignmentSource: 'cold_start_easy',
      bankId: 'bank-$subtopicId',
      topicId: topicId,
      subtopicId: subtopicId,
      yearLevel: yearLevel,
      difficultyLevel: 'Easy',
      contentVersion: 'test',
      questionIds: <String>['q-$subtopicId'],
      questions: <QuizQuestion>[_question('q-$subtopicId', subtopicId)],
    );
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
      positiveConfirmation: 'Confirmed by the server.',
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
      attemptId: 'attempt-final',
    );
  }
}

AiDiagnosisStreamFactory _diagnosisWith(
  String action, {
  String? targetTopicId,
  String? targetSubtopicId,
}) {
  return (String attemptId,
      {String? topicId, String? subtopicId, int? yearLevel}) {
    return Stream<AiDiagnosis?>.value(
      AiDiagnosis(
        attemptId: attemptId,
        studentId: 'student',
        sourceAttemptSequence: 1,
        analysisState: 'completed',
        displayCode: 'analysis_completed',
        recommendedLearningAction: action,
        recommendationBasis: 'bkt_mastery',
        recommendationTargetTopicId: targetTopicId,
        recommendationTargetSubtopicId: targetSubtopicId,
      ),
    );
  };
}

Future<void> _completeOneQuiz(WidgetTester tester) async {
  await tester.tap(find.text('Step s1'));
  await tester.pumpAndSettle();
  await tester.tap(find.text('a'));
  await tester.pump();
  await tester.tap(find.text('Finish Quiz'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('finalized secure quiz replaces the quiz with a result page', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(theme: LogicOasisTheme.light(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: QuizPage(
          title: 'Whole Numbers',
          isBahasaMelayu: false,
          sessionService: _FinalizingQuizSessionService(),
          session: _quizSession,
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

  testWidgets('quiz review opens the canonical linked forum discussion', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(900, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    final repository = _IntegrationDiscussRepository();
    await tester.pumpWidget(
      MaterialApp(theme: LogicOasisTheme.light(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: QuizPage(
          title: 'Whole Numbers',
          isBahasaMelayu: false,
          sessionService: _ReviewingQuizSessionService(),
          session: _quizSession,
          forumRepository: repository,
        ),
      ),
    );

    await tester.tap(find.text('20 004'));
    await tester.pump();
    await tester.tap(find.text('Finish Quiz'));
    await tester.pumpAndSettle();

    expect(find.text('Review these first'), findsOneWidget);
    await tester.tap(find.text('Discuss in forum'));
    await tester.pumpAndSettle();

    expect(repository.openedQuestionId, 'question-1');
    expect(find.byType(ForumDiscussionPage), findsOneWidget);
    expect(find.text('Choose your final answer'), findsOneWidget);
  });

  testWidgets('back to forge returns from the result to the subtopic page', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(theme: LogicOasisTheme.light(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) => Scaffold(
            body: Column(
              children: [
                const Text('Subtopic page'),
                FilledButton(
                  onPressed: () => Navigator.of(context).push<void>(
                    MaterialPageRoute(
                      builder: (_) => QuizPage(
                        title: 'Whole Numbers',
                        isBahasaMelayu: false,
                        sessionService: _FinalizingQuizSessionService(),
                        session: _quizSession,
                      ),
                    ),
                  ),
                  child: const Text('Start quiz'),
                ),
              ],
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Start quiz'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('20 004'));
    await tester.pump();
    await tester.tap(find.text('Finish Quiz'));
    await tester.pumpAndSettle();

    final backToForge = find.text('Back to Forge');
    await tester.ensureVisible(backToForge);
    await tester.tap(backToForge);
    await tester.pumpAndSettle();

    expect(find.text('Subtopic page'), findsOneWidget);
    expect(find.text('Quiz Result'), findsNothing);
  });

  testWidgets('repeat action restarts the same subtopic through the callable', (
    tester,
  ) async {
    final state = AppState();
    state.topics
      ..clear()
      ..add(_topic('topic-1', 'Topic One', <Subtopic>[_subtopic('s1')]));
    final service = _NavigatingQuizSessionService();
    await tester.pumpWidget(
      MaterialApp(theme: LogicOasisTheme.light(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: SubtopicPage(
          state: state,
          topic: state.topics.first,
          sessionService: service,
          aiDiagnosisStreamFactory: _diagnosisWith('repeat_subtopic'),
        ),
      ),
    );

    await _completeOneQuiz(tester);
    final practiseAgain = find.text('Practise Again');
    await tester.ensureVisible(practiseAgain);
    await tester.tap(practiseAgain);
    await tester.pumpAndSettle();

    expect(service.startedSubtopicIds, <String>['s1', 's1']);
  });

  testWidgets('advance action starts the next ordered subtopic', (tester) async {
    final state = AppState();
    state.topics
      ..clear()
      ..add(
        _topic('topic-1', 'Topic One', <Subtopic>[
          _subtopic('s1', order: 1),
          _subtopic('s2', order: 2),
        ]),
      );
    final service = _NavigatingQuizSessionService();
    await tester.pumpWidget(
      MaterialApp(theme: LogicOasisTheme.light(),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: SubtopicPage(
          state: state,
          topic: state.topics.first,
          sessionService: service,
          aiDiagnosisStreamFactory: _diagnosisWith(
            'advance',
            targetTopicId: 'topic-1',
            targetSubtopicId: 's2',
          ),
        ),
      ),
    );

    await _completeOneQuiz(tester);
    final moveOn = find.text('Move On');
    await tester.ensureVisible(moveOn);
    await tester.tap(moveOn);
    await tester.pumpAndSettle();

    expect(service.startedSubtopicIds, <String>['s1', 's2']);
  });

  testWidgets(
    'advance from the last subtopic opens the next topic subtopic page',
    (tester) async {
      final state = AppState();
      state.topics
        ..clear()
        ..addAll(<Topic>[
          _topic('topic-1', 'Topic One', <Subtopic>[_subtopic('s1')]),
          _topic('topic-2', 'Topic Two', const <Subtopic>[]),
        ]);
      final service = _NavigatingQuizSessionService();
      await tester.pumpWidget(
        MaterialApp(theme: LogicOasisTheme.light(),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: SubtopicPage(
            state: state,
            topic: state.topics.first,
            sessionService: service,
            aiDiagnosisStreamFactory: _diagnosisWith(
              'advance',
              targetTopicId: 'topic-2',
            ),
          ),
        ),
      );

      await _completeOneQuiz(tester);
      final moveOn = find.text('Move On');
      await tester.ensureVisible(moveOn);
      await tester.tap(moveOn);
      await tester.pumpAndSettle();

      expect(find.text('Topic Two'), findsWidgets);
      expect(service.startedSubtopicIds, <String>['s1']);
    },
  );

  testWidgets(
    'advance with no next topic returns to Formula Forge with a message',
    (tester) async {
      final state = AppState();
      state.topics
        ..clear()
        ..add(_topic('topic-1', 'Topic One', <Subtopic>[_subtopic('s1')]));
      final service = _NavigatingQuizSessionService();
      await tester.pumpWidget(
        MaterialApp(theme: LogicOasisTheme.light(),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: Builder(
            builder: (context) => Scaffold(
              body: Column(
                children: <Widget>[
                  const Text('Formula Forge'),
                  FilledButton(
                    onPressed: () => Navigator.of(context).push<void>(
                      MaterialPageRoute<void>(
                        builder: (_) => SubtopicPage(
                          state: state,
                          topic: state.topics.first,
                          sessionService: service,
                          aiDiagnosisStreamFactory: _diagnosisWith('advance'),
                        ),
                      ),
                    ),
                    child: const Text('Open topic'),
                  ),
                ],
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open topic'));
      await tester.pumpAndSettle();
      await _completeOneQuiz(tester);
      final moveOn = find.text('Move On');
      await tester.ensureVisible(moveOn);
      await tester.tap(moveOn);
      await tester.pumpAndSettle();

      expect(find.text('Formula Forge'), findsOneWidget);
      expect(find.text('You completed all available topics!'), findsOneWidget);
    },
  );
}
