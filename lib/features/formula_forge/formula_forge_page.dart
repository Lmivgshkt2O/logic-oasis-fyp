import 'package:flutter/material.dart';
import 'package:logic_oasis/features/formula_forge/widgets/topic_card.dart';
import 'package:logic_oasis/features/quiz/quiz_page.dart';
import 'package:logic_oasis/features/quiz/result_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/quiz_completion.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class FormulaForgePage extends StatelessWidget {
  const FormulaForgePage({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 18),
      children: [
        Row(
          children: [
            Container(
              width: 68,
              height: 68,
              decoration: BoxDecoration(
                color: theme.colorScheme.primary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Icon(
                Icons.calculate_outlined,
                color: theme.colorScheme.primary,
                size: 34,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.formulaForge,
                    style: theme.textTheme.headlineLarge,
                  ),
                  const SizedBox(height: 5),
                  Text(
                    l10n.forgeSubtitle,
                    style: theme.textTheme.bodyLarge,
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
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
            lockedReason: topic.questions.isEmpty
                ? l10n.topicLockedQuestionBank
                : null,
            onStart: topic.questions.isEmpty
                ? null
                : () async {
                    final result = await Navigator.of(context)
                        .push<QuizCompletion>(
                          MaterialPageRoute(
                            builder: (_) => QuizPage(
                              topic: topic,
                              isBahasaMelayu: state.isBahasaMelayu,
                            ),
                          ),
                        );
                    if (result != null && context.mounted) {
                      final reward = state.saveQuizResult(
                        topicId: topic.id,
                        correctCount: result.correctCount,
                        totalQuestions: topic.questions.length,
                        timeTakenSeconds: result.timeTakenSeconds,
                      );
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => ResultPage(
                            correctCount: result.correctCount,
                            totalQuestions: topic.questions.length,
                            topicArea: topic.localizedArea(
                              state.isBahasaMelayu,
                            ),
                            isBahasaMelayu: state.isBahasaMelayu,
                            reward: reward,
                            onBackToForge: () {
                              Navigator.of(context).pop();
                              state.changeTab(1);
                            },
                          ),
                        ),
                      );
                    }
                  },
          ),
          const SizedBox(height: 13),
        ],
      ],
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
