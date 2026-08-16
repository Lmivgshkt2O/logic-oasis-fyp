import 'dart:async';

import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/collaboration/qa_forum/qa_forum_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/forum_question.dart';
import 'package:logic_oasis/shared/models/next_learning_action.dart';
import 'package:logic_oasis/shared/models/quiz_completion.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';
import 'package:logic_oasis/shared/models/quiz_review_item.dart';
import 'package:logic_oasis/shared/repositories/collaboration_repository.dart';
import 'package:logic_oasis/shared/services/ai_status_service.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';
import 'package:logic_oasis/shared/widgets/section_card.dart';

typedef AiDiagnosisStreamFactory = Stream<AiDiagnosis?> Function(
  String attemptId, {
  String? topicId,
  String? subtopicId,
  int? yearLevel,
});

class ResultPage extends StatelessWidget {
  const ResultPage({
    super.key,
    required this.completion,
    required this.topicArea,
    required this.isBahasaMelayu,
    required this.topicId,
    required this.subtopicId,
    required this.yearLevel,
    this.reward,
    this.aiDiagnosis,
    this.attemptId,
    this.aiDiagnosisStreamFactory,
    this.forumRepository,
  });

  final QuizCompletion completion;
  final String topicArea;
  final bool isBahasaMelayu;
  final String topicId;
  final String subtopicId;
  final int yearLevel;
  final QuizReward? reward;
  final AiDiagnosis? aiDiagnosis;
  final String? attemptId;
  final AiDiagnosisStreamFactory? aiDiagnosisStreamFactory;
  final CollaborationRepository? forumRepository;

  Future<void> _openDiscussion(
    BuildContext context,
    QuizReviewItem item,
  ) async {
    final l10n = AppLocalizations.of(context)!;
    final repository = forumRepository ?? CollaborationRepository();
    try {
      final discussion = await repository.openOrCreateLinkedDiscussion(
        questionId: item.questionId,
      );
      if (!context.mounted) return;
      await Navigator.of(context).push<void>(
        MaterialPageRoute(
          builder: (_) => ForumDiscussionPage(
            question: ForumQuestion.fromLinkedDiscussion(discussion),
            state: AppState()
              ..language = isBahasaMelayu ? 'Bahasa Melayu' : 'English',
            repository: repository,
            // Opened from quiz review: after a successful linked submission
            // the student returns to the review card automatically.
            returnOnLinkedSubmit: true,
          ),
        ),
      );
    } catch (_) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.discussionUnavailable)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final score =
        reward?.score ??
        ((completion.correctCount /
                (completion.totalQuestions ?? 1))
            .clamp(0.0, 1.0) *
            100)
            .round();

    return Scaffold(
      appBar: AppBar(title: Text(l10n.quizResult)),
      body: LogicOasisScaffold(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        children: [
          Text(
            l10n.topicRestored(topicArea),
            style: theme.textTheme.headlineLarge,
          ),
          const SizedBox(height: 10),
          Text(
            l10n.quizCorrectSummary(
              completion.correctCount,
              completion.totalQuestions ?? completion.correctCount,
            ),
            style: theme.textTheme.bodyLarge,
          ),
          const SizedBox(height: 18),
          SectionCard(
            title: l10n.score,
            icon: Icons.emoji_events_outlined,
            child: Text('$score%', style: theme.textTheme.headlineLarge),
          ),
          if (reward != null) ...[
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _RewardTile(
                    icon: Icons.diamond_outlined,
                    label: l10n.crystals,
                    value: '+${reward!.earnedCrystals}',
                    color: LogicOasisTheme.of(context).water,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _RewardTile(
                    icon: Icons.construction_outlined,
                    label: l10n.repairReady,
                    value: l10n.home,
                    color: LogicOasisTheme.of(context).reward,
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 14),
          _ReviewSection(
            completion: completion,
            isBahasaMelayu: isBahasaMelayu,
            onDiscuss: (item) => _openDiscussion(context, item),
          ),
          const SizedBox(height: 14),
          RecommendationBox(
            text: reward == null
                ? (isBahasaMelayu
                      ? 'Markah ini telah disahkan oleh pelayan dan kemajuan anda sedang dikemas kini.'
                      : 'This score was confirmed by the server and your learning progress is being updated.')
                : l10n.masteryResultMessage(
                    isBahasaMelayu
                        ? _encouragementBm(reward!.score)
                        : reward!.encouragement,
                    isBahasaMelayu
                        ? _masteryBm(reward!.previousMastery)
                        : reward!.previousMastery,
                    isBahasaMelayu
                        ? _masteryBm(reward!.newMastery)
                        : reward!.newMastery,
                  ),
          ),
          const SizedBox(height: 14),
          _ResultAnalysis(
            attemptId: attemptId ?? completion.attemptId,
            topicId: topicId,
            subtopicId: subtopicId,
            yearLevel: yearLevel,
            isBahasaMelayu: isBahasaMelayu,
            streamFactory: aiDiagnosisStreamFactory,
            initialDiagnosis: aiDiagnosis,
          ),
          const SizedBox(height: 22),
          FilledButton.icon(
            onPressed: () => Navigator.of(
              context,
            ).pop(const NextLearningAction.back()),
            icon: const Icon(Icons.calculate_outlined),
            label: Text(l10n.backToForge),
          ),
        ],
      ),
    );
  }

  String _encouragementBm(int score) {
    if (score >= 80) {
      return 'Bagus. Topik ini semakin kukuh.';
    }
    if (score >= 50) {
      return 'Kemajuan yang baik. Sedikit lagi latihan boleh menguatkan topik ini.';
    }
    return 'Teruskan usaha. Oasis tetap berkembang apabila anda mencuba dan menyemak jawapan.';
  }

  String _masteryBm(String mastery) {
    return switch (mastery) {
      'Strong' => 'Kukuh',
      'Moderate' => 'Sederhana',
      'Weak' => 'Lemah',
      'New' => 'Baharu',
      'Locked' => 'Dikunci',
      _ => mastery,
    };
  }
}

class _ReviewSection extends StatelessWidget {
  const _ReviewSection({
    required this.completion,
    required this.isBahasaMelayu,
    required this.onDiscuss,
  });

  final QuizCompletion completion;
  final bool isBahasaMelayu;
  final Future<void> Function(QuizReviewItem item) onDiscuss;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final items = completion.reviewItems;
    if (items.isEmpty) {
      return SectionCard(
        title: l10n.reviewTheseFirst,
        icon: Icons.check_circle_outline,
        child: Text(l10n.perfectScore, style: theme.textTheme.bodyLarge),
      );
    }
    return SectionCard(
      title: l10n.reviewTheseFirst,
      icon: Icons.fact_check_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (var index = 0; index < items.length; index++) ...[
            _ReviewCard(
              item: items[index],
              isBahasaMelayu: isBahasaMelayu,
              onDiscuss: () => onDiscuss(items[index]),
            ),
            if (index < items.length - 1) const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }
}

class _ReviewCard extends StatelessWidget {
  const _ReviewCard({
    required this.item,
    required this.isBahasaMelayu,
    required this.onDiscuss,
  });

  final dynamic item;
  final bool isBahasaMelayu;
  final Future<void> Function() onDiscuss;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    final type = item.localizedType(isBahasaMelayu);
    return Semantics(
      container: true,
      label: '${item.sequenceIndex + 1}. ${item.localizedPrompt(isBahasaMelayu)}',
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 28,
            height: 28,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: oasis.reward.withValues(alpha: .15),
              border: Border.all(color: oasis.outline),
            ),
            child: Text(
              '${item.sequenceIndex + 1}',
              style: const TextStyle(
                color: OasisSemanticTheme.continuedPracticeText,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.localizedPrompt(isBahasaMelayu),
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
                if (type.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    type,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: oasis.secondaryInk,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
                const SizedBox(height: 4),
                Text(
                  item.localizedReviewFocus(isBahasaMelayu),
                  style: theme.textTheme.bodySmall,
                ),
                const SizedBox(height: 8),
                _DiscussInForumButton(onPressed: onDiscuss),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DiscussInForumButton extends StatefulWidget {
  const _DiscussInForumButton({required this.onPressed});

  final Future<void> Function() onPressed;

  @override
  State<_DiscussInForumButton> createState() => _DiscussInForumButtonState();
}

class _DiscussInForumButtonState extends State<_DiscussInForumButton> {
  bool _opening = false;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return TextButton.icon(
      onPressed: _opening
          ? null
          : () async {
              setState(() => _opening = true);
              try {
                await widget.onPressed();
              } finally {
                if (mounted) setState(() => _opening = false);
              }
            },
      icon: _opening
          ? const SizedBox.square(
              dimension: 14,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.forum_outlined),
      label: Text(_opening ? l10n.openingDiscussion : l10n.discussInForum),
    );
  }
}

/// Watches the server analysis and renders both the safe analysis card and
/// the server-backed next-practice panel with its single primary CTA.
class _ResultAnalysis extends StatefulWidget {
  const _ResultAnalysis({
    required this.attemptId,
    required this.topicId,
    required this.subtopicId,
    required this.yearLevel,
    required this.isBahasaMelayu,
    required this.streamFactory,
    this.initialDiagnosis,
  });

  final String? attemptId;
  final String topicId;
  final String subtopicId;
  final int yearLevel;
  final bool isBahasaMelayu;
  final AiDiagnosisStreamFactory? streamFactory;
  final AiDiagnosis? initialDiagnosis;

  @override
  State<_ResultAnalysis> createState() => _ResultAnalysisState();
}

class _ResultAnalysisState extends State<_ResultAnalysis> {
  late Stream<AiDiagnosis?>? _diagnosisStream;

  @override
  void initState() {
    super.initState();
    _diagnosisStream = _watchAttempt();
  }

  @override
  void didUpdateWidget(covariant _ResultAnalysis oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.attemptId != widget.attemptId ||
        oldWidget.streamFactory != widget.streamFactory ||
        oldWidget.topicId != widget.topicId ||
        oldWidget.subtopicId != widget.subtopicId ||
        oldWidget.yearLevel != widget.yearLevel) {
      _diagnosisStream = _watchAttempt();
    }
  }

  Stream<AiDiagnosis?>? _watchAttempt() {
    final attemptId = widget.attemptId;
    if (attemptId == null || attemptId.isEmpty) return null;
    return (widget.streamFactory ?? AiStatusService().watchAttempt)(
      attemptId,
      topicId: widget.topicId,
      subtopicId: widget.subtopicId,
      yearLevel: widget.yearLevel,
    );
  }

  void _retry() {
    setState(() => _diagnosisStream = _watchAttempt());
  }

  @override
  Widget build(BuildContext context) {
    final stream = _diagnosisStream;
    if (stream == null) {
      return _buildContent(context, widget.initialDiagnosis, onRetry: _retry);
    }
    return StreamBuilder<AiDiagnosis?>(
      stream: stream,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return _buildContent(
            context,
            null,
            onRetry: _retry,
            analysisError: true,
          );
        }
        return _buildContent(context, snapshot.data, onRetry: _retry);
      },
    );
  }

  Widget _buildContent(
    BuildContext context,
    AiDiagnosis? diagnosis, {
    required VoidCallback onRetry,
    bool analysisError = false,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (analysisError)
          _AnalysisUnavailable(
            isBahasaMelayu: widget.isBahasaMelayu,
            onRetry: onRetry,
          )
        else if (diagnosis != null)
          AiAnalysisStatusCard(
            diagnosis: diagnosis,
            isBahasaMelayu: widget.isBahasaMelayu,
          ),
        const SizedBox(height: 14),
        _NextPracticePanel(
          diagnosis: diagnosis,
          isBahasaMelayu: widget.isBahasaMelayu,
        ),
      ],
    );
  }
}

class _NextPracticePanel extends StatelessWidget {
  const _NextPracticePanel({
    required this.diagnosis,
    required this.isBahasaMelayu,
  });

  final AiDiagnosis? diagnosis;
  final bool isBahasaMelayu;

  NextLearningAction? _action() {
    final current = diagnosis;
    if (current == null || (!current.isCompleted && !current.isFallback)) {
      return null;
    }
    final basis = current.recommendationBasis;
    if (current.recommendsAdvance) {
      return NextLearningAction.advance(
        targetTopicId: current.recommendationTargetTopicId,
        targetSubtopicId: current.recommendationTargetSubtopicId,
        recommendationBasis: basis,
      );
    }
    return NextLearningAction.repeat(
      difficultyLabel:
          current.assignment?.difficulty.label ?? 'Easy',
      recommendationBasis: basis,
    );
  }

  String _localizedDifficulty(String label) {
    if (!isBahasaMelayu) return label;
    return switch (label) {
      'Easy' => 'Mudah',
      'Moderate' => 'Sederhana',
      'Hard' => 'Sukar',
      _ => label,
    };
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final action = _action();
    final ready = action != null;

    return Semantics(
      liveRegion: true,
      child: SectionCard(
        title: l10n.nextPractice,
        icon: ready ? Icons.route_outlined : Icons.hourglass_top_outlined,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (action?.isCorrectRateFallback == true) ...[
              Text(
                l10n.basedOnQuizProgress,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: OasisSemanticTheme.continuedPracticeText,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 6),
            ],
            Text(
              ready
                  ? l10n.nextPracticeLevel(
                      _localizedDifficulty(action.difficultyLabel ?? 'Easy'),
                    )
                  : l10n.preparingNextPractice,
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: ready
                  ? () => Navigator.of(context).pop(action)
                  : null,
              icon: Icon(
                ready
                    ? (action.isRepeat
                          ? Icons.refresh_rounded
                          : Icons.arrow_forward_rounded)
                    : Icons.hourglass_empty_rounded,
              ),
              label: Text(
                ready
                    ? (action.isRepeat
                          ? l10n.practiseAgain
                          : l10n.moveOn)
                    : l10n.preparingNextPractice,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AnalysisUnavailable extends StatelessWidget {
  const _AnalysisUnavailable({
    required this.isBahasaMelayu,
    required this.onRetry,
  });

  final bool isBahasaMelayu;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      title: isBahasaMelayu
          ? 'Status analisis tidak tersedia'
          : 'Analysis status unavailable',
      icon: Icons.sync_problem_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isBahasaMelayu
                ? 'Markah anda selamat, tetapi status analisis tidak tersedia buat sementara waktu.'
                : 'Your score is safe, but the analysis status is temporarily unavailable.',
          ),
          const SizedBox(height: 8),
          TextButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh_outlined),
            label: Text(
              isBahasaMelayu ? 'Cuba semula analisis' : 'Retry analysis',
            ),
          ),
        ],
      ),
    );
  }
}

/// A small safe projection card shared by immediate quiz results and future
/// result screens. It must receive only [AiDiagnosis.fromSafeProjection].
class AiAnalysisStatusCard extends StatelessWidget {
  const AiAnalysisStatusCard({
    super.key,
    required this.diagnosis,
    required this.isBahasaMelayu,
  });

  final AiDiagnosis diagnosis;
  final bool isBahasaMelayu;

  @override
  Widget build(BuildContext context) {
    final isReady = diagnosis.isCompleted || diagnosis.isFallback;
    final title = isBahasaMelayu
        ? (isReady ? 'Langkah latihan seterusnya' : 'Analisis pembelajaran')
        : (isReady ? 'Next practice step' : 'Learning analysis');
    final status = isBahasaMelayu
        ? switch (diagnosis.analysisState) {
            'completed' => 'Latihan seterusnya sudah sedia.',
            'fallback' => 'Cadangan latihan sedia menggunakan kemajuan kuiz.',
            'failed' =>
              'Markah anda disimpan. Cadangan akan tersedia kemudian.',
            _ => 'Markah anda disimpan. Sedang menyediakan latihan seterusnya…',
          }
        : diagnosis.childFacingStatus;
    final evidence = diagnosis.evidenceLevel == 'preliminary'
        ? (isBahasaMelayu
              ? 'Bukti awal — teruskan latihan ringkas.'
              : 'Preliminary evidence — keep practising in short steps.')
        : null;
    final modelEvidence = diagnosis.usesControlledDemonstrationModel
        ? (isBahasaMelayu
              ? 'Cadangan AI sokongan ini menggunakan model demonstrasi terkawal; ia belum disahkan untuk penggunaan dunia sebenar.'
              : 'This supportive AI recommendation uses a controlled demonstration model; it is not real-world validated.')
        : null;
    return SectionCard(
      title: title,
      icon: isReady ? Icons.route_outlined : Icons.hourglass_top_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(status),
          if (diagnosis.supportingReason != null) ...[
            const SizedBox(height: 8),
            Text(
              diagnosis.supportingReason!,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
            ),
          ],
          if (evidence != null) ...[
            const SizedBox(height: 8),
            Text(evidence, style: Theme.of(context).textTheme.bodySmall),
          ],
          if (modelEvidence != null) ...[
            const SizedBox(height: 8),
            Text(modelEvidence, style: Theme.of(context).textTheme.bodySmall),
          ],
        ],
      ),
    );
  }
}

class _RewardTile extends StatelessWidget {
  const _RewardTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SoftCard(
      padding: const EdgeInsets.all(14),
      radius: 18,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 104),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color),
            const SizedBox(height: 20),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(value, style: theme.textTheme.headlineMedium),
            ),
            Text(
              label,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}
