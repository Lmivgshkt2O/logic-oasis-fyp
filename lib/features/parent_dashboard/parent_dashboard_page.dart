import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/attempt_row.dart';
import 'package:logic_oasis/shared/widgets/metric_card.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';
import 'package:logic_oasis/shared/widgets/section_card.dart';

class ParentDashboardPage extends StatefulWidget {
  const ParentDashboardPage({super.key, required this.state});

  final AppState state;

  @override
  State<ParentDashboardPage> createState() => _ParentDashboardPageState();
}

class _ParentDashboardPageState extends State<ParentDashboardPage> {
  @override
  void initState() {
    super.initState();
    widget.state.loadParentDashboardFromFirebase();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.state,
      builder: (context, _) => _ParentDashboardContent(state: widget.state),
    );
  }
}

class _ParentDashboardContent extends StatelessWidget {
  const _ParentDashboardContent({required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final latestAttempt = state.latestAttempt;
    final insight = state.weakTopicInsight;
    final aiDiagnosis = state.recommendedAiDiagnosis;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      children: [
        Text(
          l10n.parentDashboard,
          style: theme.textTheme.headlineLarge,
        ),
        const SizedBox(height: 8),
        Text(
          l10n.parentDashboardSummary(state.studentName),
          style: theme.textTheme.bodyLarge,
        ),
        if (state.isLoadingParentDashboard ||
            state.parentDashboardMessage != null) ...[
          const SizedBox(height: 14),
          _ParentDashboardStatusBanner(state: state),
        ],
        const SizedBox(height: 18),
        SectionCard(
          title: l10n.overallRestoration,
          icon: Icons.eco_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              LinearProgressIndicator(value: state.restorationProgress),
              const SizedBox(height: 10),
              Text(
                l10n.oasisRestoredSummary(
                  (state.restorationProgress * 100).round(),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: MetricCard(
                icon: Icons.trending_up,
                label: l10n.averageScore,
                value: '${state.averageScore}%',
                color: LogicOasisTheme.leaf,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: MetricCard(
                icon: Icons.history,
                label: l10n.latestQuiz,
                value: latestAttempt == null ? '-' : '${latestAttempt.score}%',
                color: LogicOasisTheme.clay,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: l10n.recentActivity,
          icon: Icons.history_outlined,
          child: Column(
            children: [
              for (final attempt in state.recentAttempts.take(3)) ...[
                AttemptRow(
                  attempt: attempt,
                  isBahasaMelayu: state.isBahasaMelayu,
                ),
                if (attempt != state.recentAttempts.take(3).last)
                  const Divider(height: 24),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: l10n.predictionSummary,
          icon: Icons.lightbulb_outline,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.weakTopic(insight.topicTitle),
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text(insight.reason),
              if (aiDiagnosis != null) ...[
                const SizedBox(height: 12),
                _AiDiagnosisDetails(
                  masteryProbability: aiDiagnosis.bktMasteryProbability,
                  weaknessProbability: aiDiagnosis.weaknessProbability,
                  confidence: aiDiagnosis.confidence,
                  finalLabel: aiDiagnosis.finalMasteryLabel,
                  shapReasons: aiDiagnosis.shapReasons,
                  isBahasaMelayu: state.isBahasaMelayu,
                ),
              ],
              const SizedBox(height: 12),
              RecommendationBox(
                text: l10n.suggestedAction(insight.recommendation),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: l10n.collaborationNote,
          icon: Icons.groups_outlined,
          child: Text(
            l10n.collaborationNoteBody,
          ),
        ),
      ],
    );
  }
}

class _AiDiagnosisDetails extends StatelessWidget {
  const _AiDiagnosisDetails({
    required this.masteryProbability,
    required this.weaknessProbability,
    required this.confidence,
    required this.finalLabel,
    required this.shapReasons,
    required this.isBahasaMelayu,
  });

  final double masteryProbability;
  final double weaknessProbability;
  final double confidence;
  final String finalLabel;
  final List<String> shapReasons;
  final bool isBahasaMelayu;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final masteryText = (masteryProbability * 100).round();
    final weaknessText = (weaknessProbability * 100).round();
    final confidenceText = (confidence * 100).round();

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFE8F4EE),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFCFE3D7)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.greyBoxAiResult,
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            l10n.aiResultSummary(
              finalLabel,
              masteryText,
              weaknessText,
              confidenceText,
            ),
            style: theme.textTheme.bodyMedium,
          ),
          if (shapReasons.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              l10n.shapReasons(shapReasons.take(3).join(', ')),
              style: theme.textTheme.bodyMedium,
            ),
          ],
        ],
      ),
    );
  }
}

class _ParentDashboardStatusBanner extends StatelessWidget {
  const _ParentDashboardStatusBanner({required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final isSuccess = state.loadedParentDashboardFromFirebase;
    final message = state.isLoadingParentDashboard
        ? l10n.loadingParentDashboard
        : state.parentDashboardMessage ?? '';

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
            child: state.isLoadingParentDashboard
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
