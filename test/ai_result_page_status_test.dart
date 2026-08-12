import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/quiz/result_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/quiz_completion.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';

const _completion = QuizCompletion(
  correctCount: 3,
  totalQuestions: 5,
  score: 60,
  timeTakenSeconds: 3,
);

Widget _resultPage({
  required bool isBahasaMelayu,
  required AiDiagnosisStreamFactory? streamFactory,
  AiDiagnosis? aiDiagnosis,
  String? attemptId,
  QuizReward? reward,
}) {
  return MaterialApp(
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    home: ResultPage(
      completion: _completion,
      topicArea: isBahasaMelayu ? 'Jambatan Pecahan' : 'Fraction Bridge',
      isBahasaMelayu: isBahasaMelayu,
      topicId: 'whole_numbers_y4',
      subtopicId: 'read_write_numbers',
      yearLevel: 4,
      attemptId: attemptId,
      aiDiagnosisStreamFactory: streamFactory,
      aiDiagnosis: aiDiagnosis,
      reward: reward,
    ),
  );
}

void main() {
  testWidgets('result surfaces an analysis stream error and retries safely', (
    tester,
  ) async {
    var watchCount = 0;
    AiDiagnosisStreamFactory watchAttempt =
        (String attemptId, {String? topicId, String? subtopicId, int? yearLevel}) {
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
          recommendedLearningAction: 'repeat_subtopic',
          recommendationBasis: 'bkt_mastery',
        ),
      );
    };

    await tester.pumpWidget(
      _resultPage(
        isBahasaMelayu: false,
        streamFactory: watchAttempt,
        attemptId: 'attempt_retry',
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
      _resultPage(
        isBahasaMelayu: true,
        attemptId: 'attempt_retry_bm',
        streamFactory:
            (String attemptId,
                {String? topicId,
                String? subtopicId,
                int? yearLevel}) =>
                Stream<AiDiagnosis?>.error(StateError('hidden diagnostic')),
      ),
    );
    await tester.pump();

    expect(find.text('Status analisis tidak tersedia'), findsOneWidget);
    expect(find.text('Cuba semula analisis'), findsOneWidget);
    expect(find.textContaining('hidden diagnostic'), findsNothing);
  });

  testWidgets(
    'processing keeps the score immediate and disables next practice',
    (tester) async {
      await tester.pumpWidget(
        _resultPage(
          isBahasaMelayu: false,
          streamFactory: null,
          aiDiagnosis: const AiDiagnosis(
            attemptId: 'attempt_001',
            studentId: 'student_a',
            sourceAttemptSequence: 1,
            analysisState: 'processing',
            displayCode: 'analysis_pending',
          ),
          reward: const QuizReward(
            score: 20,
            earnedCrystals: 10,
            previousMastery: 'New',
            newMastery: 'Building',
            encouragement: 'Keep going.',
          ),
        ),
      );

      expect(find.text('20%'), findsOneWidget);
      expect(find.text('Learning analysis'), findsOneWidget);
      expect(
        find.textContaining('Preparing your next practice'),
        findsWidgets,
      );
      final cta = tester.widget<FilledButton>(
        find.ancestor(
          of: find.text('Preparing your next practice…').last,
          matching: find.byWidgetPredicate(
            (widget) => widget is FilledButton,
          ),
        ),
      );
      expect(cta.onPressed, isNull);
      expect(find.text('Back to Forge'), findsOneWidget);
    },
  );

  testWidgets('result labels controlled demonstration model evidence safely', (
    tester,
  ) async {
    Widget controlledResult({required bool isBahasaMelayu}) {
      return _resultPage(
        isBahasaMelayu: isBahasaMelayu,
        streamFactory: null,
        aiDiagnosis: const AiDiagnosis(
          attemptId: 'attempt_002',
          studentId: 'student_a',
          sourceAttemptSequence: 2,
          analysisState: 'completed',
          displayCode: 'analysis_completed',
          modelEvidenceState: 'controlled_demonstration',
          recommendedLearningAction: 'repeat_subtopic',
          recommendationBasis: 'bkt_mastery',
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
