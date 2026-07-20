import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/quiz/result_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';

void main() {
  testWidgets('server-confirmed result does not display a client reward', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ResultPage(
          correctCount: 3,
          totalQuestions: 5,
          topicArea: 'Whole Numbers',
          isBahasaMelayu: false,
          onBackToForge: () {},
        ),
      ),
    );

    expect(find.text('60%'), findsOneWidget);
    expect(
      find.text(
        'This score was confirmed by the server and your learning progress is being updated.',
      ),
      findsOneWidget,
    );
    expect(find.text('Crystals'), findsNothing);
  });

  testWidgets('quiz result shows a back to forge action', (tester) async {
    var returnedToForge = false;

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ResultPage(
          correctCount: 4,
          totalQuestions: 5,
          topicArea: 'Fraction Bridge',
          isBahasaMelayu: false,
          reward: const QuizReward(
            score: 80,
            earnedCrystals: 40,
            previousMastery: 'Moderate',
            newMastery: 'Strong',
            encouragement: 'Great work.',
          ),
          onBackToForge: () {
            returnedToForge = true;
          },
        ),
      ),
    );

    expect(find.text('Back to Forge'), findsOneWidget);
    expect(find.text('Mistakes'), findsOneWidget);
    expect(find.text('1 to review'), findsOneWidget);
    expect(
      find.text('Next action: Review 1 mistake, then try a new topic.'),
      findsOneWidget,
    );

    final backToForge = find.text('Back to Forge');
    await tester.ensureVisible(backToForge);
    await tester.tap(backToForge);

    expect(returnedToForge, isTrue);
  });
}
