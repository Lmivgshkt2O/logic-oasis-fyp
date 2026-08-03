import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/collaboration/qa_forum/qa_forum_page.dart';
import 'package:logic_oasis/shared/models/forum_answer.dart';
import 'package:logic_oasis/shared/models/forum_question.dart';
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
    expect(find.textContaining('unavailable for your account'), findsOneWidget);
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
}
