import 'dart:async';
import 'dart:convert';

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

  test('public advisory badge exposes only allow-listed states', () {
    const service = ForumAiStatusService();
    expect(service.publicBadgeLabel('verified'), 'AI-verified');
    expect(service.publicBadgeLabel('may_be_irrelevant'), 'May be irrelevant');
    expect(service.publicBadgeLabel('none'), isNull);
    expect(
      service.publicBadgeExplanation('verified'),
      contains('automated checks'),
    );
    expect(
      service.publicBadgeLabel('verified', isBahasaMelayu: true),
      'AI-disahkan',
    );
    expect(
      service.publicBadgeLabel('may_be_irrelevant', isBahasaMelayu: true),
      'Mungkin tidak berkaitan',
    );
    expect(
      service.publicBadgeExplanation(
        'may_be_irrelevant',
        isBahasaMelayu: true,
      ),
      contains('mungkin tidak menjawab'),
    );
  });

  test('composite author guidance renders author-only messages', () {
    const service = ForumAiStatusService();
    const correction = ForumAnswerFeedback(
      state: 'completed',
      label: 'correction_needed',
      message: '',
      correctness: 'incorrect',
      relevance: 'relevant',
      reasoning: 'sufficient_reasoning',
    );
    expect(
      service.statusText(correction),
      contains('does not match the worked answer key'),
    );
    expect(
      service.statusText(correction, isBahasaMelayu: true),
      contains('tidak sepadan dengan kunci jawapan'),
    );

    const irrelevant = ForumAnswerFeedback(
      state: 'completed',
      label: 'may_be_irrelevant',
      message: '',
      correctness: 'correct',
      relevance: 'irrelevant',
      reasoning: 'sufficient_reasoning',
    );
    expect(
      service.statusText(irrelevant),
      contains('may not address the question'),
    );

    const verified = ForumAnswerFeedback(
      state: 'completed',
      label: 'verified',
      message: '',
      correctness: 'correct',
      relevance: 'relevant',
      reasoning: 'sufficient_reasoning',
    );
    expect(
      service.statusText(verified),
      contains('automated checks'),
    );
    expect(
      service.statusText(
        verified,
        isBahasaMelayu: true,
      ),
      contains('semakan automatik'),
    );

    const needsReasoning = ForumAnswerFeedback(
      state: 'completed',
      label: 'needs_reasoning',
      message: '',
      correctness: 'correct',
      relevance: 'relevant',
      reasoning: 'needs_reasoning',
    );
    expect(
      service.statusText(needsReasoning),
      contains('Please add the steps'),
    );
  });

  testWidgets('composite correction guidance is visible only to the author', (
    tester,
  ) async {
    final answers = StreamController<List<ForumAnswer>>();
    addTearDown(answers.close);
    const question = ForumQuestion(
      id: 'linked_q1_v1',
      authorId: '',
      title: 'Which numeral shows twenty thousand and four?',
      text: 'Which numeral shows twenty thousand and four?',
      mode: 'linked',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: ForumDiscussionPage(
          question: question,
          state: AppState(),
          answersStream: answers.stream,
          blockedStudentIdsStream: Stream.value(const <String>{}),
          authorFeedbackStreamForAnswer: (_) => Stream.value(
            const ForumAnswerFeedback(
              state: 'completed',
              label: 'correction_needed',
              message: '',
              correctness: 'incorrect',
              relevance: 'relevant',
              reasoning: 'sufficient_reasoning',
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    answers.add([
      const ForumAnswer(
        id: 'linked_a1',
        questionId: 'linked_q1_v1',
        authorId: AppState.demoStudentId,
        text: '',
        mode: 'linked',
        selectedOption: 1,
        explanation: 'I compared the thousands digit.',
        aiPublicState: 'none',
        feedback: ForumAnswerFeedback(
          state: 'queued',
          label: 'uncertain',
          message: '',
        ),
      ),
    ]);
    await tester.pump();
    await tester.pump();

    expect(
      find.textContaining('does not match the worked answer key'),
      findsOneWidget,
    );
  });

  test('linked discussion projection builds the forum question model', () {
    const discussion = LinkedDiscussion(
      id: 'linked_bank_q1_v1',
      sourceQuestionId: 'bank_q1',
      sourceContentVersion: 'v1',
      prompt: 'Which numeral shows twenty thousand and four?',
      promptBm: 'Angka manakah menunjukkan dua puluh ribu empat?',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    final question = ForumQuestion.fromLinkedDiscussion(discussion);
    expect(question.id, 'linked_bank_q1_v1');
    expect(question.mode, 'linked');
    expect(question.sourceQuestionId, 'bank_q1');
    expect(question.options, hasLength(4));
    expect(question.prompt, 'Which numeral shows twenty thousand and four?');
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
      'selectedOption': '1',
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
      'selectedOption': '2',
      'explanation': 'I checked by adding back the group.',
    });
  });

  test('forum paging cursor round-trips timestamp and id and rejects malformed input', () {
    final updatedAt = DateTime.utc(2026, 8, 1, 10, 30, 15, 123, 456);
    final cursor = encodeForumQuestionCursor(
      id: 'q42',
      data: {'updatedAt': Timestamp.fromDate(updatedAt)},
    );
    final decoded = decodeForumQuestionCursor(cursor);
    expect(decoded.id, 'q42');
    expect(decoded.updatedAt, updatedAt);

    expect(
      () => decodeForumQuestionCursor('not-base64'),
      throwsFormatException,
    );
    expect(
      () => decodeForumQuestionCursor(
        base64Url.encode(utf8.encode('{}')),
      ),
      throwsFormatException,
    );
    expect(
      () => decodeForumQuestionCursor(
        base64Url.encode(utf8.encode('{"u":"","i":"x"}')),
      ),
      throwsFormatException,
    );
  });

  testWidgets('forum shows loading, empty, filter, and clear-filter states', (
    tester,
  ) async {
    final pager = _ControlledPager()..gate = Completer<void>();
    final latest = StreamController<List<ForumQuestion>>();
    final blocked = StreamController<Set<String>>();
    addTearDown(latest.close);
    addTearDown(blocked.close);
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          questionPager: pager.call,
          latestQuestionsStream: latest.stream,
          blockedStudentIdsStream: blocked.stream,
        ),
      ),
    );
    blocked.add(const {});
    await tester.pump();
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    pager.gate!.complete();
    pager.gate = null;
    await tester.pump();
    expect(find.textContaining('No questions yet'), findsOneWidget);

    const twoQuestions = <ForumQuestion>[
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
    ];
    pager.page = twoQuestions;
    latest.add(twoQuestions);
    await tester.pump();
    await tester.pump();
    expect(find.text('How can I check subtraction?'), findsOneWidget);
    expect(find.text('How do place values work?'), findsOneWidget);

    blocked.add(const {'student-2'});
    await tester.pump();
    await tester.pump();
    expect(find.text('How can I check subtraction?'), findsNothing);
    expect(find.text('How do place values work?'), findsOneWidget);

    await tester.enterText(find.byType(TextField).first, 'place values');
    await tester.pump();
    await tester.pump();
    expect(find.text('How can I check subtraction?'), findsNothing);
    expect(find.text('How do place values work?'), findsOneWidget);

    await tester.enterText(find.byType(TextField).first, 'geometry');
    await tester.pump();
    await tester.pump();
    expect(find.text('No questions match this filter.'), findsOneWidget);
    await tester.tap(find.byTooltip('Clear filter'));
    await tester.pump();
    await tester.pump();
    expect(find.text('How do place values work?'), findsOneWidget);
  });

  testWidgets('paging loads more than forty questions without duplicates or skips', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(900, 6000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    final questions = List.generate(
      55,
      (index) => ForumQuestion(
        id: 'q$index',
        authorId: 'student-$index',
        title: 'Question $index',
        text: 'Body for question $index',
      ),
    );
    final pager = _PagedPager([
      questions.sublist(0, 20),
      <ForumQuestion>[questions[19], ...questions.sublist(20, 40)],
      questions.sublist(40, 55),
    ]);
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          questionPager: pager.call,
          latestQuestionsStream: Stream.value(const []),
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
    expect(find.byType(Card), findsNWidgets(20));

    await tester.tap(find.text('Load more'));
    await tester.pumpAndSettle();
    expect(pager.requestedCursors, <String?>[null, '1']);
    expect(find.byType(Card), findsNWidgets(40));

    await tester.tap(find.text('Load more'));
    await tester.pumpAndSettle();
    expect(pager.requestedCursors, <String?>[null, '1', '2']);
    expect(find.byType(Card), findsNWidgets(55));
    expect(find.text('Load more'), findsNothing);

    final titles = <String>{};
    for (final question in questions) {
      expect(titles.add(question.title), isTrue);
    }
  });

  testWidgets('load-more error preserves the current page and retries', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(900, 6000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    final questions = List.generate(
      40,
      (index) => ForumQuestion(
        id: 'q$index',
        authorId: 'student-$index',
        title: 'Question $index',
        text: 'Body for question $index',
      ),
    );
    final pager = _PagedPager([
      questions.sublist(0, 20),
      questions.sublist(20, 40),
    ])
      ..failOnce('1');
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          questionPager: pager.call,
          latestQuestionsStream: Stream.value(const []),
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
    expect(find.byType(Card), findsNWidgets(20));

    await tester.tap(find.text('Load more'));
    await tester.pumpAndSettle();
    expect(find.textContaining('current list is unchanged'), findsOneWidget);
    expect(find.byType(Card), findsNWidgets(20));

    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(find.byType(Card), findsNWidgets(40));
    expect(find.text('Load more'), findsNothing);
  });

  testWidgets('ordering-affecting live change refetches from the first page', (
    tester,
  ) async {
    const firstPage = <ForumQuestion>[
      ForumQuestion(
        id: 'q0',
        authorId: 'a',
        title: 'First question',
        text: 'Body zero.',
      ),
      ForumQuestion(
        id: 'q1',
        authorId: 'b',
        title: 'Second question',
        text: 'Body one.',
      ),
    ];
    final pager = _ControlledPager()..page = firstPage;
    final latest = StreamController<List<ForumQuestion>>();
    addTearDown(latest.close);
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          questionPager: pager.call,
          latestQuestionsStream: latest.stream,
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
    expect(find.text('First question'), findsOneWidget);
    final callsAfterLoad = pager.calls;

    latest.add(firstPage);
    await tester.pump();
    await tester.pump();
    expect(pager.calls, callsAfterLoad);

    const newest = ForumQuestion(
      id: 'q-new',
      authorId: 'c',
      title: 'Newest question',
      text: 'Body newest.',
    );
    latest.add(<ForumQuestion>[newest, firstPage[0]]);
    await tester.pump();
    await tester.pump();
    expect(pager.calls, greaterThan(callsAfterLoad));
    expect(find.text('First question'), findsOneWidget);
  });

  testWidgets('filter changes reset the accumulated paging state', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(900, 6000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    final questions = List.generate(
      40,
      (index) => ForumQuestion(
        id: 'q$index',
        authorId: 'student-$index',
        title: 'Question $index',
        text: 'Body for question $index',
      ),
    );
    final pager = _PagedPager([
      questions.sublist(0, 20),
      questions.sublist(20, 40),
    ]);
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          questionPager: pager.call,
          latestQuestionsStream: Stream.value(const []),
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
    await tester.tap(find.text('Load more'));
    await tester.pumpAndSettle();
    expect(pager.requestedCursors, <String?>[null, '1']);

    await tester.enterText(find.byType(TextField).first, 'Question 3');
    await tester.pump();
    await tester.pump();
    expect(pager.requestedCursors, <String?>[null, '1', null]);
    expect(find.widgetWithText(Card, 'Question 3'), findsOneWidget);
    expect(find.text('Load more'), findsOneWidget);
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
          questionPager: ({required int limit, String? cursor}) async =>
              const ForumQuestionPage(
                questions: const [question],
                nextCursor: null,
                hasMore: false,
              ),
          latestQuestionsStream: Stream.value(const [question]),
          blockedStudentIdsStream: blocked,
          answersStreamForQuestion: (_) => Stream.value([answer]),
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
          questionPager: ({required int limit, String? cursor}) async =>
              const ForumQuestionPage(
                questions: const [question],
                nextCursor: null,
                hasMore: false,
              ),
          latestQuestionsStream: Stream.value(const [question]),
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
          questionPager: ({required int limit, String? cursor}) async =>
              const ForumQuestionPage(
                questions: [],
                nextCursor: null,
                hasMore: false,
              ),
          latestQuestionsStream: Stream.value(const []),
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    expect(find.text('Forum S&J'), findsOneWidget);
    expect(find.text('Tanya soalan'), findsOneWidget);
    expect(find.text('Tapis soalan'), findsOneWidget);
  });

  testWidgets('linked question prompt switches to Bahasa Melayu', (
    tester,
  ) async {
    final state = AppState()..language = 'Bahasa Melayu';
    const question = ForumQuestion(
      id: 'linked_q1_v1',
      authorId: '',
      title: 'Which numeral shows twenty thousand and four?',
      text: 'Which numeral shows twenty thousand and four?',
      mode: 'linked',
      prompt: 'Which numeral shows twenty thousand and four?',
      promptBm: 'Angka manakah menunjukkan dua puluh ribu empat?',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: ForumDiscussionPage(
          question: question,
          state: state,
          answersStream: Stream.value(const <ForumAnswer>[]),
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Angka manakah menunjukkan dua puluh ribu empat?'), findsOneWidget);
    expect(find.text('Which numeral shows twenty thousand and four?'), findsNothing);
  });

  testWidgets('question list shows the Bahasa Melayu prompt for linked threads', (
    tester,
  ) async {
    final state = AppState()..language = 'Bahasa Melayu';
    const question = ForumQuestion(
      id: 'linked_q1_v1',
      authorId: '',
      title: 'Which numeral shows twenty thousand and four?',
      text: 'Which numeral shows twenty thousand and four?',
      mode: 'linked',
      prompt: 'Which numeral shows twenty thousand and four?',
      promptBm: 'Angka manakah menunjukkan dua puluh ribu empat?',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: state,
          questionPager: ({required int limit, String? cursor}) async =>
              const ForumQuestionPage(
                questions: [question],
                nextCursor: null,
                hasMore: false,
              ),
          latestQuestionsStream: Stream.value(const [question]),
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(
      find.text('Angka manakah menunjukkan dua puluh ribu empat?'),
      findsNWidgets(2),
    );
  });

  testWidgets('author can delete their own answer after confirmation', (
    tester,
  ) async {
    final repository = _ActionRepository();
    const question = ForumQuestion(
      id: 'question-delete-answer',
      authorId: 'student-question-author',
      title: 'How can I check this calculation?',
      text: 'I want another student to review each calculation step.',
    );
    final answer = ForumAnswer(
      id: 'answer-to-delete',
      questionId: question.id,
      authorId: AppState.demoStudentId,
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
          questionPager: ({required int limit, String? cursor}) async =>
              const ForumQuestionPage(
                questions: [question],
                nextCursor: null,
                hasMore: false,
              ),
          latestQuestionsStream: Stream.value(const [question]),
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

    await tester.ensureVisible(find.byTooltip('Answer actions'));
    await tester.tap(find.byTooltip('Answer actions'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Delete answer'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Delete'));
    await tester.pumpAndSettle();

    expect(repository.deletedAnswerId, 'answer-to-delete');
    expect(find.text('Answer deleted.'), findsOneWidget);
  });

  testWidgets('author can delete their own free-form question after confirmation', (
    tester,
  ) async {
    final repository = _ActionRepository();
    const question = ForumQuestion(
      id: 'question-to-delete',
      authorId: AppState.demoStudentId,
      title: 'How do I regroup 46 plus 27?',
      text: 'I want to check whether my regrouping order is correct.',
    );
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          repository: repository,
          questionPager: ({required int limit, String? cursor}) async =>
              const ForumQuestionPage(
                questions: [question],
                nextCursor: null,
                hasMore: false,
              ),
          latestQuestionsStream: Stream.value(const [question]),
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    await tester.ensureVisible(find.byTooltip('Question actions'));
    await tester.tap(find.byTooltip('Question actions'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Delete question'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Delete'));
    await tester.pumpAndSettle();

    expect(repository.deletedQuestionId, 'question-to-delete');
  });

  testWidgets('student can remove a linked question from their own list', (
    tester,
  ) async {
    final repository = _ActionRepository();
    const question = ForumQuestion(
      id: 'linked_q1_v1',
      authorId: '',
      title: 'Which numeral shows twenty thousand and four?',
      text: 'Which numeral shows twenty thousand and four?',
      mode: 'linked',
      prompt: 'Which numeral shows twenty thousand and four?',
      promptBm: 'Angka manakah menunjukkan dua puluh ribu empat?',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          repository: repository,
          questionPager: ({required int limit, String? cursor}) async =>
              const ForumQuestionPage(
                questions: [question],
                nextCursor: null,
                hasMore: false,
              ),
          latestQuestionsStream: Stream.value(const [question]),
          blockedStudentIdsStream: Stream.value(const <String>{}),
          deletedQuestionIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    await tester.ensureVisible(find.byTooltip('Question actions'));
    await tester.tap(find.byTooltip('Question actions'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Delete question'));
    await tester.pumpAndSettle();
    expect(
      find.text('Remove this question from your list?'),
      findsOneWidget,
    );
    await tester.tap(find.text('Delete'));
    await tester.pumpAndSettle();

    expect(repository.deletedQuestionId, 'linked_q1_v1');
  });

  testWidgets('deleted linked questions are hidden from the student list', (
    tester,
  ) async {
    const question = ForumQuestion(
      id: 'linked_q1_v1',
      authorId: '',
      title: 'Which numeral shows twenty thousand and four?',
      text: 'Which numeral shows twenty thousand and four?',
      mode: 'linked',
      prompt: 'Which numeral shows twenty thousand and four?',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          questionPager: ({required int limit, String? cursor}) async =>
              const ForumQuestionPage(
                questions: [question],
                nextCursor: null,
                hasMore: false,
              ),
          latestQuestionsStream: Stream.value(const [question]),
          blockedStudentIdsStream: Stream.value(const <String>{}),
          deletedQuestionIdsStream: Stream.value(const {'linked_q1_v1'}),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('Which numeral shows twenty thousand and four?'), findsNothing);
  });

  testWidgets('linked discussion renders options, explanation, and validation', (
    tester,
  ) async {
    final answers = StreamController<List<ForumAnswer>>();
    addTearDown(answers.close);
    const question = ForumQuestion(
      id: 'linked_q1_v1',
      authorId: '',
      title: 'Which numeral shows twenty thousand and four?',
      text: 'Which numeral shows twenty thousand and four?',
      mode: 'linked',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: ForumDiscussionPage(
          question: question,
          state: AppState(),
          answersStream: answers.stream,
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    answers.add(const []);
    await tester.pump();

    expect(find.text('Choose your final answer'), findsOneWidget);
    expect(find.text('Explain your answer'), findsOneWidget);
    expect(find.text('Submit answer'), findsOneWidget);
    await tester.enterText(
      find.byType(TextField).last,
      'I compared each digit from left to right.',
    );
    await tester.ensureVisible(find.text('Submit answer'));
    await tester.tap(find.text('Submit answer'));
    await tester.pump();
    expect(find.text('Select an option first.'), findsOneWidget);
  });

  testWidgets('linked composer submits the selected option and explanation', (
    tester,
  ) async {
    final answers = StreamController<List<ForumAnswer>>();
    addTearDown(answers.close);
    final repository = _LinkedActionRepository();
    const question = ForumQuestion(
      id: 'linked_q1_v1',
      authorId: '',
      title: 'Which numeral shows twenty thousand and four?',
      text: 'Which numeral shows twenty thousand and four?',
      mode: 'linked',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: ForumDiscussionPage(
          question: question,
          state: AppState(),
          repository: repository,
          answersStream: answers.stream,
          blockedStudentIdsStream: Stream.value(const <String>{}),
          authorFeedbackStreamForAnswer: (_) => Stream.value(
            const ForumAnswerFeedback(
              state: 'queued',
              label: 'uncertain',
              message: '',
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    answers.add(const []);
    await tester.pump();

    await tester.tap(find.text('24 000'));
    await tester.enterText(
      find.byType(TextField).last,
      '  I compared the thousands digit.  ',
    );
    await tester.ensureVisible(find.text('Submit answer'));
    await tester.tap(find.text('Submit answer'));
    await tester.pumpAndSettle();

    expect(repository.submittedDiscussionId, 'linked_q1_v1');
    expect(repository.submittedOption, 1);
    expect(repository.submittedExplanation, 'I compared the thousands digit.');
    expect(find.textContaining('queued for review'), findsOneWidget);
  });

  testWidgets('linked composer uses Bahasa Melayu labels', (tester) async {
    final answers = StreamController<List<ForumAnswer>>();
    addTearDown(answers.close);
    final state = AppState()..language = 'Bahasa Melayu';
    const question = ForumQuestion(
      id: 'linked_q1_v1',
      authorId: '',
      title: 'Angka manakah menunjukkan dua puluh ribu empat?',
      text: 'Angka manakah menunjukkan dua puluh ribu empat?',
      mode: 'linked',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: ForumDiscussionPage(
          question: question,
          state: state,
          answersStream: answers.stream,
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    answers.add(const []);
    await tester.pump();

    expect(find.text('Pilih jawapan akhir'), findsOneWidget);
    expect(find.text('Terangkan jawapan anda'), findsOneWidget);
    expect(find.text('Hantar jawapan'), findsOneWidget);
  });

  testWidgets('linked answer shows option, explanation, and public badge', (
    tester,
  ) async {
    final answers = StreamController<List<ForumAnswer>>();
    addTearDown(answers.close);
    const question = ForumQuestion(
      id: 'linked_q1_v1',
      authorId: '',
      title: 'Which numeral shows twenty thousand and four?',
      text: 'Which numeral shows twenty thousand and four?',
      mode: 'linked',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: ForumDiscussionPage(
          question: question,
          state: AppState(),
          answersStream: answers.stream,
          blockedStudentIdsStream: Stream.value(const <String>{}),
          authorFeedbackStreamForAnswer: (_) => Stream.value(
            const ForumAnswerFeedback(
              state: 'completed',
              label: 'sufficient_reasoning',
              message: 'Private guidance.',
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    answers.add(const [
      ForumAnswer(
        id: 'linked_a1',
        questionId: 'linked_q1_v1',
        authorId: 'student-peer',
        text: '',
        mode: 'linked',
        selectedOption: 0,
        explanation: 'I compared the digits from left to right.',
        aiPublicState: 'verified',
        aiRunId: 'run-1',
        aiRevision: 1,
        feedback: ForumAnswerFeedback(
          state: 'queued',
          label: 'uncertain',
          message: '',
        ),
      ),
    ]);
    await tester.pump();

    expect(find.text('I compared the digits from left to right.'), findsOneWidget);
    expect(find.textContaining('Final answer:'), findsOneWidget);
    expect(find.text('AI-verified'), findsOneWidget);
    expect(find.text('Private guidance.'), findsNothing);
  });

  testWidgets('author sees private guidance while peers see only public state', (
    tester,
  ) async {
    final answers = StreamController<List<ForumAnswer>>();
    addTearDown(answers.close);
    const question = ForumQuestion(
      id: 'linked_q1_v1',
      authorId: '',
      title: 'Which numeral shows twenty thousand and four?',
      text: 'Which numeral shows twenty thousand and four?',
      mode: 'linked',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: ForumDiscussionPage(
          question: question,
          state: AppState(),
          answersStream: answers.stream,
          blockedStudentIdsStream: Stream.value(const <String>{}),
          authorFeedbackStreamForAnswer: (_) => Stream.value(
            const ForumAnswerFeedback(
              state: 'completed',
              label: 'needs_reasoning',
              message: 'Please add more reasoning.',
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    answers.add([
      const ForumAnswer(
        id: 'linked_a1',
        questionId: 'linked_q1_v1',
        authorId: AppState.demoStudentId,
        text: '',
        mode: 'linked',
        selectedOption: 1,
        explanation: 'I compared the thousands digit.',
        aiPublicState: 'may_be_irrelevant',
        feedback: ForumAnswerFeedback(
          state: 'queued',
          label: 'uncertain',
          message: '',
        ),
      ),
    ]);
    await tester.pump();
    await tester.pump();

    expect(find.textContaining('Please add the steps'), findsOneWidget);
    expect(find.text('May be irrelevant'), findsOneWidget);
  });

  testWidgets('editing a linked answer clears the public badge via the stream', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(900, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    final answers = StreamController<List<ForumAnswer>>();
    addTearDown(answers.close);
    final repository = _LinkedActionRepository();
    const question = ForumQuestion(
      id: 'linked_q1_v1',
      authorId: '',
      title: 'Which numeral shows twenty thousand and four?',
      text: 'Which numeral shows twenty thousand and four?',
      mode: 'linked',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: ForumDiscussionPage(
          question: question,
          state: AppState(),
          repository: repository,
          answersStream: answers.stream,
          blockedStudentIdsStream: Stream.value(const <String>{}),
          authorFeedbackStreamForAnswer: (_) => Stream.value(
            const ForumAnswerFeedback(
              state: 'queued',
              label: 'uncertain',
              message: '',
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    answers.add([
      const ForumAnswer(
        id: 'linked_a1',
        questionId: 'linked_q1_v1',
        authorId: AppState.demoStudentId,
        text: '',
        mode: 'linked',
        selectedOption: 0,
        explanation: 'I compared the digits from left to right.',
        aiPublicState: 'verified',
        aiRunId: 'run-1',
        aiRevision: 1,
        feedback: ForumAnswerFeedback(
          state: 'queued',
          label: 'uncertain',
          message: '',
        ),
      ),
    ]);
    await tester.pump();
    expect(find.text('AI-verified'), findsOneWidget);

    await tester.ensureVisible(find.byTooltip('Answer actions'));
    await tester.tap(find.byTooltip('Answer actions'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Edit answer'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('24 000').last);
    await tester.enterText(
      find.byType(TextField).last,
      'A revised explanation with more steps.',
    );
    await tester.ensureVisible(find.text('Submit'));
    await tester.tap(find.text('Submit'));
    await tester.pumpAndSettle();

    expect(repository.editedAnswerId, 'linked_a1');
    expect(repository.editedOption, 1);
    answers.add([
      const ForumAnswer(
        id: 'linked_a1',
        questionId: 'linked_q1_v1',
        authorId: AppState.demoStudentId,
        text: '',
        mode: 'linked',
        selectedOption: 1,
        explanation: 'A revised explanation with more steps.',
        revision: 2,
        aiPublicState: 'none',
        aiRunId: null,
        aiRevision: null,
        feedback: ForumAnswerFeedback(
          state: 'queued',
          label: 'uncertain',
          message: '',
        ),
      ),
    ]);
    await tester.pump();
    await tester.pump();
    expect(find.text('AI-verified'), findsNothing);
  });

  testWidgets('linked answers keep Helpful distinct and have no owner accept', (
    tester,
  ) async {
    final answers = StreamController<List<ForumAnswer>>();
    addTearDown(answers.close);
    const question = ForumQuestion(
      id: 'linked_q1_v1',
      authorId: '',
      title: 'Which numeral shows twenty thousand and four?',
      text: 'Which numeral shows twenty thousand and four?',
      mode: 'linked',
      options: ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: ['20 004', '24 000', '20 400', '20 040'],
    );
    await tester.pumpWidget(
      MaterialApp(
        home: ForumDiscussionPage(
          question: question,
          state: AppState(),
          answersStream: answers.stream,
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    answers.add(const [
      ForumAnswer(
        id: 'linked_a1',
        questionId: 'linked_q1_v1',
        authorId: 'student-peer',
        text: '',
        mode: 'linked',
        selectedOption: 2,
        explanation: 'I compared the thousands and hundreds digits.',
        aiPublicState: 'none',
        feedback: ForumAnswerFeedback(
          state: 'queued',
          label: 'uncertain',
          message: '',
        ),
      ),
    ]);
    await tester.pump();

    expect(find.text('Helpful'), findsOneWidget);
    expect(find.text('Accept'), findsNothing);
    expect(find.textContaining('Final answer:'), findsOneWidget);
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
          questionPager: ({required int limit, String? cursor}) async =>
              const ForumQuestionPage(
                questions: const [question],
                nextCursor: null,
                hasMore: false,
              ),
          latestQuestionsStream: Stream.value(const [question]),
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
          questionPager: ({required int limit, String? cursor}) async =>
              const ForumQuestionPage(
                questions: [],
                nextCursor: null,
                hasMore: false,
              ),
          latestQuestionsStream: Stream.value(const []),
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
    final deniedPager = _ControlledPager()
      ..error = FirebaseException(
        plugin: 'cloud_firestore',
        code: 'permission-denied',
      );
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          state: AppState(),
          questionPager: deniedPager.call,
          latestQuestionsStream: Stream.value(const <ForumQuestion>[]),
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
    expect(find.textContaining('student profile'), findsOneWidget);

    final retryablePager = _ControlledPager()
      ..error = FirebaseException(
        plugin: 'cloud_firestore',
        code: 'unavailable',
      );
    await tester.pumpWidget(
      MaterialApp(
        home: QaForumPage(
          key: const ValueKey('retryable-forum'),
          state: AppState(),
          questionPager: retryablePager.call,
          latestQuestionsStream: Stream.value(const <ForumQuestion>[]),
          blockedStudentIdsStream: Stream.value(const <String>{}),
        ),
      ),
    );
    await tester.pump();
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
        questionPager: ({required int limit, String? cursor}) async =>
            const ForumQuestionPage(
              questions: const [question],
              nextCursor: null,
              hasMore: false,
            ),
        latestQuestionsStream: Stream.value(const [question]),
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
  String? deletedAnswerId;
  String? deletedQuestionId;

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
  Future<void> deleteAnswer(String answerId) async {
    deletedAnswerId = answerId;
  }

  @override
  Future<void> deleteQuestion(String questionId) async {
    deletedQuestionId = questionId;
  }

  @override
  Stream<Set<String>> watchDeletedQuestionIds(String studentId) =>
      const Stream<Set<String>>.empty();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _LinkedActionRepository implements CollaborationRepository {
  String? submittedDiscussionId;
  int? submittedOption;
  String? submittedExplanation;
  String? editedAnswerId;
  int? editedOption;
  String? editedExplanation;

  @override
  Future<String> submitLinkedAnswer({
    required String discussionId,
    required int selectedOption,
    required String explanation,
  }) async {
    submittedDiscussionId = discussionId;
    submittedOption = selectedOption;
    submittedExplanation = explanation;
    return 'linked-a-new';
  }

  @override
  Future<int> editLinkedAnswer({
    required String answerId,
    required int selectedOption,
    required String explanation,
  }) async {
    editedAnswerId = answerId;
    editedOption = selectedOption;
    editedExplanation = explanation;
    return 2;
  }

  @override
  Stream<Set<String>> watchBlockedStudentIds(String studentId) =>
      const Stream<Set<String>>.empty();

  @override
  Stream<Set<String>> watchDeletedQuestionIds(String studentId) =>
      const Stream<Set<String>>.empty();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _ControlledPager {
  List<ForumQuestion> page = const [];
  bool hasMore = false;
  int calls = 0;
  Object? error;
  Completer<void>? gate;

  Future<ForumQuestionPage> call({
    required int limit,
    String? cursor,
  }) async {
    calls += 1;
    final pendingGate = gate;
    if (pendingGate != null) await pendingGate.future;
    final failure = error;
    if (failure != null) {
      error = null;
      throw failure;
    }
    return ForumQuestionPage(
      questions: page,
      nextCursor: null,
      hasMore: hasMore,
    );
  }
}

class _PagedPager {
  _PagedPager(this.pages);

  final List<List<ForumQuestion>> pages;
  final List<String?> requestedCursors = [];
  final Set<String> _failedCursors = {};
  int calls = 0;

  void failOnce(String cursor) => _failedCursors.add(cursor);

  Future<ForumQuestionPage> call({
    required int limit,
    String? cursor,
  }) async {
    calls += 1;
    requestedCursors.add(cursor);
    if (_failedCursors.remove(cursor)) {
      throw Exception('load more failed');
    }
    final index = cursor == null ? 0 : int.parse(cursor);
    final page = pages[index];
    final hasMore = index < pages.length - 1;
    return ForumQuestionPage(
      questions: page,
      nextCursor: hasMore ? '${index + 1}' : null,
      hasMore: hasMore,
    );
  }
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
