import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/collaboration/qa_forum/qa_forum_page.dart';
import 'package:logic_oasis/features/quiz/result_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/forum_answer.dart';
import 'package:logic_oasis/shared/models/next_learning_action.dart';
import 'package:logic_oasis/shared/models/forum_question.dart';
import 'package:logic_oasis/shared/models/quiz_completion.dart';
import 'package:logic_oasis/shared/models/quiz_review_item.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';
import 'package:logic_oasis/shared/repositories/collaboration_repository.dart';

const _completion = QuizCompletion(
  correctCount: 3,
  totalQuestions: 5,
  score: 60,
  timeTakenSeconds: 3,
  reviewItems: <QuizReviewItem>[
    QuizReviewItem(
      questionId: 'question-1',
      sequenceIndex: 2,
      questionText: 'Which numeral is correct?',
      questionTextBm: 'Angka manakah betul?',
      questionType: 'Place value',
      questionTypeBm: 'Nilai tempat',
      reviewFocus: 'Check the value of each digit.',
      reviewFocusBm: 'Semak nilai setiap digit.',
    ),
  ],
);

Widget _resultPage({
  required bool isBahasaMelayu,
  QuizReward? reward,
  CollaborationRepository? forumRepository,
}) {
  return MaterialApp(
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    locale: isBahasaMelayu ? const Locale('ms') : const Locale('en'),
    home: ResultPage(
      completion: _completion,
      topicArea: isBahasaMelayu ? 'Nombor Bulat' : 'Whole Numbers',
      isBahasaMelayu: isBahasaMelayu,
      topicId: 'whole_numbers_y4',
      subtopicId: 'read_write_numbers',
      yearLevel: 4,
      reward: reward,
      forumRepository: forumRepository,
    ),
  );
}

class _DiscussRepository implements CollaborationRepository {
  String? openedQuestionId;
  bool fail = false;

  @override
  Future<LinkedDiscussion> openOrCreateLinkedDiscussion({
    required String questionId,
  }) async {
    if (fail) {
      throw Exception('discussion unavailable');
    }
    openedQuestionId = questionId;
    return LinkedDiscussion(
      id: 'linked_$questionId',
      sourceQuestionId: questionId,
      sourceContentVersion: 'v1',
      prompt: 'Which numeral is correct?',
      promptBm: 'Angka manakah betul?',
      options: const ['20 004', '24 000', '20 400', '20 040'],
      optionsBm: const ['20 004', '24 000', '20 400', '20 040'],
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

void main() {
  testWidgets('server-confirmed result does not display a client reward', (
    tester,
  ) async {
    await tester.pumpWidget(_resultPage(isBahasaMelayu: false));

    expect(find.text('60%'), findsOneWidget);
    expect(
      find.text(
        'This score was confirmed by the server and your learning progress is being updated.',
      ),
      findsOneWidget,
    );
    expect(find.text('Crystals'), findsNothing);
  });

  testWidgets('quiz result returns a typed back action to the caller', (
    tester,
  ) async {
    NextLearningAction? returnedAction;
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: FilledButton(
                onPressed: () async {
                  returnedAction = await Navigator.of(context).push<
                    NextLearningAction
                  >(
                    MaterialPageRoute<NextLearningAction>(
                      builder: (_) => const ResultPage(
                        completion: _completion,
                        topicArea: 'Fraction Bridge',
                        isBahasaMelayu: false,
                        topicId: 'whole_numbers_y4',
                        subtopicId: 'read_write_numbers',
                        yearLevel: 4,
                        reward: QuizReward(
                          score: 80,
                          earnedCrystals: 40,
                          previousMastery: 'Moderate',
                          newMastery: 'Strong',
                          encouragement: 'Great work.',
                        ),
                      ),
                    ),
                  );
                },
                child: const Text('Open result'),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Open result'));
    await tester.pumpAndSettle();

    expect(find.text('Back to Forge'), findsOneWidget);
    expect(find.text('Review these first'), findsOneWidget);
    expect(find.text('Which numeral is correct?'), findsOneWidget);
    expect(find.text('Place value'), findsOneWidget);
    expect(find.text('Check the value of each digit.'), findsOneWidget);

    final backToForge = find.text('Back to Forge');
    await tester.ensureVisible(backToForge);
    await tester.tap(backToForge);
    await tester.pumpAndSettle();

    expect(returnedAction, isNotNull);
    expect(returnedAction!.isBack, isTrue);
  });

  testWidgets('review card opens the canonical linked discussion', (
    tester,
  ) async {
    final repository = _DiscussRepository();
    await tester.pumpWidget(_resultPage(isBahasaMelayu: false, forumRepository: repository));

    expect(find.text('Discuss in forum'), findsOneWidget);
    await tester.tap(find.text('Discuss in forum'));
    await tester.pumpAndSettle();

    expect(repository.openedQuestionId, 'question-1');
    expect(find.byType(ForumDiscussionPage), findsOneWidget);
    expect(find.text('Which numeral is correct?'), findsWidgets);
  });

  testWidgets('review card discussion entry uses Bahasa Melayu copy', (
    tester,
  ) async {
    final repository = _DiscussRepository();
    await tester.pumpWidget(_resultPage(isBahasaMelayu: true, forumRepository: repository));

    expect(find.text('Bincang dalam forum'), findsOneWidget);
    await tester.tap(find.text('Bincang dalam forum'));
    await tester.pumpAndSettle();

    expect(repository.openedQuestionId, 'question-1');
    expect(find.byType(ForumDiscussionPage), findsOneWidget);
  });

  testWidgets('discussion entry failure shows a localized message and stays put', (
    tester,
  ) async {
    final repository = _DiscussRepository()..fail = true;
    await tester.pumpWidget(_resultPage(isBahasaMelayu: false, forumRepository: repository));

    await tester.tap(find.text('Discuss in forum'));
    await tester.pumpAndSettle();

    expect(
      find.text('This question is not available for discussion.'),
      findsOneWidget,
    );
    expect(find.byType(ForumDiscussionPage), findsNothing);
    expect(find.text('Review these first'), findsOneWidget);
  });
}
