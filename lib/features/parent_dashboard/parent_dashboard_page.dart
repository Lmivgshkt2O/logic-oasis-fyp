import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/attempt_row.dart';
import 'package:logic_oasis/shared/widgets/metric_card.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';
import 'package:logic_oasis/shared/widgets/section_card.dart';

class ParentDashboardPage extends StatelessWidget {
  const ParentDashboardPage({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final latestAttempt = state.latestAttempt;
    final insight = state.weakTopicInsight;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      children: [
        Text('Parent Dashboard', style: theme.textTheme.headlineLarge),
        const SizedBox(height: 8),
        Text(
          'A calm summary of Aiman\'s learning progress.',
          style: theme.textTheme.bodyLarge,
        ),
        const SizedBox(height: 18),
        SectionCard(
          title: 'Overall restoration',
          icon: Icons.eco_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              LinearProgressIndicator(value: state.restorationProgress),
              const SizedBox(height: 10),
              Text(
                '${(state.restorationProgress * 100).round()}% of the oasis is restored.',
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
                label: 'Average Score',
                value: '${state.averageScore}%',
                color: LogicOasisTheme.leaf,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: MetricCard(
                icon: Icons.history,
                label: 'Latest Quiz',
                value: latestAttempt == null ? '-' : '${latestAttempt.score}%',
                color: LogicOasisTheme.clay,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: 'Recent activity',
          icon: Icons.history_outlined,
          child: Column(
            children: [
              for (final attempt in state.recentAttempts.take(3)) ...[
                AttemptRow(attempt: attempt),
                if (attempt != state.recentAttempts.take(3).last)
                  const Divider(height: 24),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: 'Prediction summary',
          icon: Icons.lightbulb_outline,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Weak topic: ${insight.topicTitle}',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text(insight.reason),
              const SizedBox(height: 12),
              RecommendationBox(
                text: 'Suggested action: ${insight.recommendation}',
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        const SectionCard(
          title: 'Collaboration note',
          icon: Icons.groups_outlined,
          child: Text(
            'Mutual Aid features are prepared as a later phase. For FYP1, the dashboard can show the placeholder contribution score first.',
          ),
        ),
      ],
    );
  }
}
