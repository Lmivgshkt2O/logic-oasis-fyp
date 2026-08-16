import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_state.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_time.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_view_models.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/linked_child_context.dart';
import 'package:logic_oasis/shared/models/parent_dashboard_snapshot.dart';
import 'package:logic_oasis/shared/repositories/learning_repository.dart';
import 'package:logic_oasis/shared/services/parent_firebase_session.dart';
import 'package:logic_oasis/shared/services/parent_link_context_service.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';

class ParentDashboardPage extends StatefulWidget {
  const ParentDashboardPage({
    super.key,
    required this.state,
    this.linkedChildrenGateway,
    this.dashboardLoader,
    this.clock,
  });

  final AppState state;
  final ParentLinkedChildrenGateway? linkedChildrenGateway;
  final ParentDashboardLoader? dashboardLoader;

  /// Injectable wall-clock source so the deterministic weekly derivation is
  /// testable. Defaults to the real clock.
  final DateTime Function()? clock;

  @override
  State<ParentDashboardPage> createState() => _ParentDashboardPageState();
}

class _ParentDashboardPageState extends State<ParentDashboardPage> {
  late final ParentDashboardState _dashboardState;
  late final Listenable _listenable;

  @override
  void initState() {
    super.initState();
    _dashboardState = ParentDashboardState(
      gateway: widget.linkedChildrenGateway ?? ParentLinkedChildrenService(),
      loaderFactory: _loaderFactory,
    );
    _listenable = Listenable.merge([widget.state, _dashboardState]);
    _dashboardState.loadLinkedChildren();
  }

  @override
  void dispose() {
    _dashboardState.dispose();
    super.dispose();
  }

  Future<ParentDashboardLoader> _loaderFactory() async {
    final provided = widget.dashboardLoader;
    if (provided != null) return provided;
    // Use the named parent Firebase app so Rules evaluate the parent identity,
    // while the student stays signed in through the default app.
    final repository = LearningRepository(
      firestore: await ParentFirebaseSession.firestore(),
    );
    return (LinkedChildContext selectedChild) =>
        repository.fetchParentDashboardSnapshot(
          studentId: selectedChild.studentId,
          yearLevel: selectedChild.yearLevel,
          topics: widget.state.topics,
        );
  }

  void _selectChild(LinkedChildContext? child) {
    if (child == null) return;
    _dashboardState.selectChild(child);
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _listenable,
      builder: (context, _) => _ParentDashboardContent(
        state: widget.state,
        dashboard: _dashboardState,
        now: (widget.clock?.call() ?? DateTime.now()),
        onChildSelected: _selectChild,
      ),
    );
  }
}

class _ParentDashboardContent extends StatelessWidget {
  const _ParentDashboardContent({
    required this.state,
    required this.dashboard,
    required this.now,
    required this.onChildSelected,
  });

  final AppState state;
  final ParentDashboardState dashboard;
  final DateTime now;
  final ValueChanged<LinkedChildContext?> onChildSelected;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final selectedChild = dashboard.selectedChild;
    final phase = dashboard.phase;
    final snapshot = dashboard.snapshot;
    final viewModel =
        selectedChild != null && snapshot != null && dashboard.isReady
        ? deriveParentProgressMap(
            now: now,
            studentId: selectedChild.studentId,
            yearLevel: selectedChild.yearLevel,
            mastery: snapshot.mastery ?? const [],
            practice: snapshot.practiceSummary,
            mutualAid: snapshot.forumParticipationSummary,
            curriculum: state.topics,
          )
        : null;

    return LogicOasisScaffold(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      children: [
        Text(l10n.parentDashboard, style: theme.textTheme.headlineLarge),
        const SizedBox(height: 8),
        Text(
          selectedChild == null
              ? state.t(
                  'Sign in with a linked parent account to view safe learner updates.',
                  'Log masuk dengan akaun ibu bapa yang dipautkan untuk melihat kemas kini pembelajaran selamat.',
                )
              : l10n.parentDashboardCaption(selectedChild.displayName),
          style: theme.textTheme.bodyLarge,
        ),
        if (viewModel != null) ...[
          const SizedBox(height: 4),
          _ParentUpdatedLine(viewModel: viewModel, l10n: l10n),
        ],
        if (dashboard.children.length > 1) ...[
          const SizedBox(height: 14),
          DropdownButtonFormField<LinkedChildContext>(
            initialValue: selectedChild,
            decoration: const InputDecoration(labelText: 'Linked learner'),
            items: dashboard.children
                .map(
                  (child) => DropdownMenuItem(
                    value: child,
                    child: Text(
                      '${child.displayName} (Year ${child.yearLevel})',
                    ),
                  ),
                )
                .toList(growable: false),
            onChanged: onChildSelected,
          ),
        ],
        if (_showStatusBanner(phase)) ...[
          const SizedBox(height: 14),
          _ParentDashboardSafeStatusBanner(
            loading:
                phase == ParentDashboardPhase.loadingLinks ||
                phase == ParentDashboardPhase.loadingChild,
            text: _statusText(phase, dashboard.message),
            onRetry: switch (phase) {
              ParentDashboardPhase.linkError => dashboard.loadLinkedChildren,
              ParentDashboardPhase.childError => dashboard.retryCurrentChild,
              _ => null,
            },
          ),
        ],
        if (selectedChild != null &&
            dashboard.isReady &&
            viewModel != null) ...[
          const SizedBox(height: 18),
          _ParentProgressMap(
            state: state,
            dashboard: dashboard,
            viewModel: viewModel,
            snapshot: snapshot!,
          ),
        ],
      ],
    );
  }

  static bool _showStatusBanner(ParentDashboardPhase phase) =>
      phase == ParentDashboardPhase.loadingLinks ||
      phase == ParentDashboardPhase.loadingChild ||
      phase == ParentDashboardPhase.linkError ||
      phase == ParentDashboardPhase.childError ||
      phase == ParentDashboardPhase.noActiveChild;

  static String _statusText(ParentDashboardPhase phase, String? message) {
    if (phase == ParentDashboardPhase.loadingLinks) {
      return 'Loading linked learners…';
    }
    if (phase == ParentDashboardPhase.loadingChild) {
      return 'Loading linked learner updates…';
    }
    return message ?? '';
  }
}

class _ParentUpdatedLine extends StatelessWidget {
  const _ParentUpdatedLine({required this.viewModel, required this.l10n});

  final ParentProgressMapViewModel viewModel;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    final timestamp = _latestUsedTimestamp(viewModel);
    if (timestamp == null) return const SizedBox.shrink();
    return Text(
      l10n.parentDashboardUpdated(formatAiUpdatedAt(timestamp)),
      style: theme.textTheme.bodySmall?.copyWith(color: oasis.secondaryInk),
    );
  }

  static DateTime? _latestUsedTimestamp(ParentProgressMapViewModel viewModel) {
    DateTime? latest;
    void consider(DateTime? candidate) {
      if (candidate != null && (latest == null || candidate.isAfter(latest!))) {
        latest = candidate;
      }
    }

    consider(viewModel.understanding.focusUpdatedAt);
    consider(viewModel.practice.updatedAt);
    return latest;
  }
}

/// The approved Progress Map: glance, Understanding, Practice Effort, Mutual
/// Aid, and the matching conversation starter, in that semantic order.
class _ParentProgressMap extends StatelessWidget {
  const _ParentProgressMap({
    required this.state,
    required this.dashboard,
    required this.viewModel,
    required this.snapshot,
  });

  final AppState state;
  final ParentDashboardState dashboard;
  final ParentProgressMapViewModel viewModel;
  final ParentDashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final retrying = dashboard.retryingCard;
    final canRetry =
        dashboard.phase == ParentDashboardPhase.readyPartial ||
        dashboard.phase == ParentDashboardPhase.retryingCard;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _WeeklyGlanceCard(
          l10n: l10n,
          glance: viewModel.glance,
          focusTitle: _focusTitle(state, viewModel),
        ),
        const SizedBox(height: 16),
        _UnderstandingCard(
          l10n: l10n,
          state: state,
          card: viewModel.understanding,
          action: viewModel.action,
          unavailable: snapshot.mastery == null,
          retrying: retrying == ParentCardKind.understanding,
          canRetry: canRetry && snapshot.mastery == null,
          onRetry: () => dashboard.retryCard(ParentCardKind.understanding),
        ),
        const SizedBox(height: 16),
        _PracticeCard(
          l10n: l10n,
          card: viewModel.practice,
          retrying: retrying == ParentCardKind.practice,
          canRetry:
              canRetry &&
              viewModel.practice.status == ParentPracticeStatus.unavailable,
          onRetry: () => dashboard.retryCard(ParentCardKind.practice),
        ),
        const SizedBox(height: 16),
        _MutualAidCard(
          l10n: l10n,
          card: viewModel.mutualAid,
          retrying: retrying == ParentCardKind.mutualAid,
          canRetry:
              canRetry &&
              viewModel.mutualAid.status == ParentMutualAidStatus.unavailable,
          onRetry: () => dashboard.retryCard(ParentCardKind.mutualAid),
        ),
        if (viewModel.conversationStarter != null) ...[
          const SizedBox(height: 16),
          _ConversationStarterCard(
            l10n: l10n,
            starter: viewModel.conversationStarter!,
            focusTitle: _focusTitle(state, viewModel),
          ),
        ],
      ],
    );
  }

  static String _focusTitle(
    AppState state,
    ParentProgressMapViewModel viewModel,
  ) {
    return state.isBahasaMelayu
        ? viewModel.understanding.focusSubtopicTitleBm
        : viewModel.understanding.focusSubtopicTitle;
  }
}

class _WeeklyGlanceCard extends StatelessWidget {
  const _WeeklyGlanceCard({
    required this.l10n,
    required this.glance,
    required this.focusTitle,
  });

  final AppLocalizations l10n;
  final ParentWeeklyGlance glance;
  final String focusTitle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    final headline = _headline(l10n, glance.key);
    final supporting = _supporting(l10n, glance.key, focusTitle);
    return Semantics(
      container: true,
      header: true,
      label: 'This week at a glance',
      child: SoftCard(
        padding: const EdgeInsets.all(16),
        color: oasis.surface,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(headline, style: theme.textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(supporting, style: theme.textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }

  static String _headline(AppLocalizations l10n, String key) {
    return switch (key) {
      'glance_focus_practice_mutual_aid' => l10n.glanceFull,
      'glance_focus_practice' => l10n.glanceFocusPractice,
      'glance_focus_practice_no_mutual_aid_yet' =>
        l10n.glanceFocusPracticeNoMutualAidYet,
      'glance_focus_no_practice_yet_mutual_aid' =>
        l10n.glanceFocusNoPracticeYetMutualAid,
      'glance_focus_no_practice_yet' => l10n.glanceFocusNoPracticeYet,
      'glance_focus_no_practice_yet_no_mutual_aid_yet' =>
        l10n.glanceFocusNoPracticeYetNoMutualAidYet,
      'glance_focus_mutual_aid' => l10n.glanceFocusMutualAid,
      'glance_focus_no_mutual_aid_yet' => l10n.glanceFocusNoMutualAidYet,
      'glance_focus_only' => l10n.glanceFocusOnly,
      'glance_practice_recorded' => l10n.glancePracticeRecorded,
      'glance_no_practice_yet' => l10n.glanceNoPracticeYet,
      'glance_mutual_aid_recorded' => l10n.glanceMutualAidRecorded,
      'glance_no_mutual_aid_yet' => l10n.glanceNoMutualAidYet,
      'glance_no_data_yet' => l10n.glanceNoDataYet,
      _ => l10n.glanceNoDataYet,
    };
  }

  static String _supporting(
    AppLocalizations l10n,
    String key,
    String focusTitle,
  ) {
    return switch (key) {
      'glance_focus_practice_mutual_aid' => l10n.glanceFullSupport(focusTitle),
      'glance_focus_practice' => l10n.glanceFocusPracticeSupport(focusTitle),
      'glance_focus_practice_no_mutual_aid_yet' =>
        l10n.glanceFocusPracticeNoMutualAidYetSupport(focusTitle),
      'glance_focus_no_practice_yet_mutual_aid' =>
        l10n.glanceFocusNoPracticeYetMutualAidSupport(focusTitle),
      'glance_focus_no_practice_yet' => l10n.glanceFocusNoPracticeYetSupport(
        focusTitle,
      ),
      'glance_focus_no_practice_yet_no_mutual_aid_yet' =>
        l10n.glanceFocusNoPracticeYetNoMutualAidYetSupport(focusTitle),
      'glance_focus_mutual_aid' => l10n.glanceFocusMutualAidSupport(focusTitle),
      'glance_focus_no_mutual_aid_yet' => l10n.glanceFocusNoMutualAidYetSupport(
        focusTitle,
      ),
      'glance_focus_only' => l10n.glanceFocusOnlySupport(focusTitle),
      'glance_practice_recorded' => l10n.glancePracticeRecordedSupport,
      'glance_no_practice_yet' => l10n.glanceNoPracticeYetSupport,
      'glance_mutual_aid_recorded' => l10n.glanceMutualAidRecordedSupport,
      'glance_no_mutual_aid_yet' => l10n.glanceNoMutualAidYetSupport,
      'glance_no_data_yet' => l10n.glanceNoDataYetSupport,
      _ => l10n.glanceNoDataYetSupport,
    };
  }
}

class _UnderstandingCard extends StatelessWidget {
  const _UnderstandingCard({
    required this.l10n,
    required this.state,
    required this.card,
    required this.action,
    required this.unavailable,
    required this.retrying,
    required this.canRetry,
    required this.onRetry,
  });

  final AppLocalizations l10n;
  final AppState state;
  final ParentUnderstandingCard card;
  final ParentAction? action;
  final bool unavailable;
  final bool retrying;
  final bool canRetry;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    final isBm = state.isBahasaMelayu;
    if (retrying) {
      return _retryingSection(
        theme: theme,
        title: l10n.understandingCardTitle,
        color: _warm(oasis),
      );
    }
    if (unavailable) {
      return _stateSection(
        theme: theme,
        title: l10n.understandingCardTitle,
        color: _warm(oasis),
        icon: Icons.psychology_outlined,
        text: l10n.understandingUnavailable,
        canRetry: canRetry,
        onRetry: onRetry,
      );
    }
    if (card.status == ParentUnderstandingStatus.insufficientEvidence) {
      return _stateSection(
        theme: theme,
        title: l10n.understandingCardTitle,
        color: _warm(oasis),
        icon: Icons.psychology_outlined,
        text: l10n.understandingInsufficient,
        canRetry: false,
        onRetry: onRetry,
      );
    }
    final focusTitle = isBm
        ? card.focusSubtopicTitleBm
        : card.focusSubtopicTitle;
    final topicTitle = isBm ? card.topicTitleBm : card.topicTitle;
    final strengthTitle = card.positiveSubtopicId == null
        ? null
        : isBm
        ? card.positiveSubtopicTitleBm
        : card.positiveSubtopicTitle;
    return _ProgressSection(
      title: l10n.understandingCardTitle,
      color: _warm(oasis),
      icon: Icons.psychology_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.learningSnapshotLabel,
            style: theme.textTheme.labelLarge?.copyWith(
              color: oasis.primaryInk,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(l10n.focusTopic(topicTitle), style: theme.textTheme.bodyMedium),
          const SizedBox(height: 4),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  l10n.focusSubtopic(focusTitle),
                  style: theme.textTheme.titleMedium,
                ),
              ),
              const SizedBox(width: 8),
              _StatusPill(label: _bandLabel(l10n, card.masteryBand!)),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            l10n.focusObservationSentence(card.focusObservationCount ?? 0),
            style: theme.textTheme.bodySmall,
          ),
          if (strengthTitle != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                ExcludeSemantics(
                  child: Icon(
                    Icons.workspace_premium_outlined,
                    size: 18,
                    color: oasis.forest,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    l10n.focusStrength(strengthTitle),
                    style: theme.textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
          ],
          if (action != null) ...[
            const SizedBox(height: 12),
            Divider(color: oasis.outline, height: 1),
            const SizedBox(height: 10),
            Text(
              l10n.parentNextStep,
              style: theme.textTheme.labelLarge?.copyWith(
                color: oasis.primaryInk,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _actionText(l10n, action!, focusTitle),
              style: theme.textTheme.bodyMedium,
            ),
          ],
        ],
      ),
    );
  }

  static Color _warm(OasisSemanticTheme oasis) => Color.alphaBlend(
    oasis.forest.withValues(alpha: 0.08),
    oasis.surface,
  );

  static String _bandLabel(AppLocalizations l10n, ParentMasteryBand band) {
    return switch (band) {
      ParentMasteryBand.needsGuidedPractice =>
        l10n.focusStatusNeedsGuidedPractice,
      ParentMasteryBand.growing => l10n.focusStatusGrowing,
      ParentMasteryBand.currentStrength => l10n.focusStatusCurrentStrength,
    };
  }

  static String _actionText(
    AppLocalizations l10n,
    ParentAction action,
    String focusTitle,
  ) {
    return switch (action.kind) {
      ParentActionKind.understandingFocus => l10n.actionUnderstandingFocus(
        focusTitle,
      ),
      ParentActionKind.maintainStrength => l10n.actionMaintainStrength(
        focusTitle,
      ),
      ParentActionKind.practiceRoutine => l10n.actionPracticeRoutine,
      ParentActionKind.mutualAidInvitation => l10n.actionMutualAidInvitation,
      ParentActionKind.needsMoreActivity => l10n.actionNeedsMoreActivity,
    };
  }
}

class _PracticeCard extends StatelessWidget {
  const _PracticeCard({
    required this.l10n,
    required this.card,
    required this.retrying,
    required this.canRetry,
    required this.onRetry,
  });

  final AppLocalizations l10n;
  final ParentPracticeCard card;
  final bool retrying;
  final bool canRetry;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    if (retrying) {
      return _retryingSection(
        theme: theme,
        title: l10n.practiceCardTitle,
        color: _green(oasis),
      );
    }
    if (card.status == ParentPracticeStatus.unavailable) {
      return _stateSection(
        theme: theme,
        title: l10n.practiceCardTitle,
        color: _green(oasis),
        icon: Icons.task_alt_outlined,
        text: l10n.practiceUnavailable,
        canRetry: canRetry,
        onRetry: onRetry,
      );
    }
    final dayLabels = <String>[
      l10n.dayMonday,
      l10n.dayTuesday,
      l10n.dayWednesday,
      l10n.dayThursday,
      l10n.dayFriday,
      l10n.daySaturday,
      l10n.daySunday,
    ];
    return _ProgressSection(
      title: l10n.practiceCardTitle,
      color: _green(oasis),
      icon: Icons.task_alt_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${l10n.practiceWeekly(card.weeklyTotal)} '
            '${l10n.practiceActiveDays(card.activeDayCount)}',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              for (var index = 0; index < 7; index++) ...[
                if (index > 0) const SizedBox(width: 6),
                Expanded(
                  child: Semantics(
                    container: true,
                    label: '${dayLabels[index]}: ${card.dailyCounts[index]}',
                    child: Column(
                      children: [
                        Text(
                          dayLabels[index],
                          style: theme.textTheme.labelSmall?.copyWith(
                            color: oasis.secondaryInk,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${card.dailyCounts[index]}',
                          style: theme.textTheme.titleSmall,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
          if (card.previousWeekCompletedPracticeCount != null) ...[
            const SizedBox(height: 10),
            Text(
              l10n.practiceComparison(card.previousWeekCompletedPracticeCount!),
              style: theme.textTheme.bodySmall,
            ),
          ],
          if (card.improvedOverPreviousWeek &&
              card.supportedDifference != null) ...[
            const SizedBox(height: 4),
            Text(
              l10n.practiceImproved(card.supportedDifference!),
              style: theme.textTheme.bodyMedium?.copyWith(
                color: oasis.forest,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ],
      ),
    );
  }

  static Color _green(OasisSemanticTheme oasis) => Color.alphaBlend(
    oasis.leaf.withValues(alpha: 0.10),
    oasis.surface,
  );
}

class _MutualAidCard extends StatelessWidget {
  const _MutualAidCard({
    required this.l10n,
    required this.card,
    required this.retrying,
    required this.canRetry,
    required this.onRetry,
  });

  final AppLocalizations l10n;
  final ParentMutualAidCard card;
  final bool retrying;
  final bool canRetry;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    if (retrying) {
      return _retryingSection(
        theme: theme,
        title: l10n.mutualAidCardTitle,
        color: _blue(oasis),
      );
    }
    if (card.status == ParentMutualAidStatus.unavailable) {
      return _stateSection(
        theme: theme,
        title: l10n.mutualAidCardTitle,
        color: _blue(oasis),
        icon: Icons.forum_outlined,
        text: l10n.mutualAidUnavailable,
        canRetry: canRetry,
        onRetry: onRetry,
      );
    }
    final rows = <Widget>[];
    if (card.questionsPostedCount > 0) {
      rows.add(
        _TimelineRow(
          icon: Icons.help_outline,
          text: l10n.mutualAidQuestions(card.questionsPostedCount),
        ),
      );
    }
    if (card.answersSubmittedCount > 0) {
      final replies = l10n.mutualAidReplies(card.answersSubmittedCount);
      final accepted = card.acceptedAnswersCount > 0
          ? l10n.mutualAidAccepted(card.acceptedAnswersCount)
          : '';
      rows.add(
        _TimelineRow(icon: Icons.forum_outlined, text: '$replies$accepted'),
      );
    }
    if (card.helpfulReceivedCount > 0) {
      rows.add(
        _TimelineRow(
          icon: Icons.favorite_outline,
          text: l10n.mutualAidHelpfulMarks(card.helpfulReceivedCount),
        ),
      );
    }
    return _ProgressSection(
      title: l10n.mutualAidCardTitle,
      color: _blue(oasis),
      icon: Icons.forum_outlined,
      child: rows.isEmpty
          ? Text(l10n.mutualAidZero, style: theme.textTheme.bodyMedium)
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (var index = 0; index < rows.length; index++) ...[
                  if (index > 0) const SizedBox(height: 10),
                  rows[index],
                ],
              ],
            ),
    );
  }

  static Color _blue(OasisSemanticTheme oasis) => Color.alphaBlend(
    oasis.water.withValues(alpha: 0.10),
    oasis.surface,
  );
}

class _ConversationStarterCard extends StatelessWidget {
  const _ConversationStarterCard({
    required this.l10n,
    required this.starter,
    required this.focusTitle,
  });

  final AppLocalizations l10n;
  final ParentConversationStarter starter;
  final String focusTitle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    final question = switch (starter.actionKind) {
      ParentActionKind.understandingFocus =>
        l10n.conversationUnderstandingFocus(focusTitle),
      ParentActionKind.maintainStrength => l10n.conversationMaintainStrength(
        focusTitle,
      ),
      ParentActionKind.practiceRoutine => l10n.conversationPracticeRoutine,
      ParentActionKind.mutualAidInvitation =>
        l10n.conversationMutualAidInvitation,
      ParentActionKind.needsMoreActivity => l10n.conversationNeedsMoreActivity,
    };
    return Semantics(
      container: true,
      header: true,
      label: l10n.conversationStarterTitle,
      child: SoftCard(
        padding: const EdgeInsets.all(16),
        color: oasis.mint,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              l10n.conversationStarterTitle,
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text(question, style: theme.textTheme.bodyLarge),
          ],
        ),
      ),
    );
  }
}

class _ProgressSection extends StatelessWidget {
  const _ProgressSection({
    required this.title,
    required this.color,
    required this.icon,
    required this.child,
  });

  final String title;
  final Color color;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    return Semantics(
      container: true,
      header: true,
      label: title,
      child: SoftCard(
        padding: const EdgeInsets.all(16),
        color: color,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                ExcludeSemantics(
                  child: Icon(icon, size: 20, color: oasis.primaryInk),
                ),
                const SizedBox(width: 8),
                Text(title, style: theme.textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 10),
            child,
          ],
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: oasis.groupedSurface,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: theme.textTheme.labelMedium?.copyWith(
          color: oasis.primaryInk,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    return Row(
      children: [
        ExcludeSemantics(
          child: Icon(icon, size: 18, color: oasis.water),
        ),
        const SizedBox(width: 8),
        Expanded(child: Text(text, style: theme.textTheme.bodyMedium)),
      ],
    );
  }
}

class _ParentDashboardSafeStatusBanner extends StatelessWidget {
  const _ParentDashboardSafeStatusBanner({
    required this.loading,
    required this.text,
    this.onRetry,
  });

  final bool loading;
  final String text;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    return SoftCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      color: loading ? oasis.mint : oasis.groupedSurface,
      child: Row(
        children: [
          SizedBox(
            width: 20,
            height: 20,
            child: loading
                ? const CircularProgressIndicator(strokeWidth: 2.4)
                : const Icon(Icons.cloud_off_outlined, size: 20),
          ),
          const SizedBox(width: 10),
          Expanded(child: Text(text)),
          if (!loading && onRetry != null)
            TextButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}

Widget _stateSection({
  required ThemeData theme,
  required String title,
  required Color color,
  required IconData icon,
  required String text,
  required bool canRetry,
  required VoidCallback onRetry,
}) {
  return _ProgressSection(
    title: title,
    color: color,
    icon: icon,
    child: Row(
      children: [
        Expanded(child: Text(text, style: theme.textTheme.bodyMedium)),
        if (canRetry)
          TextButton(onPressed: onRetry, child: const Text('Retry')),
      ],
    ),
  );
}

Widget _retryingSection({
  required ThemeData theme,
  required String title,
  required Color color,
}) {
  return _ProgressSection(
    title: title,
    color: color,
    icon: Icons.hourglass_top_outlined,
    child: Row(
      children: [
        const SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        const SizedBox(width: 10),
        Text('Loading…', style: theme.textTheme.bodyMedium),
      ],
    ),
  );
}
