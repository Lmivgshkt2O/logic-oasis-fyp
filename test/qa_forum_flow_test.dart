import 'dart:async';

import 'package:cloud_functions/cloud_functions.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/collaboration/qa_forum/qa_forum_page.dart';
import 'package:logic_oasis/shared/models/forum_answer.dart';
import 'package:logic_oasis/shared/models/forum_question.dart';
import 'package:logic_oasis/shared/repositories/collaboration_repository.dart';
import 'package:logic_oasis/shared/services/forum_ai_status_service.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

void main() {
  test(
    'forum feedback stays advisory and never labels probability confidence',
    () {
      const feedback = ForumAnswerFeedback(
        state: 'completed',
        label: 'needs_reasoning',
        message: 'Please add the steps behind your answer.',
        probability: 0.74,
        modelVersion: 'forum-explanation-nb-v1',
        calibrationState: 'not_calibrated',
      );

      expect(
        const ForumAiStatusService().statusText(feedback),
        contains('steps'),
      );
      expect(feedback.calibrationState, 'not_calibrated');
    },
  );

  test('fallback stays editable rather than asserting a model decision', () {
    const feedback = ForumAnswerFeedback(
      state: 'fallback',
      label: 'uncertain',
      message: '',
    );
    expect(
      const ForumAiStatusService().statusText(feedback),
      contains('saved'),
    );
  });

  test('pending revision is shown as an active feedback review', () {
    const feedback = ForumAnswerFeedback(
      state: 'pending',
      label: 'uncertain',
      message: 'Your revised answer is being reviewed.',
    );
    expect(
      const ForumAiStatusService().statusText(feedback),
      contains('Checking the explanation'),
    );
  });

  test('forum feedback has a Bahasa Melayu presentation', () {
    const feedback = ForumAnswerFeedback(
      state: 'completed',
      label: 'needs_reasoning',
      message: 'Please add more reasoning.',
    );
    expect(
      const ForumAiStatusService().statusText(feedback, isBahasaMelayu: true),
      contains('Sila tambah langkah'),
    );
  });

  test('linked question model parses the server-owned source contract', () {
    final question = ForumQuestion.fromFirestore('linked_q1_v1', {
      'mode': 'linked',
      'sourceQuestionId': 'bank_q1',
      'sourceContentVersion': 'v1',
      'title': 'Which numeral shows twenty thousand and four?',
      'text': 'Which numeral shows twenty thousand and four?',
      'promptSnapshot': {
        'questionText': 'Which numeral shows twenty thousand and four?',
        'questionTextBm': 'Angka manakah menunjukkan dua puluh ribu empat?',
        'options': ['20 004', '24 000', '20 400', '20 040'],
        'optionsBm': ['20 004', '24 000', '20 400', '20 040'],
      },
    });

    expect(question.mode, 'linked');
    expect(question.sourceQuestionId, 'bank_q1');
    expect(question.sourceContentVersion, 'v1');
    expect(question.prompt, 'Which numeral shows twenty thousand and four?');
    expect(question.promptBm, 'Angka manakah menunjukkan dua puluh ribu empat?');
    expect(question.options, hasLength(4));
    expect(question.optionsBm, hasLength(4));
  });

  test('linked answer model parses structured fields and public projection', () {
    final answer = ForumAnswer.fromFirestore('linked_a1', {
      'questionId': 'linked_q1_v1',
      'authorId': 'student-a',
      'mode': 'linked',
      'selectedOption': 2,
      'explanation': 'I added the thousands and compared the digits.',
      'revision': 2,
      'aiPublicState': 'none',
      'aiRunId': 'opaque-run-id',
      'aiRevision': 2,
    });

    expect(answer.mode, 'linked');
    expect(answer.selectedOption, 2);
    expect(answer.explanation, 'I added the thousands and compared the digits.');
    expect(answer.aiPublicState, 'none');
    expect(answer.aiRunId, 'opaque-run-id');
    expect(answer.aiRevision, 2);
  });

  test('repository routes linked discussion and answer callables', () async {
    final functions = _FakeFunctions({
      'openOrCreateForumDiscussion': {
        'discussionId': 'linked_bank_q1_v1',
        'sourceQuestionId': 'bank_q1',
        'sourceContentVersion': 'v1',
        'promptSnapshot': {
          'questionText': 'Which numeral shows twenty thousand and four?',
          'options': ['20 004', '24 000', '20 400', '20 040'],
        },
        'created': true,
      },
      'submitLinkedForumAnswer': {
        'answerId': 'linked_a1',
        'questionId': 'linked_bank_q1_v1',
        'revision': 1,
      },
      'editLinkedForumAnswer': {
        'answerId': 'linked_a1',
        'revision': 2,
      },
    });
    final repository = CollaborationRepository(
      firestore: _FakeFirestore(),
      functions: functions,
    );

    final discussion = await repository.openOrCreateLinkedDiscussion(
      questionId: 'bank_q1',
    );
    expect(discussion.id, 'linked_bank_q1_v1');
    expect(discussion.created, isTrue);
    expect(discussion.options, hasLength(4));
    expect(functions.calls['openOrCreateForumDiscussion'], {
      'questionId': 'bank_q1',
    });

    final answerId = await repository.submitLinkedAnswer(
      discussionId: 'linked_bank_q1_v1',
      selectedOption: 1,
      explanation: '  I compared each option with the question.  ',
    );
    expect(answerId, 'linked_a1');
    expect(functions.calls['submitLinkedForumAnswer'], {
      'discussionId': 'linked_bank_q1_v1',
      'selectedOption': 1,
      'explanation': 'I compared each option with the question.',
    });

    final revision = await repository.editLinkedAnswer(
      answerId: 'linked_a1',
      selectedOption: 2,
      explanation: 'I checked by adding back the group.',
    );
    expect(revision, 2);
    expect(functions.calls['editLinkedForumAnswer'], {
      'answerId': 'linked_a1',
      'selectedOption': 2,
      'explanation': 'I checked by adding back the group.',
    });
  });

  testWidgets('forum shows loading, empty, filter, and clear-filter states', (
    tester,
  ) async {
    final questions = StreamController<List<ForumQuestion>>();
    final blocked = StreamController<Set<String>>();
    addTearDown(questions.close);
    addTearDown(blocked.close);
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          questionsStream: questions.stream,
          blockedStudentIdsStream: blocked.stream,
        ),
      ),
    );
    blocked.add(const {});
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    questions.add(const []);
    await tester.pump();
    expect(find.textContaining('No questions yet'), findsOneWidget);

    questions.add(const [
      ForumQuestion(
        id: 'q1',
        authorId: 'student-2',
        title: 'How can I check subtraction?',
        text: 'I used addition but want another way to check.',
      ),
      ForumQuestion(
        id: 'q2',
        authorId: 'student-3',
        title: 'How do place values work?',
        text: 'I split the number into hundreds, tens, and ones.',
      ),
    ]);
    await tester.pump();
    expect(find.text('How can I check subtraction?'), findsOneWidget);
    expect(find.text('How do place values work?'), findsOneWidget);

    blocked.add(const {'student-2'});
    await tester.pump();
    expect(find.text('How can I check subtraction?'), findsNothing);
    expect(find.text('How do place values work?'), findsOneWidget);

    await tester.enterText(find.byType(TextField).first, 'place values');
    await tester.pump();
    expect(find.text('How can I check subtraction?'), findsNothing);
    expect(find.text('How do place values work?'), findsOneWidget);

    await tester.enterText(find.byType(TextField).first, 'geometry');
    await tester.pump();
    expect(find.text('No questions match this filter.'), findsOneWidget);
    await tester.tap(find.byTooltip('Clear filter'));
    await tester.pump();
    expect(find.text('How do place values work?'), findsOneWidget);
  });

  testWidgets('accepted answer is visibly singular in the answer view', (
    tester,
  ) async {
    final blocked = Stream<Set<String>>.value(const {}).asBroadcastStream();
    const question = ForumQuestion(
      id: 'q1',
      authorId: 'student-owner',
      title: 'How can I verify this result?',
      text: 'I want to compare two methods for checking the result.',
      acceptedAnswerId: 'a1',
    );
    const answer = ForumAnswer(
      id: 'a1',
      questionId: 'q1',
      authorId: 'student-peer',
      text: 'Subtract the addend from the total to check the other addend.',
      feedback: ForumAnswerFeedback(
        state: 'completed',
        label: 'explanation_sufficient',
        message: 'Your method is clear.',
      ),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          questionsStream: Stream.value(const [question]),
          blockedStudentIdsStream: blocked,
          answersStreamForQuestion: (_) => Stream.value(const [answer]),
        ),
      ),
    );
    await tester.pump();
    await tester.tap(find.text(question.title));
    await tester.pumpAndSettle();

    expect(find.text('Accepted answer'), findsOneWidget);
    expect(find.text('Accept'), findsNothing);
    expect(find.text('Your method is clear.'), findsNothing);
  });

  testWidgets('AI feedback is visible only to the answer author', (
    tester,
  ) async {
    final state = AppState();
    const question = ForumQuestion(
      id: 'q-author-only',
      authorId: 'student-question-author',
      title: 'How can I explain this calculation?',
      text: 'I want to show each step so another student can understand it.',
    );
    const answer = ForumAnswer(
      id: 'a-author-only',
      questionId: 'q-author-only',
      authorId: AppState.demoStudentId,
      text: 'I regrouped the tens and then checked by subtracting.',
      feedback: ForumAnswerFeedback(
        state: 'completed',
        label: 'needs_reasoning',
        message: 'Please add more reasoning.',
      ),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: state,
          questionsStream: Stream.value(const [question]),
          blockedStudentIdsStream: Stream.value(
            const <String>{},
          ).asBroadcastStream(),
          answersStreamForQuestion: (_) => Stream.value(const [answer]),
        ),
      ),
    );
    await tester.pump();
    await tester.tap(find.text(question.title));
    await tester.pumpAndSettle();
    expect(find.textContaining('Please add the steps'), findsOneWidget);
  });

  testWidgets('forum chrome follows the Bahasa Melayu preference', (
    tester,
  ) async {
    final state = AppState()..language = 'Bahasa Melayu';
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: state,
          questionsStream: Stream.value(const []),
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    expect(find.text('Forum S&J'), findsOneWidget);
    expect(find.text('Tanya soalan'), findsOneWidget);
    expect(find.text('Tapis soalan'), findsOneWidget);
  });

  testWidgets('remote acceptance hides every competing accept control', (
    tester,
  ) async {
    final answers = StreamController<List<ForumAnswer>>();
    addTearDown(answers.close);
    const question = ForumQuestion(
      id: 'q1',
      authorId: 'student_aiman_y4',
      title: 'How can I verify this result?',
      text: 'I want to compare two methods for checking the result.',
    );
    const feedback = ForumAnswerFeedback(
      state: 'completed',
      label: 'explanation_sufficient',
      message: 'Your method is clear.',
    );
    const first = ForumAnswer(
      id: 'a1',
      questionId: 'q1',
      authorId: 'student-peer-1',
      text: 'Subtract one addend from the total to verify the other.',
      feedback: feedback,
    );
    const second = ForumAnswer(
      id: 'a2',
      questionId: 'q1',
      authorId: 'student-peer-2',
      text: 'Regroup the values and calculate the total a second time.',
      feedback: feedback,
    );
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          questionsStream: Stream.value(const [question]),
          blockedStudentIdsStream: Stream.value(
            const <String>{},
          ).asBroadcastStream(),
          answersStreamForQuestion: (_) => answers.stream,
        ),
      ),
    );
    await tester.pump();
    await tester.tap(find.text(question.title));
    await tester.pump();
    answers.add(const [first, second]);
    await tester.pump();
    expect(find.text('Accept'), findsNWidgets(2));

    answers.add([
      ForumAnswer(
        id: first.id,
        questionId: first.questionId,
        authorId: first.authorId,
        text: first.text,
        feedback: feedback,
        acceptedAt: DateTime(2026, 8, 1),
      ),
      second,
    ]);
    await tester.pump();
    expect(find.text('Accepted answer'), findsOneWidget);
    expect(find.text('Accept'), findsNothing);
  });

  testWidgets('forum renders a block-stream permission failure', (
    tester,
  ) async {
    final blocked = StreamController<Set<String>>();
    addTearDown(blocked.close);
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          questionsStream: Stream.value(const []),
          blockedStudentIdsStream: blocked.stream,
        ),
      ),
    );
    blocked.addError(
      FirebaseException(plugin: 'cloud_firestore', code: 'permission-denied'),
    );
    await tester.pump();
    expect(find.textContaining('not allowed for your account'), findsOneWidget);
  });

  testWidgets('forum distinguishes denied access from retryable load failure', (
    tester,
  ) async {
    final denied = StreamController<List<ForumQuestion>>();
    addTearDown(denied.close);
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          questionsStream: denied.stream,
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    denied.addError(
      FirebaseException(plugin: 'cloud_firestore', code: 'permission-denied'),
    );
    await tester.pump();
    expect(find.textContaining('student profile'), findsOneWidget);

    final retryable = StreamController<List<ForumQuestion>>();
    addTearDown(retryable.close);
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          key: const ValueKey('retryable-forum'),
          state: AppState(),
          questionsStream: retryable.stream,
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    retryable.addError(
      FirebaseException(plugin: 'cloud_firestore', code: 'unavailable'),
    );
    await tester.pump();
    expect(find.textContaining('check your connection'), findsOneWidget);
  });

  testWidgets('editing an answer closes cleanly without a lifecycle error', (
    tester,
  ) async {
    final repository = _ActionRepository();
    await _openAnswerActions(
      tester,
      repository: repository,
      answerAuthorId: AppState.demoStudentId,
    );

    await tester.tap(find.byTooltip('Answer actions'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Edit answer'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byType(TextField).last,
      'I regrouped the tens, then subtracted to check every step.',
    );
    await tester.tap(find.text('Submit'));
    await tester.pumpAndSettle();

    expect(repository.edited, isTrue);
    expect(find.textContaining('edited successfully'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('reporting an answer closes cleanly without a lifecycle error', (
    tester,
  ) async {
    final repository = _ActionRepository();
    await _openAnswerActions(
      tester,
      repository: repository,
      answerAuthorId: 'student-peer',
    );

    await tester.tap(find.byTooltip('Answer actions'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Report'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byType(TextField).last,
      'This response contains unrelated content.',
    );
    await tester.tap(find.text('Submit'));
    await tester.pumpAndSettle();

    expect(repository.reported, isTrue);
    expect(find.text('Report submitted.'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

Future<void> _openAnswerActions(
  WidgetTester tester, {
  required CollaborationRepository repository,
  required String answerAuthorId,
}) async {
  const question = ForumQuestion(
    id: 'question-actions',
    authorId: 'student-question-author',
    title: 'How can I check this calculation?',
    text: 'I want another student to review each calculation step.',
  );
  final answer = ForumAnswer(
    id: 'answer-actions',
    questionId: question.id,
    authorId: answerAuthorId,
    text: 'I regrouped the values and checked the calculation.',
    feedback: const ForumAnswerFeedback(
      state: 'completed',
      label: 'sufficient_reasoning',
      message: 'The reasoning is clear.',
    ),
  );
  await tester.pumpWidget(
    MaterialApp(
      home: QaForumPage(
        state: AppState(),
        repository: repository,
        questionsStream: Stream.value(const [question]),
        blockedStudentIdsStream: Stream.value(
          const <String>{},
        ).asBroadcastStream(),
        answersStreamForQuestion: (_) => Stream.value([answer]),
      ),
    ),
  );
  await tester.pump();
  await tester.tap(find.text(question.title));
  await tester.pumpAndSettle();
}

class _ActionRepository implements CollaborationRepository {
  bool edited = false;
  bool reported = false;

  @override
  Future<void> editAnswer({
    required String studentId,
    required String answerId,
    required String text,
  }) async {
    edited = true;
  }

  @override
  Future<void> report({
    required String targetType,
    required String targetId,
    required String reason,
  }) async {
    reported = true;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeFirestore implements FirebaseFirestore {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeFunctions implements FirebaseFunctions {
  _FakeFunctions(this.results);

  final Map<String, Map<String, dynamic>> results;
  final Map<String, Map<String, dynamic>> calls = {};

  @override
  dynamic noSuchMethod(Invocation invocation) {
    if (invocation.memberName == #httpsCallable) {
      final name = invocation.positionalArguments.first as String;
      return _FakeHttpsCallable((parameters) async {
        calls[name] = Map<String, dynamic>.from(parameters);
        return _FakeHttpsCallableResult(results[name] ?? {});
      });
    }
    return super.noSuchMethod(invocation);
  }
}

class _FakeHttpsCallable implements HttpsCallable {
  _FakeHttpsCallable(this._handler);

  final Future<_FakeHttpsCallableResult> Function(Map<String, dynamic>)
  _handler;

  @override
  Future<HttpsCallableResult<T>> call<T>([dynamic parameters]) async {
    final result = await _handler(Map<String, dynamic>.from(parameters as Map));
    return _FakeHttpsCallableResult<T>(result.data as T);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeHttpsCallableResult<T> implements HttpsCallableResult<T> {
  _FakeHttpsCallableResult(this.data);

  @override
  final T data;
}
