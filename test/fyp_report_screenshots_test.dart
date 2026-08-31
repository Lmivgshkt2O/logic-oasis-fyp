// FYP report screenshot captures.
//
// Copy this file into the project's `test/` folder, then run:
//   flutter test test/fyp_report_screenshots_test.dart
//
// PNGs are written to the folder set in `_outDir` (default: ../report_shots).
// Change `_outDir` if you want them somewhere else.
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/app/logic_oasis_shell.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/formula_forge/subtopic_page.dart';
import 'package:logic_oasis/features/quiz/quiz_page.dart';
import 'package:logic_oasis/features/quiz/result_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/adaptive_assignment.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/question_bank.dart';
import 'package:logic_oasis/shared/models/question_response.dart';
import 'package:logic_oasis/shared/models/quiz_completion.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/quiz_review_item.dart';
import 'package:logic_oasis/shared/models/quiz_session.dart';
import 'package:logic_oasis/shared/models/trusted_subtopic_progress.dart';
import 'package:logic_oasis/shared/services/quiz_session_service.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/state/app_state_scope.dart';

final String _outDir = '../report_shots';

Future<void> _capture(
  WidgetTester tester,
  Widget app,
  String fileName,
) async {
  Directory(_outDir).createSync(recursive: true);
  await tester.binding.setSurfaceSize(const Size(430, 2000));
  addTearDown(() => tester.binding.setSurfaceSize(null));
  await tester.pumpWidget(
    RepaintBoundary(
      key: const Key('capture-boundary'),
      child: app,
    ),
  );
  // Allow the page to settle; timed pumps avoid hanging on animations.
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
  await tester.pump(const Duration(milliseconds: 400));

  final boundary = tester.renderObject<RenderRepaintBoundary>(
    find.byKey(const Key('capture-boundary')),
  );
  final image = await boundary.toImage(pixelRatio: 2.0);
  final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
  File('$_outDir/$fileName').writeAsBytesSync(byteData!.buffer.asUint8List());
}

MaterialApp _wrap(Widget home) {
  return MaterialApp(
    theme: LogicOasisTheme.light(),
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    home: home,
  );
}

// ---- Quiz setup (mirrors quiz_feedback_guidance_test.dart) ----
const _quizSession = QuizSession(
  id: 'session-report',
  attemptId: 'attempt-report',
  assignmentId: 'assignment-report',
  assignmentSource: 'cold_start_easy',
  bankId: 'bank-report',
  topicId: 'whole_numbers',
  subtopicId: 'read_write_numbers',
  yearLevel: 4,
  difficultyLevel: 'Easy',
  contentVersion: 'test',
  questionIds: <String>['question-report'],
  questions: <QuizQuestion>[
    QuizQuestion(
      id: 'question-report',
      bankId: 'bank-report',
      topicId: 'whole_numbers',
      subtopicId: 'read_write_numbers',
      skillId: 'read_write_numbers',
      yearLevel: 4,
      difficultyLevel: 'Easy',
      estimatedDifficulty: .2,
      contentVersion: 'test',
      language: 'en',
      createdAt: '2026-07-30',
      question: 'Which numeral is shown?',
      questionBm: 'Angka manakah ditunjukkan?',
      options: <String>['2 004', '20 004'],
      optionsBm: <String>['2 004', '20 004'],
      sourceReference: 'Test',
    ),
  ],
);

class _WrongAnswerService implements QuizSessionGateway {
  @override
  Future<QuizSession> startSession({
    required String topicId,
    required String subtopicId,
    required int yearLevel,
  }) =>
      throw UnsupportedError('The quiz page receives an existing session.');

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
      isCorrect: false,
      feedbackHint: 'Twenty thousand has 20 groups of one thousand.',
      feedbackHintBm: 'Dua puluh ribu mempunyai 20 kumpulan seribu.',
      feedbackExample: 'In 43 007, the 43 shows 43 thousands.',
      feedbackExampleBm: 'Dalam 43 007, angka 43 menunjukkan 43 ribu.',
      reviewFocus: 'Check how many thousands are named before the ones.',
      reviewFocusBm: 'Semak berapa ribu yang disebut sebelum sa.',
      validationStatus: 'validated',
    );
  }

  @override
  Future<QuizCompletion> finalizeSession(String sessionId) =>
      throw UnsupportedError('Not needed.');
}

TrustedSubtopicProgress _mastery(
  String subtopicId, {
  required bool completed,
  double? probability,
  String basis = 'bkt_mastery',
}) {
  return TrustedSubtopicProgress(
    studentId: AppState.demoStudentId,
    topicId: 'whole_numbers_y4',
    subtopicId: subtopicId,
    yearLevel: 4,
    completed: completed,
    masteryLevel: completed ? 'Strong' : 'New',
    bestCorrectRate: completed ? 0.9 : 0.43,
    attempted: true,
    accessUnlocked: true,
    masteryProbability: probability,
    recommendationBasis: basis,
    projectionStatus: 'ai_enriched',
  );
}

void main() {
  testWidgets('capture Formula Forge and Home within the 4-tab shell', (
    tester,
  ) async {
    // Forge
    var state = AppState()..changeTab(1);
    await _capture(
      tester,
      _wrapShell(state),
      'fig4_01_formula_forge.png',
    );
    // Home
    state = AppState()..changeTab(0);
    await _capture(
      tester,
      _wrapShell(state),
      'fig4_02_home.png',
    );
  });

  testWidgets('capture subtopic mastery cards (Ready to move on)', (
    tester,
  ) async {
    final state = AppState();
    state.applyTrustedSubtopicProgress([
      _mastery('read_write_numbers', completed: true, probability: 0.9),
      _mastery('place_digit_value', completed: false, probability: 0.4),
      _mastery(
        'compare_order_numbers',
        completed: false,
        probability: 0.5,
      ),
      _mastery('odd_even_numbers', completed: false, probability: 0.6),
      _mastery('number_patterns', completed: false, probability: 0.7),
    ], replaceAll: true);
    final topic = state.topics.firstWhere(
      (item) => item.id == 'whole_numbers_y4',
    );
    await _capture(
      tester,
      _wrap(SubtopicPage(state: state, topic: topic)),
      'fig4_03_subtopic_mastery.png',
    );
  });

  testWidgets('capture quiz wrong-answer guidance', (tester) async {
    await _capture(
      tester,
      _wrap(QuizPage(
        title: 'Whole Numbers',
        isBahasaMelayu: false,
        session: _quizSession,
        sessionService: _WrongAnswerService(),
      )),
      'fig4_04_quiz_guidance.png',
    );
    // show the hint by selecting a wrong option
    await tester.tap(find.text('2 004'));
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
    final boundary = tester.renderObject<RenderRepaintBoundary>(
      find.byKey(const Key('capture-boundary')),
    );
    final image = await boundary.toImage(pixelRatio: 2.0);
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
    File('$_outDir/fig4_04_quiz_guidance.png')
        .writeAsBytesSync(byteData!.buffer.asUint8List());
  });

  testWidgets('capture result review cards and next action', (tester) async {
    const completion = QuizCompletion(
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
    const assignment = AdaptiveAssignment(
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
    const diagnosis = AiDiagnosis(
      attemptId: 'attempt-1',
      studentId: 'student',
      sourceAttemptSequence: 1,
      analysisState: 'completed',
      displayCode: 'analysis_completed',
      assignment: assignment,
      recommendedLearningAction: 'repeat_subtopic',
      recommendationBasis: 'bkt_mastery',
    );
    await _capture(
      tester,
      _wrap(ResultPage(
        completion: completion,
        topicArea: 'Whole Numbers',
        isBahasaMelayu: false,
        topicId: 'whole_numbers_y4',
        subtopicId: 'read_write_numbers',
        yearLevel: 4,
        aiDiagnosis: diagnosis,
      )),
      'fig4_05_result.png',
    );
  });
}

Widget _wrapShell(AppState state) {
  return AppStateScope(
    state: state,
    child: MaterialApp(
      theme: LogicOasisTheme.light(),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      home: LogicOasisShell(onLogout: () {}),
    ),
  );
}
