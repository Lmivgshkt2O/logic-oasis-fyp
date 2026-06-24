import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/progress/widgets/topic_progress_row.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/attempt_row.dart';
import 'package:logic_oasis/shared/widgets/metric_card.dart';
import 'package:logic_oasis/shared/widgets/section_card.dart';

class ProgressPage extends StatelessWidget {
  const ProgressPage({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final insight = state.weakTopicInsight;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      children: [
        Text('Student Progress', style: theme.textTheme.headlineLarge),
        const SizedBox(height: 8),
        Text(
          'Track topic mastery before sending insights to parents.',
          style: theme.textTheme.bodyLarge,
        ),
        const SizedBox(height: 18),
        Row(
          children: [
            Expanded(
              child: MetricCard(
                icon: Icons.assignment_turned_in_outlined,
                label: 'Quizzes',
                value: '${state.completedQuizzes}',
                color: LogicOasisTheme.leaf,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: MetricCard(
                icon: Icons.scoreboard_outlined,
                label: 'Average',
                value: '${state.averageScore}%',
                color: LogicOasisTheme.water,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: 'Topic mastery',
          icon: Icons.route_outlined,
          child: Column(
            children: [
              for (final topic in state.topics)
                Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: TopicProgressRow(topic: topic),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: 'Recent attempts',
          icon: Icons.history_outlined,
          child: Column(
            children: [
              for (final attempt in state.recentAttempts) ...[
                AttemptRow(attempt: attempt),
                if (attempt != state.recentAttempts.last)
                  const Divider(height: 24),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: 'Weak-topic signal',
          icon: Icons.psychology_alt_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${insight.topicTitle} needs focus',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 6),
              Text(insight.reason),
              const SizedBox(height: 8),
              Text(
                'Mastery: ${insight.mastery} • Average: ${insight.averageScore}%',
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
