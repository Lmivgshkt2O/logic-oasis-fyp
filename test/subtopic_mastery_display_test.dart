import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/formula_forge/subtopic_page.dart';
import 'package:logic_oasis/shared/models/trusted_subtopic_progress.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

void main() {
  late AppState state;

  setUp(() {
    state = AppState();
  });

  dynamic currentTopic() => state.topics.firstWhere(
    (item) => item.id == 'whole_numbers_y4',
  );

  TrustedSubtopicProgress record(
    String subtopicId, {
    bool completed = false,
    bool accessUnlocked = true,
    double? masteryProbability,
    String? recommendationBasis,
    String? projectionStatus,
    double bestCorrectRate = 0,
  }) {
    return TrustedSubtopicProgress(
      studentId: AppState.demoStudentId,
      topicId: 'whole_numbers_y4',
      subtopicId: subtopicId,
      yearLevel: 4,
      completed: completed,
      masteryLevel: completed ? 'Strong' : 'New',
      bestCorrectRate: bestCorrectRate,
      attempted: true,
      accessUnlocked: accessUnlocked,
      masteryProbability: masteryProbability,
      recommendationBasis: recommendationBasis,
      projectionStatus: projectionStatus,
    );
  }

  Future<void> pumpSubtopicPage(WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(home: SubtopicPage(state: state, topic: currentTopic())),
    );
    await tester.pumpAndSettle();
  }

  testWidgets(
    'a 0% attempted first subtopic unlocks the next card without completing it',
    (tester) async {
      state.applyTrustedSubtopicProgress([
        record(
          'read_write_numbers',
          bestCorrectRate: 0,
          recommendationBasis: 'provisional_pending_ai',
          projectionStatus: 'finalized_pending_ai',
        ),
      ], replaceAll: true);
      final topic = currentTopic();
      final subtopics = state.subtopicsForTopic(topic);

      await pumpSubtopicPage(tester);

      expect(find.text('0 of 5 subtopics completed'), findsOneWidget);
      expect(find.text('Preparing mastery…'), findsOneWidget);
      expect(subtopics.first.isComplete, isFalse);
      expect(subtopics.first.accessUnlocked, isTrue);
      expect(state.isSubtopicUnlocked(topic, subtopics[1]), isTrue);
    },
  );

  testWidgets('BKT probability renders as mastery without reusing correct rate',
      (tester) async {
    state.applyTrustedSubtopicProgress([
      record(
        'read_write_numbers',
        masteryProbability: 0.43,
        recommendationBasis: 'bkt_mastery',
        projectionStatus: 'ai_enriched',
        bestCorrectRate: 0.9,
      ),
    ], replaceAll: true);

    await pumpSubtopicPage(tester);

    expect(find.text('Mastery 43%'), findsOneWidget);
    expect(find.text('Still learning'), findsOneWidget);
    expect(find.textContaining('90%'), findsNothing);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Semantics &&
            widget.properties.label == 'Mastery 43%, Still learning',
      ),
      findsOneWidget,
    );
  });

  testWidgets('pending analysis shows no invented percentage', (tester) async {
    state.applyTrustedSubtopicProgress([
      record(
        'read_write_numbers',
        recommendationBasis: 'provisional_pending_ai',
        projectionStatus: 'finalized_pending_ai',
      ),
    ], replaceAll: true);

    await pumpSubtopicPage(tester);

    expect(find.text('Preparing mastery…'), findsOneWidget);
    expect(find.textContaining('Mastery'), findsNothing);
  });

  testWidgets('fallback is labelled as quiz progress, not BKT mastery',
      (tester) async {
    state.applyTrustedSubtopicProgress([
      record(
        'read_write_numbers',
        bestCorrectRate: 0.6,
        recommendationBasis: 'correct_rate_fallback',
        projectionStatus: 'ai_enriched',
      ),
    ], replaceAll: true);

    await pumpSubtopicPage(tester);

    expect(find.text('Quiz progress 60%'), findsOneWidget);
    expect(find.textContaining('Mastery'), findsNothing);
  });

  testWidgets('topic progress counts completed subtopics, not mastery',
      (tester) async {
    state.applyTrustedSubtopicProgress([
      record(
        'read_write_numbers',
        completed: true,
        masteryProbability: 0.9,
        recommendationBasis: 'bkt_mastery',
        projectionStatus: 'ai_enriched',
      ),
      record(
        'place_digit_value',
        masteryProbability: 0.4,
        recommendationBasis: 'bkt_mastery',
        projectionStatus: 'ai_enriched',
      ),
      record(
        'compare_order_numbers',
        masteryProbability: 0.5,
        recommendationBasis: 'bkt_mastery',
        projectionStatus: 'ai_enriched',
      ),
      record(
        'odd_even_numbers',
        masteryProbability: 0.6,
        recommendationBasis: 'bkt_mastery',
        projectionStatus: 'ai_enriched',
      ),
      record(
        'number_patterns',
        masteryProbability: 0.7,
        recommendationBasis: 'bkt_mastery',
        projectionStatus: 'ai_enriched',
      ),
    ], replaceAll: true);

    await pumpSubtopicPage(tester);

    expect(find.text('1 of 5 subtopics completed'), findsOneWidget);
    expect(currentTopic().progress, closeTo(0.2, 0.0001));
    expect(find.text('Ready to move on'), findsOneWidget);
  });

  testWidgets('no difficulty labels appear on subtopic cards', (tester) async {
    await pumpSubtopicPage(tester);

    expect(find.textContaining('Easy'), findsNothing);
    expect(find.textContaining('Moderate'), findsNothing);
    expect(find.textContaining('Hard'), findsNothing);
  });

  testWidgets('Bahasa Melayu mastery copy renders without overflow',
      (tester) async {
    state.language = 'Bahasa Melayu';
    state.applyTrustedSubtopicProgress([
      record(
        'read_write_numbers',
        masteryProbability: 0.43,
        recommendationBasis: 'bkt_mastery',
        projectionStatus: 'ai_enriched',
      ),
    ], replaceAll: true);

    await pumpSubtopicPage(tester);

    expect(find.text('Penguasaan 43%'), findsOneWidget);
    expect(find.text('Masih belajar'), findsOneWidget);
  });
}
