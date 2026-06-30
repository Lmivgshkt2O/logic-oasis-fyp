import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/quiz/result_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';

void main() {
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

    await tester.tap(find.text('Back to Forge'));

    expect(returnedToForge, isTrue);
  });
}
