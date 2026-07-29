import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/quiz/result_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';

void main() {
  testWidgets('result surfaces an analysis stream error and retries safely', (
    tester,
  ) async {
    var watchCount = 0;
    Stream<AiDiagnosis?> watchAttempt(String _) {
      watchCount += 1;
      if (watchCount == 1) {
        return Stream<AiDiagnosis?>.error(StateError('hidden diagnostic'));
      }
      return Stream<AiDiagnosis?>.value(
        const AiDiagnosis(
          attemptId: 'attempt_retry',
          studentId: 'student_a',
          sourceAttemptSequence: 1,
          analysisState: 'completed',
          displayCode: 'analysis_completed',
        ),
      );
    }

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ResultPage(
          correctCount: 3,
          totalQuestions: 5,
          topicArea: 'Fraction Bridge',
          isBahasaMelayu: false,
          attemptId: 'attempt_retry',
          aiDiagnosisStreamFactory: watchAttempt,
          onBackToForge: () {},
        ),
      ),
    );
    await tester.pump();

    expect(find.textContaining('temporarily unavailable'), findsOneWidget);
    expect(find.text('Retry analysis'), findsOneWidget);
    expect(find.textContaining('hidden diagnostic'), findsNothing);

    final retryAnalysis = find.text('Retry analysis');
    await tester.ensureVisible(retryAnalysis);
    await tester.tap(retryAnalysis);
    await tester.pumpAndSettle();

    expect(watchCount, 2);
    expect(find.text('Next practice step'), findsOneWidget);
    expect(find.text('Your next practice is ready.'), findsOneWidget);
  });

  testWidgets('result localizes the safe analysis error state in Malay', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ResultPage(
          correctCount: 3,
          totalQuestions: 5,
          topicArea: 'Jambatan Pecahan',
          isBahasaMelayu: true,
          attemptId: 'attempt_retry_bm',
          aiDiagnosisStreamFactory: (_) =>
              Stream<AiDiagnosis?>.error(StateError('hidden diagnostic')),
          onBackToForge: () {},
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Status analisis tidak tersedia'), findsOneWidget);
    expect(find.text('Cuba semula analisis'), findsOneWidget);
    expect(find.textContaining('hidden diagnostic'), findsNothing);
  });

  testWidgets('result keeps the score immediate while analysis is processing', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ResultPage(
          correctCount: 1,
          totalQuestions: 5,
          topicArea: 'Fraction Bridge',
          isBahasaMelayu: false,
          reward: const QuizReward(
            score: 20,
            earnedCrystals: 10,
            previousMastery: 'New',
            newMastery: 'Building',
            encouragement: 'Keep going.',
          ),
          aiDiagnosis: const AiDiagnosis(
            attemptId: 'attempt_001',
            studentId: 'student_a',
            sourceAttemptSequence: 1,
            analysisState: 'processing',
            displayCode: 'analysis_pending',
          ),
          onBackToForge: () {},
        ),
      ),
    );

    expect(find.text('20%'), findsOneWidget);
    expect(find.text('Learning analysis'), findsOneWidget);
    expect(find.textContaining('Preparing your next practice'), findsOneWidget);
  });

  testWidgets('result labels controlled demonstration model evidence safely', (
    tester,
  ) async {
    Widget controlledResult({required bool isBahasaMelayu}) {
      return MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ResultPage(
          correctCount: 4,
          totalQuestions: 5,
          topicArea: 'Fraction Bridge',
          isBahasaMelayu: isBahasaMelayu,
          reward: const QuizReward(
            score: 80,
            earnedCrystals: 20,
            previousMastery: 'Building',
            newMastery: 'Strong',
            encouragement: 'Keep going.',
          ),
          aiDiagnosis: const AiDiagnosis(
            attemptId: 'attempt_002',
            studentId: 'student_a',
            sourceAttemptSequence: 2,
            analysisState: 'completed',
            displayCode: 'analysis_completed',
            modelEvidenceState: 'controlled_demonstration',
          ),
          onBackToForge: () {},
        ),
      );
    }

    await tester.pumpWidget(controlledResult(isBahasaMelayu: false));

    expect(
      find.textContaining('controlled demonstration model'),
      findsOneWidget,
    );
    expect(find.textContaining('not real-world validated'), findsOneWidget);

    await tester.pumpWidget(controlledResult(isBahasaMelayu: true));

    expect(find.textContaining('model demonstrasi terkawal'), findsOneWidget);
    expect(find.textContaining('belum disahkan'), findsOneWidget);
  });
}
