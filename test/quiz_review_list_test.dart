import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/quiz/result_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/adaptive_assignment.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/question_bank.dart';
import 'package:logic_oasis/shared/models/quiz_completion.dart';
import 'package:logic_oasis/shared/models/quiz_review_item.dart';

const _twoItemCompletion = QuizCompletion(
  correctCount: 3,
  totalQuestions: 5,
  score: 60,
  timeTakenSeconds: 3,
  reviewItems: <QuizReviewItem>[
    QuizReviewItem(
      questionId: 'question-2',
      sequenceIndex: 1,
      questionText: 'Which numeral shows twenty thousand four?',
      questionTextBm: 'Angka manakah menunjukkan dua puluh ribu empat?',
      questionType: 'Read a number',
      questionTypeBm: 'Baca nombor',
      reviewFocus: 'Read the thousands group first.',
      reviewFocusBm: 'Baca kumpulan ribu dahulu.',
    ),
    QuizReviewItem(
      questionId: 'question-5',
      sequenceIndex: 4,
      questionText: 'Which number is even?',
      questionTextBm: 'Nombor manakah genap?',
      questionType: 'Odd or even',
      questionTypeBm: 'Ganjil atau genap',
      reviewFocus: 'Look at the ones digit.',
      reviewFocusBm: 'Lihat digit sa.',
    ),
  ],
);

const _perfectCompletion = QuizCompletion(
  correctCount: 5,
  totalQuestions: 5,
  score: 100,
  timeTakenSeconds: 3,
);

Widget _resultPage({
  required QuizCompletion completion,
  required bool isBahasaMelayu,
  AiDiagnosis? aiDiagnosis,
}) {
  return MaterialApp(
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    locale: isBahasaMelayu ? const Locale('ms') : null,
    home: ResultPage(
      completion: completion,
      topicArea: isBahasaMelayu ? 'Nombor Bulat' : 'Whole Numbers',
      isBahasaMelayu: isBahasaMelayu,
      topicId: 'whole_numbers_y4',
      subtopicId: 'read_write_numbers',
      yearLevel: 4,
      aiDiagnosis: aiDiagnosis,
    ),
  );
}

AiDiagnosis _diagnosis({
  required String action,
  String basis = 'bkt_mastery',
  String? analysisState = 'completed',
  AdaptiveAssignment? assignment,
  String? targetTopicId,
  String? targetSubtopicId,
}) {
  return AiDiagnosis(
    attemptId: 'attempt-1',
    studentId: 'student',
    sourceAttemptSequence: 1,
    analysisState: analysisState!,
    displayCode: 'analysis_completed',
    assignment: assignment,
    recommendedLearningAction: action,
    recommendationBasis: basis,
    recommendationTargetTopicId: targetTopicId,
    recommendationTargetSubtopicId: targetSubtopicId,
  );
}

void main() {
  testWidgets('two missed questions render two review cards without a count', (
    tester,
  ) async {
    await tester.pumpWidget(
      _resultPage(completion: _twoItemCompletion, isBahasaMelayu: false),
    );

    expect(find.text('Review these first'), findsOneWidget);
    expect(find.text('Which numeral shows twenty thousand four?'), findsOneWidget);
    expect(find.text('Read a number'), findsOneWidget);
    expect(find.text('Read the thousands group first.'), findsOneWidget);
    expect(find.text('Which number is even?'), findsOneWidget);
    expect(find.text('Odd or even'), findsOneWidget);
    expect(find.text('Look at the ones digit.'), findsOneWidget);
    expect(find.text('2 to review'), findsNothing);
    expect(find.text('1 to review'), findsNothing);
  });

  testWidgets('Bahasa Melayu review cards use the matching fields', (
    tester,
  ) async {
    await tester.pumpWidget(
      _resultPage(completion: _twoItemCompletion, isBahasaMelayu: true),
    );

    expect(find.text('Semak dahulu'), findsOneWidget);
    expect(
      find.text('Angka manakah menunjukkan dua puluh ribu empat?'),
      findsOneWidget,
    );
    expect(find.text('Baca nombor'), findsOneWidget);
    expect(find.text('Baca kumpulan ribu dahulu.'), findsOneWidget);
    expect(find.text('Nombor manakah genap?'), findsOneWidget);
    expect(find.text('Ganjil atau genap'), findsOneWidget);
    expect(find.text('Lihat digit sa.'), findsOneWidget);
  });

  testWidgets('a perfect score hides the review list and shows success', (
    tester,
  ) async {
    await tester.pumpWidget(
      _resultPage(completion: _perfectCompletion, isBahasaMelayu: false),
    );

    expect(find.text('Perfect score! Nothing to review.'), findsOneWidget);
    expect(find.text('Which numeral shows twenty thousand four?'), findsNothing);
  });

  testWidgets('next assigned difficulty appears only in the result panel', (
    tester,
  ) async {
    final assignment = const AdaptiveAssignment(
      id: 'assignment',
      subtopicId: 'read_write_numbers',
      bankId: 'bank-moderate',
      difficulty: QuestionDifficulty.moderate,
      policyVersion: 'adaptive-policy-v1',
      reasonCode: 'stay_target_zone',
      reasonText: 'Keep practising at this level.',
      evidenceCount: 5,
      usedBktFallback: false,
      masteryProbability: 0.5,
    );
    await tester.pumpWidget(
      _resultPage(
        completion: _twoItemCompletion,
        isBahasaMelayu: false,
        aiDiagnosis: _diagnosis(
          action: 'repeat_subtopic',
          assignment: assignment,
        ),
      ),
    );

    expect(find.text('Next: Moderate practice'), findsOneWidget);
    expect(find.text('Practise Again'), findsOneWidget);
  });

  testWidgets('fallback recommendation is visibly labelled', (tester) async {
    await tester.pumpWidget(
      _resultPage(
        completion: _twoItemCompletion,
        isBahasaMelayu: false,
        aiDiagnosis: _diagnosis(
          action: 'repeat_subtopic',
          basis: 'correct_rate_fallback',
          analysisState: 'fallback',
        ),
      ),
    );

    expect(find.text('Based on your quiz progress'), findsOneWidget);
    expect(find.text('Next: Easy practice'), findsOneWidget);
    expect(find.text('Practise Again'), findsOneWidget);
  });
}
