import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_state.dart';
import 'package:logic_oasis/shared/models/forum_participation_summary.dart';
import 'package:logic_oasis/shared/models/linked_child_context.dart';
import 'package:logic_oasis/shared/models/parent_dashboard_snapshot.dart';
import 'package:logic_oasis/shared/models/parent_practice_summary.dart';
import 'package:logic_oasis/shared/models/trusted_subtopic_progress.dart';
import 'package:logic_oasis/shared/services/parent_link_context_service.dart';

const childA = LinkedChildContext(
  studentId: 'student_a',
  displayName: 'Aiman',
  yearLevel: 4,
);
const childB = LinkedChildContext(
  studentId: 'student_b',
  displayName: 'Bela',
  yearLevel: 5,
);

class _Gateway implements ParentLinkedChildrenGateway {
  _Gateway(this.result);

  Future<List<LinkedChildContext>> Function() result;

  @override
  Future<List<LinkedChildContext>> loadLinkedChildren() => result();
}

class _ControllableLoader {
  final List<Completer<ParentDashboardSnapshot>> pending = [];
  int calls = 0;

  Future<ParentDashboardSnapshot> call(LinkedChildContext child) {
    final completer = Completer<ParentDashboardSnapshot>();
    pending.add(completer);
    calls++;
    return completer.future;
  }
}

Future<ParentDashboardLoader> Function() loaderFactory(
  _ControllableLoader loader,
) =>
    () async => loader.call;

TrustedSubtopicProgress masteryRecord() {
  return TrustedSubtopicProgress(
    studentId: 'student_a',
    topicId: 'whole_numbers_y4',
    subtopicId: 'read_write_numbers',
    yearLevel: 4,
    completed: true,
    masteryLevel: 'Moderate',
    bestCorrectRate: 0.6,
    attempted: true,
    accessUnlocked: true,
    masteryProbability: 0.55,
    evidenceLevel: 'established',
    observationCount: 2,
    updatedAt: DateTime.utc(2026, 8, 1, 8),
  );
}

ParentPracticeSummary practiceSummary() {
  return ParentPracticeSummary(
    schemaVersion: parentPracticeSummarySchemaVersion,
    studentId: 'student_a',
    timezone: parentPracticeTimezone,
    weekStart: DateTime.utc(2026, 8, 9, 16),
    dailyCompletionCounts: const [1, 0, 0, 0, 2, 0, 0],
    completedPracticeCount: 3,
    activeDayCount: 2,
    updatedAt: DateTime.utc(2026, 8, 11, 4),
  );
}

ForumParticipationSummary mutualAidSummary() {
  return const ForumParticipationSummary(
    studentId: 'student_a',
    questionsPostedCount: 1,
    answersSubmittedCount: 2,
    acceptedAnswersCount: 1,
    helpfulReceivedCount: 0,
  );
}

ParentDashboardSnapshot fullSnapshot() {
  return ParentDashboardSnapshot(
    mastery: [masteryRecord()],
    practiceSummary: practiceSummary(),
    forumParticipationSummary: mutualAidSummary(),
  );
}

ParentDashboardSnapshot partialSnapshot() {
  return ParentDashboardSnapshot(mastery: [masteryRecord()]);
}

Future<void> settle() => pumpEventQueue();

void main() {
  group('ParentDashboardState phases', () {
    test('initial links loading then no active child are distinct', () async {
      final state = ParentDashboardState(
        gateway: _Gateway(() async => const []),
        loaderFactory: () async =>
            (_) async => fullSnapshot(),
      );

      expect(state.phase, ParentDashboardPhase.loadingLinks);
      await state.loadLinkedChildren();

      expect(state.phase, ParentDashboardPhase.noActiveChild);
      expect(
        state.message,
        'No active linked learner is available for this account.',
      );
      expect(state.selectedChild, isNull);
      expect(state.snapshot, isNull);
    });

    test(
      'link error is distinct and retry reloads links then the child',
      () async {
        var fail = true;
        final gateway = _Gateway(() async {
          if (fail) {
            throw const ParentLinkContextException('Link context failed.');
          }
          return const [childA];
        });
        final loader = _ControllableLoader();
        final state = ParentDashboardState(
          gateway: gateway,
          loaderFactory: loaderFactory(loader),
        );

        await state.loadLinkedChildren();
        expect(state.phase, ParentDashboardPhase.linkError);
        expect(state.message, 'Link context failed.');

        fail = false;
        unawaited(state.loadLinkedChildren());
        expect(state.phase, ParentDashboardPhase.loadingLinks);
        await settle();
        expect(state.phase, ParentDashboardPhase.loadingChild);
        expect(loader.calls, 1);

        loader.pending[0].complete(fullSnapshot());
        await settle();
        expect(state.phase, ParentDashboardPhase.readyAll);
      },
    );

    test(
      'full evidence is ready-all and partial evidence is ready-partial',
      () async {
        final all = ParentDashboardState(
          gateway: _Gateway(() async => const [childA]),
          loaderFactory: () async =>
              (_) async => fullSnapshot(),
        );
        await all.loadLinkedChildren();
        expect(all.phase, ParentDashboardPhase.readyAll);

        final partial = ParentDashboardState(
          gateway: _Gateway(() async => const [childA]),
          loaderFactory: () async =>
              (_) async => partialSnapshot(),
        );
        await partial.loadLinkedChildren();
        expect(partial.phase, ParentDashboardPhase.readyPartial);
      },
    );
  });

  group('ParentDashboardState races', () {
    test(
      'disposing while a child load is pending ignores the late completion',
      () async {
        final loader = _ControllableLoader();
        final state = ParentDashboardState(
          gateway: _Gateway(() async => const [childA]),
          loaderFactory: loaderFactory(loader),
        );
        final notifications = <ParentDashboardPhase>[];
        state.addListener(() => notifications.add(state.phase));

        unawaited(state.loadLinkedChildren());
        await settle();
        expect(state.phase, ParentDashboardPhase.loadingChild);

        state.dispose();
        loader.pending.single.complete(fullSnapshot());
        await settle();

        // Completing after dispose must neither notify nor mutate state.
        expect(notifications, isNot(contains(ParentDashboardPhase.readyAll)));
      },
    );

    test(
      'switching children clears A and late A results cannot overwrite B',
      () async {
        final loader = _ControllableLoader();
        final state = ParentDashboardState(
          gateway: _Gateway(() async => const [childA, childB]),
          loaderFactory: loaderFactory(loader),
        );

        unawaited(state.loadLinkedChildren());
        await settle();
        expect(state.phase, ParentDashboardPhase.loadingChild);

        unawaited(state.selectChild(childB));
        expect(state.selectedChild?.studentId, 'student_b');
        expect(state.snapshot, isNull);
        expect(state.phase, ParentDashboardPhase.loadingChild);

        await settle();
        loader.pending[1].complete(fullSnapshot());
        await settle();
        expect(state.phase, ParentDashboardPhase.readyAll);
        final committed = state.snapshot;

        loader.pending[0].complete(partialSnapshot());
        await settle();
        expect(state.selectedChild?.studentId, 'student_b');
        expect(state.snapshot, same(committed));
        expect(state.phase, ParentDashboardPhase.readyAll);
      },
    );

    test(
      'out-of-order same-child refreshes keep the newest generation',
      () async {
        final loader = _ControllableLoader();
        final state = ParentDashboardState(
          gateway: _Gateway(() async => const [childA]),
          loaderFactory: loaderFactory(loader),
        );

        unawaited(state.loadLinkedChildren());
        await settle();
        loader.pending[0].complete(fullSnapshot());
        await settle();
        expect(state.phase, ParentDashboardPhase.readyAll);

        unawaited(state.retryCurrentChild());
        unawaited(state.retryCurrentChild());
        await settle();
        // The older (gen2) response completes first and must be ignored because
        // the newest request generation is still in flight.
        loader.pending[1].complete(partialSnapshot());
        await settle();
        expect(state.phase, ParentDashboardPhase.loadingChild);
        expect(state.snapshot, isNull);

        loader.pending[2].complete(fullSnapshot());
        await settle();
        expect(state.phase, ParentDashboardPhase.readyAll);
        expect(state.snapshot?.mastery, hasLength(1));
      },
    );

    test('child error is distinct and whole-context retry targets the current '
        'child', () async {
      final loader = _ControllableLoader();
      final state = ParentDashboardState(
        gateway: _Gateway(() async => const [childA]),
        loaderFactory: loaderFactory(loader),
      );

      unawaited(state.loadLinkedChildren());
      await settle();
      loader.pending[0].completeError(StateError('boom'));
      await settle();
      expect(state.phase, ParentDashboardPhase.childError);
      expect(
        state.message,
        'Safe learner updates are temporarily unavailable.',
      );
      expect(state.snapshot, isNull);

      unawaited(state.retryCurrentChild());
      await settle();
      expect(state.phase, ParentDashboardPhase.loadingChild);
      expect(loader.calls, 2);
      loader.pending[1].complete(fullSnapshot());
      await settle();
      expect(state.phase, ParentDashboardPhase.readyAll);
    });
  });

  group('ParentDashboardState revocation and card retry', () {
    test('revocation clears the whole child view', () async {
      final loader = _ControllableLoader();
      final state = ParentDashboardState(
        gateway: _Gateway(() async => const [childA]),
        loaderFactory: loaderFactory(loader),
      );

      unawaited(state.loadLinkedChildren());
      await settle();
      loader.pending[0].completeError(
        const ParentDashboardAuthException('revoked'),
      );
      await settle();

      expect(state.phase, ParentDashboardPhase.childError);
      expect(
        state.message,
        'This learner link is no longer active. Please reconnect.',
      );
      expect(state.snapshot, isNull);
      expect(state.retryingCard, isNull);
    });

    test(
      'a linked-child refresh that removes the child clears content',
      () async {
        var children = [childA];
        final gateway = _Gateway(() async => List.of(children));
        final loader = _ControllableLoader();
        final state = ParentDashboardState(
          gateway: gateway,
          loaderFactory: loaderFactory(loader),
        );

        unawaited(state.loadLinkedChildren());
        await settle();
        loader.pending[0].complete(fullSnapshot());
        await settle();
        expect(state.phase, ParentDashboardPhase.readyAll);

        children = [];
        await state.loadLinkedChildren();
        expect(state.phase, ParentDashboardPhase.noActiveChild);
        expect(state.selectedChild, isNull);
        expect(state.snapshot, isNull);
      },
    );

    test(
      'card retry keeps other cards and commits when the card succeeds',
      () async {
        final loader = _ControllableLoader();
        final state = ParentDashboardState(
          gateway: _Gateway(() async => const [childA]),
          loaderFactory: loaderFactory(loader),
        );

        unawaited(state.loadLinkedChildren());
        await settle();
        loader.pending[0].complete(partialSnapshot());
        await settle();
        expect(state.phase, ParentDashboardPhase.readyPartial);

        unawaited(state.retryCard(ParentCardKind.practice));
        expect(state.phase, ParentDashboardPhase.retryingCard);
        expect(state.retryingCard, ParentCardKind.practice);
        expect(state.snapshot, isNotNull);

        await settle();
        loader.pending[1].complete(fullSnapshot());
        await settle();
        expect(state.phase, ParentDashboardPhase.readyAll);
        expect(state.retryingCard, isNull);
      },
    );

    test(
      'card retry that stays unavailable returns to ready-partial',
      () async {
        final loader = _ControllableLoader();
        final state = ParentDashboardState(
          gateway: _Gateway(() async => const [childA]),
          loaderFactory: loaderFactory(loader),
        );

        unawaited(state.loadLinkedChildren());
        await settle();
        loader.pending[0].complete(partialSnapshot());
        await settle();

        unawaited(state.retryCard(ParentCardKind.mutualAid));
        await settle();
        loader.pending[1].complete(partialSnapshot());
        await settle();

        expect(state.phase, ParentDashboardPhase.readyPartial);
        expect(state.retryingCard, isNull);
        expect(state.snapshot, isNotNull);
      },
    );
  });
}
