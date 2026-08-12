import 'dart:async';

import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/features/quiz/result_page.dart';
import 'package:logic_oasis/features/quiz/quiz_page.dart';
import 'package:logic_oasis/shared/models/next_learning_action.dart';
import 'package:logic_oasis/shared/models/subtopic.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/services/quiz_session_service.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';

class SubtopicPage extends StatelessWidget {
  const SubtopicPage({
    super.key,
    required this.state,
    required this.topic,
    this.sessionService,
    this.aiDiagnosisStreamFactory,
  });

  final AppState state;
  final Topic topic;
  final QuizSessionGateway? sessionService;
  final AiDiagnosisStreamFactory? aiDiagnosisStreamFactory;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: state,
      builder: (context, _) {
        final currentTopic = state.topics.firstWhere(
          (item) => item.id == topic.id,
          orElse: () => topic,
        );
        final subtopics = state.subtopicsForTopic(currentTopic);

        return Scaffold(
          appBar: AppBar(
            title: Text(currentTopic.localizedTitle(state.isBahasaMelayu)),
          ),
          body: LogicOasisScaffold(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
            children: [
              LogicHeader(
                leading: const _SubtopicHeaderIcon(),
                title: currentTopic.localizedTitle(state.isBahasaMelayu),
                subtitle: state.t(
                  'Choose one small step to practise.',
                  'Pilih satu langkah kecil untuk berlatih.',
                ),
              ),
              const SizedBox(height: 16),
              _TopicProgressSummary(topic: currentTopic, state: state),
              const SizedBox(height: 16),
              for (final subtopic in subtopics) ...[
                _SubtopicCard(
                  topic: currentTopic,
                  subtopic: subtopic,
                  state: state,
                  onStart: () =>
                      _startSubtopicQuiz(context, currentTopic, subtopic),
                ),
                const SizedBox(height: 12),
              ],
            ],
          ),
        );
      },
    );
  }

  Future<void> _startSubtopicQuiz(
    BuildContext context,
    Topic topic,
    Subtopic subtopic,
  ) async {
    if (!state.isSubtopicUnlocked(topic, subtopic) ||
        subtopic.activeBankCount <= 0 ||
        subtopic.questions.isEmpty) {
      return;
    }

    _showStartingQuiz(context);
    try {
      final session = await (sessionService ?? QuizSessionService()).startSession(
        topicId: topic.id,
        subtopicId: subtopic.id,
        yearLevel: topic.yearLevel,
      );
      if (!context.mounted) return;
      Navigator.of(context).pop();
      final action = await Navigator.of(context).push<NextLearningAction>(
        MaterialPageRoute(
          builder: (_) => QuizPage(
            session: session,
            title: topic.localizedTitle(state.isBahasaMelayu),
            isBahasaMelayu: state.isBahasaMelayu,
            sessionService: sessionService,
            aiDiagnosisStreamFactory: aiDiagnosisStreamFactory,
            onFinalized: (completion) {
              state.applyTrustedQuizCompletion(
                topicId: topic.id,
                subtopicId: subtopic.id,
                correctCount: completion.correctCount,
                totalQuestions:
                    completion.totalQuestions ?? session.questions.length,
              );
              // The callable completion has already been confirmed. Reconcile
              // with its projection without holding the result page hostage to
              // a separate Firestore read.
              unawaited(state.refreshTrustedProgress(replaceAll: false));
              return Future<void>.value();
            },
          ),
        ),
      );
      if (!context.mounted) return;
      await _resolveNextLearningAction(
        context,
        topic,
        subtopic,
        action,
      );
    } on QuizSessionException catch (error) {
      if (!context.mounted) return;
      Navigator.of(context).pop();
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(error.message)));
    } catch (_) {
      if (!context.mounted) return;
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            state.t(
              'Unable to start a secure quiz. Check the connection and try again.',
              'Tidak dapat memulakan kuiz selamat. Semak sambungan dan cuba lagi.',
            ),
          ),
        ),
      );
    }
  }

  void _showStartingQuiz(BuildContext context) {
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()),
    );
  }

  Future<void> _resolveNextLearningAction(
    BuildContext context,
    Topic topic,
    Subtopic subtopic,
    NextLearningAction? action,
  ) async {
    if (action == null || action.isBack) return;
    if (action.isRepeat) {
      await _startSubtopicQuiz(context, topic, subtopic);
      return;
    }
    if (action.isAdvance) {
      await _handleAdvance(context, topic, action);
    }
  }

  Future<void> _handleAdvance(
    BuildContext context,
    Topic topic,
    NextLearningAction action,
  ) async {
    final targetTopicId = action.targetTopicId;
    final targetSubtopicId = action.targetSubtopicId;
    if (targetSubtopicId != null &&
        (targetTopicId == null || targetTopicId == topic.id)) {
      final matches = state
          .subtopicsForTopic(topic)
          .where((item) => item.id == targetSubtopicId)
          .toList();
      if (matches.isNotEmpty) {
        await _startSubtopicQuiz(context, topic, matches.first);
        return;
      }
    }

    final topics = state.topics;
    if (targetTopicId != null && targetTopicId != topic.id) {
      final nextTopic = topics.where((item) => item.id == targetTopicId).toList();
      if (nextTopic.isNotEmpty) {
        _openSubtopicPage(context, nextTopic.first);
        return;
      }
    }

    final topicIndex = topics.indexWhere((item) => item.id == topic.id);
    if (topicIndex >= 0 && topicIndex + 1 < topics.length) {
      _openSubtopicPage(context, topics[topicIndex + 1]);
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          state.t(
            'You completed all available topics!',
            'Anda telah melengkapkan semua topik yang tersedia!',
          ),
        ),
      ),
    );
    Navigator.of(context).popUntil((route) => route.isFirst);
  }

  void _openSubtopicPage(BuildContext context, Topic nextTopic) {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => SubtopicPage(
          state: state,
          topic: nextTopic,
          sessionService: sessionService,
          aiDiagnosisStreamFactory: aiDiagnosisStreamFactory,
        ),
      ),
    );
  }
}

class _TopicProgressSummary extends StatelessWidget {
  const _TopicProgressSummary({required this.topic, required this.state});

  final Topic topic;
  final AppState state;

  @override
  Widget build(BuildContext context) {
    final subtopics = state.subtopicsForTopic(topic);
    final completed = subtopics.where((subtopic) => subtopic.isComplete).length;
    return SoftCard(
      padding: const EdgeInsets.all(14),
      radius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.route_rounded,
                color: LogicOasisDesign.forest,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  state.t(
                    '$completed of ${subtopics.length} subtopics completed',
                    '$completed daripada ${subtopics.length} subtopik selesai',
                  ),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ProgressBar(
            value: topic.progress,
            color: LogicOasisDesign.leaf,
            height: 7,
          ),
        ],
      ),
    );
  }
}

class _SubtopicCard extends StatelessWidget {
  const _SubtopicCard({
    required this.topic,
    required this.subtopic,
    required this.state,
    required this.onStart,
  });

  final Topic topic;
  final Subtopic subtopic;
  final AppState state;
  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    final unlocked = state.isSubtopicUnlocked(topic, subtopic);
    final lockedReason = state.lockedReasonForSubtopic(topic, subtopic);
    // A client-side question preview alone is not sufficient for the U3
    // callable workflow: the selected bank must also be active on the server.
    // This avoids offering a playable card that would fail at quiz start while
    // its Firestore bank deployment is still pending.
    // The server callable is the bank authority: the card stays tappable as
    // long as client-safe questions are present, so a stale or missing
    // `activeBankCount` never locks the first subtopic. If the server bank is
    // genuinely unavailable, the start attempt returns a clear localized error.
    final hasClientQuestions = subtopic.questions.isNotEmpty;
    final canStart = unlocked && hasClientQuestions;
    final status = _SubtopicStatus.forSubtopic(
      subtopic,
      unlocked: unlocked,
      isBahasaMelayu: state.isBahasaMelayu,
    );
    final description =
        lockedReason ??
        (!hasClientQuestions
            ? state.t(
                'Question bank is not ready yet.',
                'Bank soalan belum tersedia.',
              )
            : subtopic.localizedDescription(state.isBahasaMelayu));

    return Opacity(
      opacity: canStart ? 1 : .72,
      child: SoftCard(
        onTap: canStart ? onStart : null,
        padding: const EdgeInsets.all(14),
        radius: 18,
        child: Row(
          children: [
            _SubtopicStepBadge(order: subtopic.order, unlocked: unlocked),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          subtopic.localizedTitle(state.isBahasaMelayu),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: LogicOasisDesign.ink,
                            fontSize: 17,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      Icon(
                        canStart
                            ? Icons.play_arrow_rounded
                            : Icons.lock_outline_rounded,
                        color: canStart
                            ? LogicOasisDesign.forest
                            : const Color(0xFF8C7A61),
                      ),
                    ],
                  ),
                  const SizedBox(height: 5),
                  Text(
                    description,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: LogicOasisDesign.body,
                      fontSize: 12.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Semantics(
                    container: true,
                    label: status.progressSemanticsLabel,
                    child: Row(
                      children: [
                        Expanded(
                          child: ProgressBar(
                            value: status.progress,
                            color: status.progressColor,
                            height: 6,
                          ),
                        ),
                        if (status.percentageLabel != null) ...[
                          const SizedBox(width: 8),
                          Text(
                            status.percentageLabel!,
                            style: const TextStyle(
                              color: LogicOasisDesign.body,
                              fontSize: 12,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ],
                        const SizedBox(width: 10),
                        StatusChip(
                          label: status.label,
                          icon: status.icon,
                          color: status.color,
                          background: status.background,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Child-facing mastery/status shown on a subtopic card. It renders only
/// server-derived values: BKT mastery when available, a clearly labelled
/// quiz-progress rate on fallback, and no invented percentage while pending.
class _SubtopicStatus {
  const _SubtopicStatus({
    required this.label,
    required this.color,
    required this.background,
    this.icon,
    this.progress = 0,
    this.percentageLabel,
    this.progressSemanticsLabel = '',
  });

  final String label;
  final Color color;
  final Color background;
  final String? icon;
  final double progress;
  final Color progressColor = LogicOasisDesign.leaf;
  final String? percentageLabel;
  final String progressSemanticsLabel;

  factory _SubtopicStatus.forSubtopic(
    Subtopic subtopic, {
    required bool unlocked,
    required bool isBahasaMelayu,
  }) {
    if (!unlocked) {
      return const _SubtopicStatus(
        label: 'Lock',
        color: Color(0xFF8C7A61),
        background: Color(0xFFF1E8D7),
        icon: 'lock_outline',
        progressSemanticsLabel: 'Locked',
      );
    }
    if (!subtopic.isAttempted) {
      final label =
          subtopic.mastery == 'New'
              ? (isBahasaMelayu ? 'Baru' : 'New')
              : subtopic.mastery;
      return _SubtopicStatus(
        label: label,
        color: const Color(0xFFB96E00),
        background: const Color(0xFFFFF0CC),
        progressSemanticsLabel: label,
      );
    }
    if (subtopic.isAnalysisPending) {
      final label = isBahasaMelayu
          ? 'Menyediakan penguasaan…'
          : 'Preparing mastery…';
      return _SubtopicStatus(
        label: label,
        color: const Color(0xFFB96E00),
        background: const Color(0xFFFFF0CC),
        progressSemanticsLabel: label,
      );
    }
    if (subtopic.usesCorrectRateFallback) {
      final percent = ((subtopic.bestCorrectRate ?? 0) * 100).round();
      final label = isBahasaMelayu
          ? 'Kemajuan kuiz $percent%'
          : 'Quiz progress $percent%';
      return _SubtopicStatus(
        label: label,
        color: const Color(0xFFB96E00),
        background: const Color(0xFFFFF0CC),
        progress: subtopic.bestCorrectRate ?? 0,
        progressSemanticsLabel: label,
      );
    }
    final masteryProbability = subtopic.masteryProbability;
    if (masteryProbability != null) {
      final percent = (masteryProbability * 100).round();
      final ready = subtopic.isComplete;
      final statusLabel = ready
          ? (isBahasaMelayu ? 'Bersedia untuk teruskan' : 'Ready to move on')
          : (isBahasaMelayu ? 'Masih belajar' : 'Still learning');
      final percentageLabel = isBahasaMelayu
          ? 'Penguasaan $percent%'
          : 'Mastery $percent%';
      return _SubtopicStatus(
        label: statusLabel,
        color: ready
            ? LogicOasisDesign.forest
            : const Color(0xFFB96E00),
        background: ready
            ? const Color(0xFFE3F5DB)
            : const Color(0xFFFFF0CC),
        progress: masteryProbability,
        percentageLabel: percentageLabel,
        progressSemanticsLabel: '$percentageLabel, $statusLabel',
      );
    }
    return _SubtopicStatus(
      label: subtopic.mastery,
      color: const Color(0xFFB96E00),
      background: const Color(0xFFFFF0CC),
      progressSemanticsLabel: subtopic.mastery,
    );
  }
}

class _SubtopicStepBadge extends StatelessWidget {
  const _SubtopicStepBadge({required this.order, required this.unlocked});

  final int order;
  final bool unlocked;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 46,
      height: 46,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: unlocked ? const Color(0xFFE3F5DB) : const Color(0xFFF1E8D7),
        border: Border.all(color: LogicOasisDesign.line),
      ),
      child: Text(
        '$order',
        style: TextStyle(
          color: unlocked ? LogicOasisDesign.forest : const Color(0xFF8C7A61),
          fontSize: 18,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _SubtopicHeaderIcon extends StatelessWidget {
  const _SubtopicHeaderIcon();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 58,
      height: 58,
      decoration: BoxDecoration(
        color: const Color(0xFFE3F5DB),
        borderRadius: BorderRadius.circular(17),
      ),
      child: const Icon(
        Icons.account_tree_rounded,
        color: LogicOasisDesign.forest,
        size: 30,
      ),
    );
  }
}
