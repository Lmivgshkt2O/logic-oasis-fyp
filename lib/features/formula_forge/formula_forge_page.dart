import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/features/formula_forge/subtopic_page.dart';
import 'package:logic_oasis/features/formula_forge/widgets/topic_card.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';

class FormulaForgePage extends StatelessWidget {
  const FormulaForgePage({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return LogicOasisScaffold(
      children: [
        LogicHeader(
          leading: const _ForgeVillageIcon(),
          title: 'Formula Forge',
          subtitle: state.t(
            'Practice topics that restore your oasis.',
            l10n.forgeSubtitle,
          ),
        ),
        const SizedBox(height: 18),
        if (state.isLoadingTopics || state.topicLoadMessage != null) ...[
          _FirebaseStatusBanner(state: state),
          const SizedBox(height: 13),
        ],
        if (state.isSavingQuizToFirebase || state.quizSaveMessage != null) ...[
          _QuizSaveStatusBanner(state: state),
          const SizedBox(height: 13),
        ],
        for (final topic in state.topics) ...[
          TopicCard(
            topic: topic,
            isBahasaMelayu: state.isBahasaMelayu,
            lockedReason: _lockedReasonForTopic(state, topic, l10n),
            onStart: _canOpenTopic(state, topic)
                ? () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => SubtopicPage(
                          state: state,
                          topic: topic,
                        ),
                      ),
                    );
                  }
                : null,
          ),
          const SizedBox(height: 14),
        ],
      ],
    );
  }

  bool _canOpenTopic(AppState state, Topic topic) {
    return state.isTopicUnlocked(topic) &&
        state.subtopicsForTopic(topic).isNotEmpty;
  }

  String? _lockedReasonForTopic(
    AppState state,
    Topic topic,
    AppLocalizations l10n,
  ) {
    final sequenceReason = state.lockedReasonForTopic(topic);
    if (sequenceReason != null) return sequenceReason;
    if (state.subtopicsForTopic(topic).isEmpty) {
      return l10n.topicLockedQuestionBank;
    }
    return null;
  }
}

class _ForgeVillageIcon extends StatelessWidget {
  const _ForgeVillageIcon();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 58,
      height: 58,
      decoration: BoxDecoration(
        color: const Color(0xFFDDF4E4),
        borderRadius: BorderRadius.circular(17),
      ),
      child: const Icon(
        Icons.account_balance_rounded,
        color: LogicOasisDesign.forest,
        size: 30,
      ),
    );
  }
}

class _QuizSaveStatusBanner extends StatelessWidget {
  const _QuizSaveStatusBanner({required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isSuccess = state.lastQuizSavedToFirebase;
    final message = state.quizSaveMessage ?? '';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: isSuccess ? const Color(0xFFE8F4EE) : const Color(0xFFFFF6E6),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isSuccess ? const Color(0xFFCFE3D7) : const Color(0xFFF0D8A8),
        ),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 20,
            height: 20,
            child: state.isSavingQuizToFirebase
                ? const CircularProgressIndicator(strokeWidth: 2.4)
                : Icon(
                    isSuccess ? Icons.task_alt_outlined : Icons.info_outline,
                    size: 20,
                    color: isSuccess
                        ? const Color(0xFF4F8F72)
                        : const Color(0xFF9A6514),
                  ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: const Color(0xFF33433D),
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FirebaseStatusBanner extends StatelessWidget {
  const _FirebaseStatusBanner({required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isSuccess = state.loadedTopicsFromFirebase;
    final message = state.isLoadingTopics
        ? AppLocalizations.of(context)!.loadingFirebaseQuestionBank
        : state.topicLoadMessage ?? '';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: isSuccess ? const Color(0xFFE8F4EE) : const Color(0xFFFFF6E6),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isSuccess ? const Color(0xFFCFE3D7) : const Color(0xFFF0D8A8),
        ),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 20,
            height: 20,
            child: state.isLoadingTopics
                ? const CircularProgressIndicator(strokeWidth: 2.4)
                : Icon(
                    isSuccess
                        ? Icons.cloud_done_outlined
                        : Icons.cloud_off_outlined,
                    size: 20,
                    color: isSuccess
                        ? const Color(0xFF4F8F72)
                        : const Color(0xFF9A6514),
                  ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: const Color(0xFF33433D),
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
